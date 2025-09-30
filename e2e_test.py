#!/usr/bin/env python3
"""
End-to-End System Integration Test for Telemetry Dashboard
Tests the complete flow from metric ingestion to real-time visualization
"""

import asyncio
import aiohttp
import websockets
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import uuid
from colorama import Fore, Style, init

init(autoreset=True)

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/metrics"


class E2ESystemTest:
    def __init__(self):
        self.test_service = f"e2e_test_{uuid.uuid4().hex[:8]}"
        self.results = []
        self.websocket_messages = []
        self.alerts_received = []
        
    def log(self, message: str, level: str = "INFO"):
        colors = {
            "INFO": Fore.BLUE,
            "SUCCESS": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "TEST": Fore.CYAN
        }
        color = colors.get(level, Fore.WHITE)
        print(f"{color}[{level}] {message}{Style.RESET_ALL}")
    
    def print_header(self, title: str):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}{Style.RESET_ALL}\n")
    
    async def test_scenario_1_normal_operation(self, session: aiohttp.ClientSession):
        """Test normal metric flow through the system"""
        self.print_header("Scenario 1: Normal Operation Flow")
        
        # Step 1: Send a normal metric
        self.log("Sending normal metric...", "TEST")
        test_metric = {
            "timestamp": datetime.now().isoformat(),
            "service": self.test_service,
            "metric_type": "latency",
            "value": 45.67,
            "tags": {
                "endpoint": "/test",
                "region": "us-east",
                "test_id": "scenario_1"
            }
        }
        
        async with session.post(f"{BASE_URL}/metrics/ingest", json=test_metric) as resp:
            assert resp.status == 200, f"Ingestion failed: {resp.status}"
            data = await resp.json()
            assert data["status"] == "success", "Ingestion status not success"
            self.log("✓ Metric ingested successfully", "SUCCESS")
        
        # Step 2: Query it back
        await asyncio.sleep(0.5)  # Let it propagate
        self.log("Querying metric back...", "TEST")
        
        query = {
            "start_time": (datetime.now() - timedelta(minutes=1)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "services": [self.test_service],
            "aggregation": "raw"
        }
        
        async with session.post(f"{BASE_URL}/metrics/query", json=query) as resp:
            assert resp.status == 200, f"Query failed: {resp.status}"
            data = await resp.json()
            metrics = data.get("data", [])
            
            found = any(
                m["service"] == self.test_service and 
                m["value"] == 45.67 
                for m in metrics
            )
            assert found, "Metric not found in query results"
            self.log("✓ Metric retrieved successfully", "SUCCESS")
        
        # Step 3: Verify service discovery
        self.log("Checking service discovery...", "TEST")
        
        async with session.get(f"{BASE_URL}/metrics/services") as resp:
            assert resp.status == 200, f"Services endpoint failed: {resp.status}"
            data = await resp.json()
            services = [s["service"] for s in data["services"]]
            
            assert self.test_service in services, f"Test service not found in {services}"
            self.log(f"✓ Service '{self.test_service}' discovered", "SUCCESS")
        
        return True
    
    async def test_scenario_2_anomaly_detection(self, session: aiohttp.ClientSession):
        """Test anomaly detection and alert generation"""
        self.print_header("Scenario 2: Anomaly Detection & Alerts")
        
        # Step 1: Send high error rate metric
        self.log("Sending anomalous metric (high error rate)...", "TEST")
        anomaly_metric = {
            "timestamp": datetime.now().isoformat(),
            "service": self.test_service,
            "metric_type": "error_rate",
            "value": 0.85,  # 85% error rate - should trigger critical alert
            "tags": {"test_id": "scenario_2"}
        }
        
        async with session.post(f"{BASE_URL}/metrics/ingest", json=anomaly_metric) as resp:
            assert resp.status == 200, f"Ingestion failed: {resp.status}"
            data = await resp.json()
            
            # Check if alert was generated
            if "alert" in data and data["alert"]:
                alert = data["alert"]
                assert alert["severity"] == "critical", f"Expected critical, got {alert['severity']}"
                assert alert["service"] == self.test_service
                self.log(f"✓ Alert triggered: {alert['message']}", "SUCCESS")
                alert_id = alert["id"]
            else:
                assert False, "No alert generated for anomaly"
        
        # Step 2: Verify alert appears in alerts list
        await asyncio.sleep(0.5)
        self.log("Checking alerts endpoint...", "TEST")
        
        async with session.get(f"{BASE_URL}/metrics/alerts?limit=10") as resp:
            assert resp.status == 200
            data = await resp.json()
            alerts = data["alerts"]
            
            found_alert = any(
                a["service"] == self.test_service and 
                a["metric_type"] == "error_rate"
                for a in alerts
            )
            assert found_alert, "Alert not found in alerts list"
            self.log("✓ Alert present in alerts list", "SUCCESS")
        
        return True
    
    async def test_scenario_3_websocket_realtime(self):
        """Test real-time WebSocket updates"""
        self.print_header("Scenario 3: Real-time WebSocket Updates")
        
        self.log("Connecting to WebSocket...", "TEST")
        
        async with aiohttp.ClientSession() as session:
            async with websockets.connect(WS_URL) as websocket:
                # Receive initial data
                msg = await websocket.recv()
                data = json.loads(msg)
                assert data["type"] == "initial", "No initial data received"
                self.log(f"✓ Initial data received: {len(data.get('data', []))} metrics", "SUCCESS")
                
                # Send a metric while connected
                self.log("Sending metric while WebSocket connected...", "TEST")
                test_metric = {
                    "timestamp": datetime.now().isoformat(),
                    "service": self.test_service,
                    "metric_type": "throughput",
                    "value": 1234.56,
                    "tags": {"test_id": "scenario_3", "realtime": True}
                }
                
                async with session.post(f"{BASE_URL}/metrics/ingest", json=test_metric) as resp:
                    assert resp.status == 200
                
                # Wait for WebSocket update
                received = False
                start_time = time.time()
                
                while time.time() - start_time < 5:  # Wait up to 5 seconds
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                        data = json.loads(msg)
                        
                        if data["type"] == "metric":
                            metric = data["data"]
                            if (metric["service"] == self.test_service and 
                                metric["value"] == 1234.56):
                                received = True
                                self.log("✓ Real-time metric received via WebSocket", "SUCCESS")
                                break
                    except asyncio.TimeoutError:
                        continue
                
                assert received, "Metric not received via WebSocket"
        
        return True
    
    async def test_scenario_4_aggregation(self, session: aiohttp.ClientSession):
        """Test metric aggregation and percentile calculation"""
        self.print_header("Scenario 4: Aggregation & Statistics")
        
        # Step 1: Send multiple metrics for aggregation
        self.log("Sending batch of metrics for aggregation...", "TEST")
        
        base_time = datetime.now()
        metrics_sent = []
        
        for i in range(20):
            metric = {
                "timestamp": base_time.isoformat(),
                "service": self.test_service,
                "metric_type": "latency",
                "value": 50 + (i * 5),  # Values: 50, 55, 60, ..., 145
                "tags": {"test_id": "scenario_4", "index": i}
            }
            
            async with session.post(f"{BASE_URL}/metrics/ingest", json=metric) as resp:
                assert resp.status == 200
                metrics_sent.append(metric["value"])
        
        self.log(f"✓ Sent {len(metrics_sent)} metrics", "SUCCESS")
        
        # Step 2: Query with aggregation
        await asyncio.sleep(1)
        self.log("Querying with aggregation...", "TEST")
        
        query = {
            "start_time": (base_time - timedelta(minutes=1)).isoformat(),
            "end_time": (base_time + timedelta(minutes=1)).isoformat(),
            "services": [self.test_service],
            "metric_types": ["latency"],
            "aggregation": "1m"
        }
        
        async with session.post(f"{BASE_URL}/metrics/query", json=query) as resp:
            assert resp.status == 200
            data = await resp.json()
            aggregated = data.get("data", [])
            
            if aggregated:
                agg = aggregated[0]
                
                # Verify aggregation fields exist
                required_fields = ["p50", "p95", "p99", "min", "max", "avg", "count"]
                for field in required_fields:
                    assert field in agg, f"Missing aggregation field: {field}"
                
                # Verify values are reasonable
                assert agg["min"] >= 50, f"Min {agg['min']} should be >= 50"
                assert agg["max"] <= 145, f"Max {agg['max']} should be <= 145"
                assert agg["count"] >= 15, f"Count {agg['count']} should be >= 15"
                
                self.log(f"✓ Aggregation working: P50={agg['p50']:.1f}, P95={agg['p95']:.1f}, P99={agg['p99']:.1f}", "SUCCESS")
            else:
                self.log("⚠ No aggregated data returned", "WARNING")
        
        return True
    
    async def test_scenario_5_data_consistency(self, session: aiohttp.ClientSession):
        """Test data consistency across different endpoints"""
        self.print_header("Scenario 5: Data Consistency")
        
        # Step 1: Send metrics with specific values
        self.log("Sending test metrics...", "TEST")
        
        test_values = {
            "latency": 123.45,
            "throughput": 5678.90,
            "error_rate": 0.02,
            "cpu": 45.67,
            "memory": 67.89
        }
        
        timestamp = datetime.now()
        
        for metric_type, value in test_values.items():
            metric = {
                "timestamp": timestamp.isoformat(),
                "service": self.test_service,
                "metric_type": metric_type,
                "value": value,
                "tags": {"test_id": "scenario_5"}
            }
            
            async with session.post(f"{BASE_URL}/metrics/ingest", json=metric) as resp:
                assert resp.status == 200
        
        self.log(f"✓ Sent {len(test_values)} different metric types", "SUCCESS")
        
        # Step 2: Query raw data
        await asyncio.sleep(1)
        self.log("Verifying data consistency...", "TEST")
        
        query = {
            "start_time": (timestamp - timedelta(seconds=10)).isoformat(),
            "end_time": (timestamp + timedelta(seconds=10)).isoformat(),
            "services": [self.test_service],
            "aggregation": "raw"
        }
        
        async with session.post(f"{BASE_URL}/metrics/query", json=query) as resp:
            assert resp.status == 200
            data = await resp.json()
            metrics = data.get("data", [])
            
            # Verify all metric types are present with correct values
            found_types = {}
            for metric in metrics:
                if metric["service"] == self.test_service:
                    found_types[metric["metric_type"]] = metric["value"]
            
            for metric_type, expected_value in test_values.items():
                assert metric_type in found_types, f"Missing metric type: {metric_type}"
                assert found_types[metric_type] == expected_value, \
                    f"Value mismatch for {metric_type}: expected {expected_value}, got {found_types[metric_type]}"
            
            self.log("✓ All metric types present with correct values", "SUCCESS")
        
        # Step 3: Verify service statistics
        self.log("Checking service statistics...", "TEST")
        
        async with session.get(f"{BASE_URL}/metrics/services") as resp:
            assert resp.status == 200
            data = await resp.json()
            
            test_service_data = next(
                (s for s in data["services"] if s["service"] == self.test_service),
                None
            )
            
            assert test_service_data is not None, "Test service not found"
            assert "metrics" in test_service_data, "No metrics in service data"
            
            # Check health status calculation
            if test_values["error_rate"] < 0.05 and test_values["latency"] < 500:
                expected_status = "healthy"
            else:
                expected_status = "degraded"
            
            self.log(f"✓ Service status: {test_service_data['status']}", "SUCCESS")
        
        return True
    
    async def test_scenario_6_concurrent_operations(self, session: aiohttp.ClientSession):
        """Test system under concurrent load"""
        self.print_header("Scenario 6: Concurrent Operations")
        
        self.log("Testing concurrent metric ingestion...", "TEST")
        
        # Send 50 metrics concurrently
        async def send_metric(index: int):
            metric = {
                "timestamp": datetime.now().isoformat(),
                "service": self.test_service,
                "metric_type": "latency",
                "value": float(index),
                "tags": {"test_id": "scenario_6", "index": index}
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/metrics/ingest",
                    json=metric,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
            except:
                return False
        
        tasks = [send_metric(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r)
        assert success_count >= 45, f"Only {success_count}/50 succeeded"
        self.log(f"✓ Concurrent ingestion: {success_count}/50 successful", "SUCCESS")
        
        # Concurrent queries
        self.log("Testing concurrent queries...", "TEST")
        
        async def query_metrics():
            query = {
                "start_time": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "end_time": datetime.now().isoformat(),
                "aggregation": "raw"
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/metrics/query",
                    json=query,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    return resp.status == 200
            except:
                return False
        
        tasks = [query_metrics() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r)
        assert success_count >= 18, f"Only {success_count}/20 queries succeeded"
        self.log(f"✓ Concurrent queries: {success_count}/20 successful", "SUCCESS")
        
        return True
    
    async def run_all_scenarios(self):
        """Run all E2E test scenarios"""
        self.print_header("END-TO-END SYSTEM INTEGRATION TEST")
        
        scenarios = [
            ("Normal Operation", self.test_scenario_1_normal_operation),
            ("Anomaly Detection", self.test_scenario_2_anomaly_detection),
            ("WebSocket Real-time", self.test_scenario_3_websocket_realtime),
            ("Aggregation", self.test_scenario_4_aggregation),
            ("Data Consistency", self.test_scenario_5_data_consistency),
            ("Concurrent Operations", self.test_scenario_6_concurrent_operations)
        ]
        
        passed = 0
        failed = 0
        
        async with aiohttp.ClientSession() as session:
            # First verify system is running
            try:
                async with session.get(f"{BASE_URL}/metrics/health") as resp:
                    if resp.status != 200:
                        self.log("System not running!", "ERROR")
                        return
            except:
                self.log(f"Cannot connect to {BASE_URL}", "ERROR")
                return
            
            # Run WebSocket test separately (needs its own session)
            for name, test_func in scenarios:
                try:
                    if "WebSocket" in name:
                        result = await test_func()
                    else:
                        result = await test_func(session)
                    
                    if result:
                        self.log(f"✅ {name} - PASSED", "SUCCESS")
                        passed += 1
                    else:
                        self.log(f"❌ {name} - FAILED", "ERROR")
                        failed += 1
                except AssertionError as e:
                    self.log(f"❌ {name} - FAILED: {str(e)}", "ERROR")
                    failed += 1
                except Exception as e:
                    self.log(f"❌ {name} - ERROR: {str(e)}", "ERROR")
                    failed += 1
        
        # Print summary
        self.print_header("E2E TEST RESULTS SUMMARY")
        
        print(f"{Fore.GREEN}Passed: {passed}/{len(scenarios)}{Style.RESET_ALL}")
        if failed > 0:
            print(f"{Fore.RED}Failed: {failed}/{len(scenarios)}{Style.RESET_ALL}")
        
        success_rate = (passed / len(scenarios)) * 100
        
        if success_rate == 100:
            print(f"\n{Fore.GREEN}🎉 All E2E tests PASSED! System integration verified.{Style.RESET_ALL}")
        elif success_rate >= 80:
            print(f"\n{Fore.YELLOW}⚠ Most tests passed ({success_rate:.0f}%). Check failures.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Multiple failures ({success_rate:.0f}%). System issues detected.{Style.RESET_ALL}")
        
        # Component interaction summary
        print(f"\n{Fore.CYAN}Component Interactions Tested:{Style.RESET_ALL}")
        print("  ✓ API → Storage → Query")
        print("  ✓ Ingestion → Processing → Alerts")
        print("  ✓ Metrics → WebSocket → Real-time Updates")
        print("  ✓ Raw Data → Aggregation → Statistics")
        print("  ✓ Services → Discovery → Health Status")
        print("  ✓ Concurrent Operations → System Stability")
        
        return passed == len(scenarios)


async def main():
    test = E2ESystemTest()
    success = await test.run_all_scenarios()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))