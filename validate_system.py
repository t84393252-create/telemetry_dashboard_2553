#!/usr/bin/env python3
"""
Comprehensive validation script for the Telemetry Dashboard System
"""

import asyncio
import aiohttp
import websockets
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
from colorama import Fore, Style, init

init(autoreset=True)

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/metrics"

class SystemValidator:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        if passed:
            print(f"{Fore.GREEN}✓ {test_name}{Style.RESET_ALL}")
            self.passed += 1
        else:
            print(f"{Fore.RED}✗ {test_name}: {details}{Style.RESET_ALL}")
            self.failed += 1
        self.results.append({"test": test_name, "passed": passed, "details": details})
    
    async def test_health_endpoint(self, session: aiohttp.ClientSession):
        """Test the health check endpoint"""
        try:
            async with session.get(f"{BASE_URL}/metrics/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result(
                        "Health Check Endpoint", 
                        "status" in data and data["status"] == "healthy"
                    )
                else:
                    self.log_result("Health Check Endpoint", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Health Check Endpoint", False, str(e))
    
    async def test_metric_ingestion(self, session: aiohttp.ClientSession):
        """Test metric ingestion endpoint"""
        test_metric = {
            "timestamp": datetime.now().isoformat(),
            "service": "test_service",
            "metric_type": "latency",
            "value": 123.45,
            "tags": {"test": True}
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/metrics/ingest",
                json=test_metric
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result(
                        "Metric Ingestion", 
                        data.get("status") == "success"
                    )
                else:
                    self.log_result("Metric Ingestion", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Metric Ingestion", False, str(e))
    
    async def test_metric_query(self, session: aiohttp.ClientSession):
        """Test metric query endpoint"""
        query = {
            "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "services": None,
            "metric_types": None,
            "aggregation": "raw"
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/metrics/query",
                json=query
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result(
                        "Metric Query", 
                        "data" in data and isinstance(data["data"], list)
                    )
                else:
                    self.log_result("Metric Query", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Metric Query", False, str(e))
    
    async def test_services_endpoint(self, session: aiohttp.ClientSession):
        """Test services list endpoint"""
        try:
            async with session.get(f"{BASE_URL}/metrics/services") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    has_services = "services" in data and len(data["services"]) > 0
                    self.log_result(
                        "Services Endpoint", 
                        has_services,
                        f"Found {len(data.get('services', []))} services" if has_services else "No services found"
                    )
                else:
                    self.log_result("Services Endpoint", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Services Endpoint", False, str(e))
    
    async def test_alerts_endpoint(self, session: aiohttp.ClientSession):
        """Test alerts endpoint"""
        try:
            async with session.get(f"{BASE_URL}/metrics/alerts?limit=10") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log_result(
                        "Alerts Endpoint", 
                        "alerts" in data and isinstance(data["alerts"], list)
                    )
                else:
                    self.log_result("Alerts Endpoint", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Alerts Endpoint", False, str(e))
    
    async def test_websocket_connection(self):
        """Test WebSocket connection and data streaming"""
        try:
            async with websockets.connect(WS_URL) as websocket:
                # Wait for initial data
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(message)
                
                initial_ok = data.get("type") == "initial" and "data" in data
                
                if initial_ok:
                    # Wait for real-time updates
                    metrics_received = 0
                    start_time = time.time()
                    
                    while time.time() - start_time < 5:  # Collect for 5 seconds
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1)
                            data = json.loads(message)
                            if data.get("type") == "metric":
                                metrics_received += 1
                        except asyncio.TimeoutError:
                            continue
                    
                    self.log_result(
                        "WebSocket Streaming", 
                        metrics_received > 0,
                        f"Received {metrics_received} metrics in 5 seconds"
                    )
                else:
                    self.log_result("WebSocket Streaming", False, "No initial data received")
                    
        except Exception as e:
            self.log_result("WebSocket Streaming", False, str(e))
    
    async def test_data_generation(self, session: aiohttp.ClientSession):
        """Test that data is being generated"""
        await asyncio.sleep(2)  # Wait for generator to create some data
        
        query = {
            "start_time": (datetime.now() - timedelta(minutes=1)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "aggregation": "raw"
        }
        
        try:
            async with session.post(f"{BASE_URL}/metrics/query", json=query) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    metrics = data.get("data", [])
                    
                    # Check for variety in data
                    services = set(m["service"] for m in metrics)
                    metric_types = set(m["metric_type"] for m in metrics)
                    
                    self.log_result(
                        "Data Generation", 
                        len(services) >= 5 and len(metric_types) >= 5,
                        f"Services: {len(services)}, Metric Types: {len(metric_types)}"
                    )
                else:
                    self.log_result("Data Generation", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Data Generation", False, str(e))
    
    async def test_anomaly_detection(self, session: aiohttp.ClientSession):
        """Test anomaly detection by sending high-value metrics"""
        # Send a metric that should trigger an alert
        anomaly_metric = {
            "timestamp": datetime.now().isoformat(),
            "service": "test_service",
            "metric_type": "error_rate",
            "value": 0.95,  # 95% error rate should trigger alert
            "tags": {"test": True}
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/metrics/ingest",
                json=anomaly_metric
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    has_alert = "alert" in data and data["alert"] is not None
                    self.log_result(
                        "Anomaly Detection", 
                        has_alert,
                        "Alert triggered for high error rate" if has_alert else "No alert generated"
                    )
                else:
                    self.log_result("Anomaly Detection", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Anomaly Detection", False, str(e))
    
    async def test_aggregation(self, session: aiohttp.ClientSession):
        """Test metric aggregation"""
        query = {
            "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now().isoformat(),
            "aggregation": "1m"
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/metrics/query",
                json=query
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    metrics = data.get("data", [])
                    
                    if metrics:
                        # Check if aggregated data has expected fields
                        sample = metrics[0]
                        has_percentiles = all(
                            key in sample for key in ["p50", "p95", "p99", "min", "max", "avg"]
                        )
                        self.log_result(
                            "Metric Aggregation", 
                            has_percentiles,
                            "Percentiles calculated" if has_percentiles else "Missing aggregation fields"
                        )
                    else:
                        self.log_result("Metric Aggregation", False, "No aggregated data")
                else:
                    self.log_result("Metric Aggregation", False, f"Status: {resp.status}")
        except Exception as e:
            self.log_result("Metric Aggregation", False, str(e))
    
    async def run_all_tests(self):
        """Run all validation tests"""
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"  Telemetry Dashboard System Validation")
        print(f"{'='*50}{Style.RESET_ALL}\n")
        
        async with aiohttp.ClientSession() as session:
            print(f"{Fore.YELLOW}Testing API Endpoints...{Style.RESET_ALL}")
            await self.test_health_endpoint(session)
            await self.test_metric_ingestion(session)
            await self.test_metric_query(session)
            await self.test_services_endpoint(session)
            await self.test_alerts_endpoint(session)
            
            print(f"\n{Fore.YELLOW}Testing WebSocket...{Style.RESET_ALL}")
            await self.test_websocket_connection()
            
            print(f"\n{Fore.YELLOW}Testing Data Processing...{Style.RESET_ALL}")
            await self.test_data_generation(session)
            await self.test_anomaly_detection(session)
            await self.test_aggregation(session)
        
        # Print summary
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"  Test Results Summary")
        print(f"{'='*50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Passed: {self.passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}  Failed: {self.failed}{Style.RESET_ALL}")
        
        success_rate = (self.passed / (self.passed + self.failed)) * 100 if (self.passed + self.failed) > 0 else 0
        
        if success_rate == 100:
            print(f"\n{Fore.GREEN}✓ All tests passed! System is working correctly.{Style.RESET_ALL}")
        elif success_rate >= 80:
            print(f"\n{Fore.YELLOW}⚠ Most tests passed ({success_rate:.0f}%). Check failed tests.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}✗ Many tests failed ({success_rate:.0f}%). System needs attention.{Style.RESET_ALL}")
        
        return self.passed, self.failed


async def main():
    validator = SystemValidator()
    
    # Check if backend is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/") as resp:
                if resp.status != 200:
                    print(f"{Fore.RED}Backend is not responding. Please start it first:{Style.RESET_ALL}")
                    print(f"  cd backend && python main.py")
                    return
    except:
        print(f"{Fore.RED}Cannot connect to backend at {BASE_URL}{Style.RESET_ALL}")
        print(f"Please start the backend first:")
        print(f"  cd backend && python main.py")
        return
    
    await validator.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Validation interrupted by user{Style.RESET_ALL}")
        sys.exit(0)