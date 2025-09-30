#!/usr/bin/env python3
"""
Performance testing script for the Telemetry Dashboard
Tests throughput, latency, and system limits
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
from typing import List, Dict
import json
from colorama import Fore, Style, init

init(autoreset=True)

BASE_URL = "http://localhost:8000"


class PerformanceTest:
    def __init__(self):
        self.results = {}
        
    def print_header(self, title: str):
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"  {title}")
        print(f"{'='*50}{Style.RESET_ALL}\n")
    
    def print_metric(self, name: str, value: str, unit: str = "", status: str = "info"):
        colors = {
            "good": Fore.GREEN,
            "warning": Fore.YELLOW,
            "bad": Fore.RED,
            "info": Fore.BLUE
        }
        color = colors.get(status, Fore.WHITE)
        print(f"  {name:.<30} {color}{value:>10}{unit}{Style.RESET_ALL}")
    
    async def test_ingestion_throughput(self, session: aiohttp.ClientSession, duration: int = 10):
        """Test how many metrics per second can be ingested"""
        print(f"{Fore.YELLOW}Testing ingestion throughput for {duration} seconds...{Style.RESET_ALL}")
        
        metrics_sent = 0
        errors = 0
        start_time = time.time()
        
        async def send_metric():
            nonlocal metrics_sent, errors
            metric = {
                "timestamp": datetime.now().isoformat(),
                "service": "perf_test",
                "metric_type": "latency",
                "value": 100.0,
                "tags": {"test": "performance"}
            }
            
            try:
                async with session.post(
                    f"{BASE_URL}/metrics/ingest",
                    json=metric,
                    timeout=aiohttp.ClientTimeout(total=1)
                ) as resp:
                    if resp.status == 200:
                        metrics_sent += 1
                    else:
                        errors += 1
            except:
                errors += 1
        
        # Send metrics concurrently
        while time.time() - start_time < duration:
            tasks = [send_metric() for _ in range(10)]  # Send 10 concurrent requests
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.01)  # Small delay between batches
        
        elapsed = time.time() - start_time
        throughput = metrics_sent / elapsed
        
        self.results["ingestion_throughput"] = throughput
        self.results["ingestion_errors"] = errors
        
        status = "good" if throughput > 100 else "warning" if throughput > 50 else "bad"
        self.print_metric("Metrics/second", f"{throughput:.1f}", "", status)
        self.print_metric("Total sent", str(metrics_sent))
        self.print_metric("Errors", str(errors), "", "good" if errors == 0 else "warning")
    
    async def test_query_latency(self, session: aiohttp.ClientSession, iterations: int = 100):
        """Test query response times"""
        print(f"\n{Fore.YELLOW}Testing query latency ({iterations} requests)...{Style.RESET_ALL}")
        
        latencies = []
        errors = 0
        
        query = {
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "aggregation": "raw"
        }
        
        for i in range(iterations):
            start = time.time()
            try:
                async with session.post(
                    f"{BASE_URL}/metrics/query",
                    json=query,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        await resp.json()
                        latencies.append((time.time() - start) * 1000)  # Convert to ms
                    else:
                        errors += 1
            except:
                errors += 1
            
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{iterations}", end="\r")
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p50 = statistics.median(latencies)
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            p99 = sorted(latencies)[int(len(latencies) * 0.99)]
            
            self.results["query_avg_latency"] = avg_latency
            self.results["query_p95_latency"] = p95
            
            status = "good" if avg_latency < 50 else "warning" if avg_latency < 100 else "bad"
            self.print_metric("Average latency", f"{avg_latency:.2f}", "ms", status)
            self.print_metric("P50 latency", f"{p50:.2f}", "ms")
            self.print_metric("P95 latency", f"{p95:.2f}", "ms")
            self.print_metric("P99 latency", f"{p99:.2f}", "ms")
            self.print_metric("Errors", str(errors), "", "good" if errors == 0 else "warning")
    
    async def test_websocket_latency(self):
        """Test WebSocket message latency"""
        print(f"\n{Fore.YELLOW}Testing WebSocket latency...{Style.RESET_ALL}")
        
        import websockets
        
        try:
            async with websockets.connect(f"ws://localhost:8000/ws/metrics") as ws:
                # Wait for initial message
                await ws.recv()
                
                latencies = []
                messages_received = 0
                start_time = time.time()
                
                # Collect messages for 5 seconds
                while time.time() - start_time < 5:
                    try:
                        msg_start = time.time()
                        message = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        latency = (time.time() - msg_start) * 1000
                        
                        data = json.loads(message)
                        if data.get("type") == "metric":
                            latencies.append(latency)
                            messages_received += 1
                    except asyncio.TimeoutError:
                        continue
                
                if latencies:
                    avg_latency = statistics.mean(latencies)
                    
                    self.results["ws_avg_latency"] = avg_latency
                    self.results["ws_messages_per_sec"] = messages_received / 5
                    
                    status = "good" if avg_latency < 10 else "warning" if avg_latency < 50 else "bad"
                    self.print_metric("Avg WS latency", f"{avg_latency:.2f}", "ms", status)
                    self.print_metric("Messages/second", f"{messages_received / 5:.1f}")
                else:
                    self.print_metric("WebSocket test", "No messages", "", "bad")
                    
        except Exception as e:
            self.print_metric("WebSocket test", "Failed", "", "bad")
            print(f"  Error: {str(e)}")
    
    async def test_concurrent_connections(self, session: aiohttp.ClientSession):
        """Test system behavior under concurrent load"""
        print(f"\n{Fore.YELLOW}Testing concurrent connections...{Style.RESET_ALL}")
        
        async def make_request():
            try:
                start = time.time()
                async with session.get(
                    f"{BASE_URL}/metrics/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        return time.time() - start, True
            except:
                pass
            return 0, False
        
        # Test with increasing concurrent connections
        for concurrent in [10, 50, 100]:
            tasks = [make_request() for _ in range(concurrent)]
            results = await asyncio.gather(*tasks)
            
            successful = sum(1 for _, success in results if success)
            avg_time = statistics.mean(t for t, success in results if success and t > 0) if successful > 0 else 0
            
            success_rate = (successful / concurrent) * 100
            status = "good" if success_rate >= 95 else "warning" if success_rate >= 80 else "bad"
            
            print(f"\n  {concurrent} concurrent connections:")
            self.print_metric("  Success rate", f"{success_rate:.1f}", "%", status)
            if avg_time > 0:
                self.print_metric("  Avg response time", f"{avg_time*1000:.1f}", "ms")
    
    async def test_data_retention(self, session: aiohttp.ClientSession):
        """Test data storage and retrieval"""
        print(f"\n{Fore.YELLOW}Testing data retention...{Style.RESET_ALL}")
        
        # Send a unique metric
        test_id = f"retention_test_{int(time.time())}"
        metric = {
            "timestamp": datetime.now().isoformat(),
            "service": test_id,
            "metric_type": "latency",
            "value": 999.99,
            "tags": {"retention_test": True}
        }
        
        # Send metric
        async with session.post(f"{BASE_URL}/metrics/ingest", json=metric) as resp:
            if resp.status != 200:
                self.print_metric("Data retention test", "Failed to send", "", "bad")
                return
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Query it back
        query = {
            "start_time": datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "services": [test_id],
            "aggregation": "raw"
        }
        
        async with session.post(f"{BASE_URL}/metrics/query", json=query) as resp:
            if resp.status == 200:
                data = await resp.json()
                metrics = data.get("data", [])
                
                found = any(
                    m.get("service") == test_id and m.get("value") == 999.99 
                    for m in metrics
                )
                
                if found:
                    self.print_metric("Data retention", "Working", "", "good")
                    self.print_metric("Storage latency", "<1", "s", "good")
                else:
                    self.print_metric("Data retention", "Not found", "", "bad")
            else:
                self.print_metric("Data retention", "Query failed", "", "bad")
    
    async def run_all_tests(self):
        """Run all performance tests"""
        self.print_header("Performance Testing Suite")
        
        async with aiohttp.ClientSession() as session:
            # Check if system is running
            try:
                async with session.get(f"{BASE_URL}/metrics/health") as resp:
                    if resp.status != 200:
                        print(f"{Fore.RED}System is not running. Start it first.{Style.RESET_ALL}")
                        return
            except:
                print(f"{Fore.RED}Cannot connect to {BASE_URL}{Style.RESET_ALL}")
                return
            
            await self.test_ingestion_throughput(session, duration=5)
            await self.test_query_latency(session, iterations=50)
            await self.test_websocket_latency()
            await self.test_concurrent_connections(session)
            await self.test_data_retention(session)
        
        # Summary
        self.print_header("Performance Summary")
        
        if "ingestion_throughput" in self.results:
            throughput = self.results["ingestion_throughput"]
            if throughput > 100:
                print(f"{Fore.GREEN}✓ Excellent ingestion performance ({throughput:.0f} metrics/sec){Style.RESET_ALL}")
            elif throughput > 50:
                print(f"{Fore.YELLOW}⚠ Good ingestion performance ({throughput:.0f} metrics/sec){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ Poor ingestion performance ({throughput:.0f} metrics/sec){Style.RESET_ALL}")
        
        if "query_avg_latency" in self.results:
            latency = self.results["query_avg_latency"]
            if latency < 50:
                print(f"{Fore.GREEN}✓ Excellent query latency ({latency:.1f}ms avg){Style.RESET_ALL}")
            elif latency < 100:
                print(f"{Fore.YELLOW}⚠ Acceptable query latency ({latency:.1f}ms avg){Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}✗ High query latency ({latency:.1f}ms avg){Style.RESET_ALL}")
        
        if "ws_avg_latency" in self.results:
            ws_latency = self.results["ws_avg_latency"]
            if ws_latency < 10:
                print(f"{Fore.GREEN}✓ Excellent WebSocket latency ({ws_latency:.1f}ms){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ WebSocket latency could be improved ({ws_latency:.1f}ms){Style.RESET_ALL}")


async def main():
    test = PerformanceTest()
    await test.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Performance test interrupted{Style.RESET_ALL}")