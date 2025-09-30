import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, deque
import asyncio
from models import MetricData, AggregatedMetric, Alert, MetricType
import uuid


class MetricsProcessor:
    def __init__(self):
        self.buffer = defaultdict(lambda: deque(maxlen=1000))
        self.anomaly_thresholds = {
            MetricType.LATENCY: {"warning": 500, "critical": 1000},
            MetricType.ERROR_RATE: {"warning": 0.05, "critical": 0.1},
            MetricType.CPU: {"warning": 80, "critical": 95},
            MetricType.MEMORY: {"warning": 80, "critical": 95},
            MetricType.THROUGHPUT: {"warning": 100, "critical": 50}
        }
        self.alerts = deque(maxlen=100)
        self.window_data = defaultdict(list)
    
    def add_to_buffer(self, metric: MetricData):
        key = f"{metric.service}_{metric.metric_type.value}"
        self.buffer[key].append({
            "timestamp": metric.timestamp,
            "value": metric.value,
            "tags": metric.tags
        })
    
    def calculate_percentiles(self, values: List[float]) -> Tuple[float, float, float]:
        if not values:
            return 0.0, 0.0, 0.0
        
        sorted_values = np.sort(values)
        p50 = np.percentile(sorted_values, 50)
        p95 = np.percentile(sorted_values, 95)
        p99 = np.percentile(sorted_values, 99)
        
        return float(p50), float(p95), float(p99)
    
    def aggregate_metrics(
        self, 
        metrics: List[MetricData], 
        interval_minutes: int = 1
    ) -> List[AggregatedMetric]:
        grouped = defaultdict(list)
        
        for metric in metrics:
            interval_key = metric.timestamp.replace(
                second=0, 
                microsecond=0,
                minute=(metric.timestamp.minute // interval_minutes) * interval_minutes
            )
            key = (interval_key, metric.service, metric.metric_type)
            grouped[key].append(metric.value)
        
        aggregated = []
        for (timestamp, service, metric_type), values in grouped.items():
            p50, p95, p99 = self.calculate_percentiles(values)
            
            aggregated.append(AggregatedMetric(
                timestamp=timestamp,
                service=service,
                metric_type=metric_type,
                p50=p50,
                p95=p95,
                p99=p99,
                min=min(values),
                max=max(values),
                avg=sum(values) / len(values),
                count=len(values)
            ))
        
        return sorted(aggregated, key=lambda x: x.timestamp)
    
    def detect_anomaly(self, metric: MetricData) -> Optional[Alert]:
        thresholds = self.anomaly_thresholds.get(metric.metric_type)
        if not thresholds:
            return None
        
        severity = None
        threshold = None
        
        if metric.metric_type == MetricType.THROUGHPUT:
            if metric.value < thresholds["critical"]:
                severity = "critical"
                threshold = thresholds["critical"]
            elif metric.value < thresholds["warning"]:
                severity = "warning"
                threshold = thresholds["warning"]
        else:
            if metric.value > thresholds["critical"]:
                severity = "critical"
                threshold = thresholds["critical"]
            elif metric.value > thresholds["warning"]:
                severity = "warning"
                threshold = thresholds["warning"]
        
        if severity:
            alert = Alert(
                id=str(uuid.uuid4()),
                timestamp=metric.timestamp,
                service=metric.service,
                metric_type=metric.metric_type,
                severity=severity,
                message=f"{metric.metric_type.value} threshold exceeded for {metric.service}",
                value=metric.value,
                threshold=threshold
            )
            self.alerts.append(alert)
            return alert
        
        return None
    
    def calculate_sliding_window_rate(
        self, 
        service: str, 
        metric_type: MetricType,
        window_seconds: int = 60
    ) -> float:
        key = f"{service}_{metric_type.value}"
        buffer_data = list(self.buffer[key])
        
        if not buffer_data:
            return 0.0
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        
        recent_values = [
            item["value"] 
            for item in buffer_data 
            if item["timestamp"] > cutoff
        ]
        
        if not recent_values:
            return 0.0
        
        return sum(recent_values) / window_seconds
    
    def get_service_statistics(self, service: str) -> Dict:
        stats = {}
        
        for metric_type in MetricType:
            key = f"{service}_{metric_type.value}"
            buffer_data = list(self.buffer[key])
            
            if buffer_data:
                values = [item["value"] for item in buffer_data]
                p50, p95, p99 = self.calculate_percentiles(values)
                
                stats[metric_type.value] = {
                    "current": values[-1] if values else 0,
                    "p50": p50,
                    "p95": p95,
                    "p99": p99,
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values)
                }
        
        return stats
    
    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        return list(self.alerts)[-limit:]
    
    def clear_old_buffer_data(self, max_age_seconds: int = 3600):
        cutoff = datetime.now() - timedelta(seconds=max_age_seconds)
        
        for key in self.buffer:
            self.buffer[key] = deque(
                (item for item in self.buffer[key] if item["timestamp"] > cutoff),
                maxlen=1000
            )