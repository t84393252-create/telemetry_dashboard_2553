import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import List
from models import MetricData, MetricType
import json


class MetricsGenerator:
    def __init__(self):
        self.services = ["auth", "api", "database", "cache", "queue"]
        self.endpoints = {
            "auth": ["/login", "/logout", "/refresh", "/register"],
            "api": ["/users", "/products", "/orders", "/search"],
            "database": ["query", "insert", "update", "delete"],
            "cache": ["get", "set", "delete", "flush"],
            "queue": ["publish", "/consume", "/ack", "/nack"]
        }
        self.regions = ["us-east", "us-west", "eu-central", "ap-south"]
        self.running = False
        self.base_time = 0
    
    def generate_latency(self, service: str, time_factor: float) -> float:
        base_latencies = {
            "auth": 50,
            "api": 100,
            "database": 30,
            "cache": 5,
            "queue": 20
        }
        
        base = base_latencies.get(service, 50)
        
        sine_wave = math.sin(time_factor * 0.1) * 20
        noise = random.gauss(0, base * 0.1)
        
        if random.random() < 0.02:
            spike = random.uniform(base * 2, base * 5)
        else:
            spike = 0
        
        return max(1, base + sine_wave + noise + spike)
    
    def generate_throughput(self, service: str, time_factor: float) -> float:
        base_throughputs = {
            "auth": 1000,
            "api": 5000,
            "database": 2000,
            "cache": 10000,
            "queue": 3000
        }
        
        base = base_throughputs.get(service, 1000)
        
        daily_pattern = math.sin((time_factor % 1440) / 1440 * 2 * math.pi) * base * 0.3
        
        hourly_variation = math.sin(time_factor * 0.05) * base * 0.1
        noise = random.gauss(0, base * 0.05)
        
        if random.random() < 0.01:
            traffic_spike = random.uniform(base * 0.5, base * 1.5)
        else:
            traffic_spike = 0
        
        return max(10, base + daily_pattern + hourly_variation + noise + traffic_spike)
    
    def generate_error_rate(self, service: str, time_factor: float) -> float:
        base_error_rates = {
            "auth": 0.001,
            "api": 0.002,
            "database": 0.0005,
            "cache": 0.0001,
            "queue": 0.001
        }
        
        base = base_error_rates.get(service, 0.001)
        
        if random.random() < 0.005:
            error_spike = random.uniform(0.05, 0.15)
        else:
            error_spike = 0
        
        noise = random.gauss(0, base * 0.5)
        
        return max(0, min(1, base + noise + error_spike))
    
    def generate_cpu(self, service: str, time_factor: float) -> float:
        base_cpu = {
            "auth": 40,
            "api": 60,
            "database": 70,
            "cache": 30,
            "queue": 50
        }
        
        base = base_cpu.get(service, 50)
        
        load_pattern = math.sin(time_factor * 0.02) * 15
        noise = random.gauss(0, 5)
        
        if random.random() < 0.01:
            cpu_spike = random.uniform(20, 30)
        else:
            cpu_spike = 0
        
        return max(5, min(100, base + load_pattern + noise + cpu_spike))
    
    def generate_memory(self, service: str, time_factor: float) -> float:
        base_memory = {
            "auth": 50,
            "api": 65,
            "database": 80,
            "cache": 90,
            "queue": 55
        }
        
        base = base_memory.get(service, 60)
        
        gradual_increase = (time_factor % 1440) / 1440 * 10
        noise = random.gauss(0, 3)
        
        if random.random() < 0.005:
            memory_leak = random.uniform(5, 15)
        else:
            memory_leak = 0
        
        return max(10, min(100, base + gradual_increase + noise + memory_leak))
    
    def generate_batch(self) -> List[MetricData]:
        metrics = []
        current_time = datetime.now()
        self.base_time += 1
        
        for service in self.services:
            endpoints = self.endpoints[service]
            region = random.choice(self.regions)
            
            latency = self.generate_latency(service, self.base_time)
            metrics.append(MetricData(
                timestamp=current_time,
                service=service,
                metric_type=MetricType.LATENCY,
                value=latency,
                tags={
                    "endpoint": random.choice(endpoints),
                    "region": region,
                    "status_code": 200 if random.random() > 0.05 else 500
                }
            ))
            
            throughput = self.generate_throughput(service, self.base_time)
            metrics.append(MetricData(
                timestamp=current_time,
                service=service,
                metric_type=MetricType.THROUGHPUT,
                value=throughput,
                tags={"region": region}
            ))
            
            error_rate = self.generate_error_rate(service, self.base_time)
            metrics.append(MetricData(
                timestamp=current_time,
                service=service,
                metric_type=MetricType.ERROR_RATE,
                value=error_rate,
                tags={"region": region}
            ))
            
            cpu = self.generate_cpu(service, self.base_time)
            metrics.append(MetricData(
                timestamp=current_time,
                service=service,
                metric_type=MetricType.CPU,
                value=cpu,
                tags={"host": f"{service}-{random.randint(1, 3)}"}
            ))
            
            memory = self.generate_memory(service, self.base_time)
            metrics.append(MetricData(
                timestamp=current_time,
                service=service,
                metric_type=MetricType.MEMORY,
                value=memory,
                tags={"host": f"{service}-{random.randint(1, 3)}"}
            ))
        
        return metrics
    
    async def start_generation(self, callback):
        self.running = True
        while self.running:
            metrics = self.generate_batch()
            await callback(metrics)
            await asyncio.sleep(1)
    
    def stop_generation(self):
        self.running = False