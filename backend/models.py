from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Optional, List, Literal, Any
from enum import Enum


class MetricType(str, Enum):
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    CPU = "cpu"
    MEMORY = "memory"


class MetricData(BaseModel):
    timestamp: datetime
    service: str
    metric_type: MetricType
    value: float
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MetricQuery(BaseModel):
    start_time: datetime
    end_time: datetime
    services: Optional[List[str]] = None
    metric_types: Optional[List[MetricType]] = None
    aggregation: Optional[Literal["raw", "1m", "5m", "1h"]] = "raw"


class AggregatedMetric(BaseModel):
    timestamp: datetime
    service: str
    metric_type: MetricType
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    avg: float
    count: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ServiceHealth(BaseModel):
    service: str
    status: Literal["healthy", "degraded", "unhealthy"]
    uptime_percentage: float
    error_rate: float
    avg_latency: float
    last_seen: datetime


class Alert(BaseModel):
    id: str
    timestamp: datetime
    service: str
    metric_type: MetricType
    severity: Literal["info", "warning", "critical"]
    message: str
    value: float
    threshold: float