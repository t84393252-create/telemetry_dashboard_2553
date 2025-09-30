# Validation Output Examples

This document shows what successful validation outputs look like for each test step.

## 1. Backend Health Check ✅

**Command:**
```bash
curl http://localhost:8000/metrics/health
```

**Successful Output:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T14:32:45.123456",
    "services_count": 5
}
```

**What This Means:**
- ✅ Backend is running
- ✅ Database is connected
- ✅ 5 services are being monitored

---

## 2. Metric Ingestion ✅

**Command:**
```bash
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2024-01-15T14:32:45Z", "service": "test", "metric_type": "latency", "value": 123.45}'
```

**Successful Output:**
```json
{
    "status": "success"
}
```

**If Anomaly Detected:**
```json
{
    "status": "success",
    "alert": {
        "id": "a4f2c891-5b21-4b2d-9c5f-3a8b4c5d6e7f",
        "timestamp": "2024-01-15T14:32:45Z",
        "service": "test",
        "metric_type": "error_rate",
        "severity": "critical",
        "message": "error_rate threshold exceeded for test",
        "value": 0.95,
        "threshold": 0.1
    }
}
```

---

## 3. Query Metrics ✅

**Command:**
```bash
curl -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{"start_time": "2024-01-15T14:30:00Z", "end_time": "2024-01-15T14:35:00Z", "aggregation": "raw"}'
```

**Successful Output:**
```json
{
    "data": [
        {
            "timestamp": "2024-01-15T14:32:45.123456",
            "service": "auth",
            "metric_type": "latency",
            "value": 45.23,
            "tags": {
                "endpoint": "/login",
                "region": "us-east",
                "status_code": 200
            }
        },
        {
            "timestamp": "2024-01-15T14:32:45.234567",
            "service": "api",
            "metric_type": "throughput",
            "value": 5432.1,
            "tags": {
                "region": "us-west"
            }
        },
        {
            "timestamp": "2024-01-15T14:32:45.345678",
            "service": "database",
            "metric_type": "cpu",
            "value": 67.8,
            "tags": {
                "host": "database-2"
            }
        }
    ]
}
```

**What This Shows:**
- ✅ Multiple services reporting
- ✅ Different metric types
- ✅ Tags with contextual data
- ✅ Precise timestamps

---

## 4. Service Discovery ✅

**Command:**
```bash
curl http://localhost:8000/metrics/services
```

**Successful Output:**
```json
{
    "services": [
        {
            "service": "auth",
            "status": "healthy",
            "metrics": {
                "latency": {
                    "current": 45.2,
                    "p50": 42.5,
                    "p95": 89.3,
                    "p99": 125.7,
                    "min": 22.1,
                    "max": 203.4,
                    "avg": 48.6
                },
                "error_rate": {
                    "current": 0.002,
                    "avg": 0.0015
                }
            }
        },
        {
            "service": "api",
            "status": "healthy",
            "metrics": {
                "latency": {
                    "current": 102.3,
                    "avg": 98.7
                }
            }
        },
        {
            "service": "database",
            "status": "degraded",
            "metrics": {
                "latency": {
                    "current": 523.4,
                    "avg": 487.2
                }
            }
        },
        {
            "service": "cache",
            "status": "healthy",
            "metrics": {}
        },
        {
            "service": "queue",
            "status": "healthy",
            "metrics": {}
        }
    ]
}
```

**Status Indicators:**
- 🟢 **healthy**: All metrics within normal range
- 🟡 **degraded**: Some metrics elevated but not critical
- 🔴 **unhealthy**: Critical thresholds exceeded

---

## 5. WebSocket Initial Connection ✅

**WebSocket Connect Response:**
```json
{
    "type": "initial",
    "data": [
        {
            "timestamp": "2024-01-15T14:32:44",
            "service": "auth",
            "metric_type": "latency",
            "value": 43.2,
            "tags": {}
        },
        {
            "timestamp": "2024-01-15T14:32:43",
            "service": "api",
            "metric_type": "throughput",
            "value": 4521.3,
            "tags": {}
        }
    ]
}
```

**Real-time Updates:**
```json
{
    "type": "metric",
    "data": {
        "timestamp": "2024-01-15T14:32:46",
        "service": "database",
        "metric_type": "latency",
        "value": 28.9,
        "tags": {
            "endpoint": "query",
            "region": "us-east"
        }
    }
}
```

**Alert Broadcast:**
```json
{
    "type": "alert",
    "data": {
        "id": "b7c9e2f4-8a1b-4c2d-9e3f-5a6b7c8d9e0f",
        "timestamp": "2024-01-15T14:32:47",
        "service": "api",
        "metric_type": "error_rate",
        "severity": "warning",
        "message": "error_rate threshold exceeded for api",
        "value": 0.08,
        "threshold": 0.05
    }
}
```

---

## 6. Aggregated Metrics ✅

**Command:**
```bash
curl -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{"start_time": "2024-01-15T14:00:00Z", "end_time": "2024-01-15T14:30:00Z", "aggregation": "1m"}'
```

**Successful Output:**
```json
{
    "data": [
        {
            "timestamp": "2024-01-15T14:00:00",
            "service": "auth",
            "metric_type": "latency",
            "p50": 45.2,
            "p95": 98.7,
            "p99": 156.3,
            "min": 21.3,
            "max": 234.5,
            "avg": 52.4,
            "count": 60
        },
        {
            "timestamp": "2024-01-15T14:01:00",
            "service": "auth",
            "metric_type": "latency",
            "p50": 46.8,
            "p95": 102.3,
            "p99": 178.9,
            "min": 19.7,
            "max": 267.8,
            "avg": 54.1,
            "count": 60
        }
    ]
}
```

**What Aggregation Provides:**
- **p50**: Median value (50th percentile)
- **p95**: 95% of values are below this
- **p99**: 99% of values are below this
- **count**: Number of data points in interval

---

## 7. Recent Alerts ✅

**Command:**
```bash
curl http://localhost:8000/metrics/alerts?limit=5
```

**Successful Output:**
```json
{
    "alerts": [
        {
            "id": "c8d9e0f1-9a2b-5c3d-0e4f-6b7c8d9e0f1a",
            "timestamp": "2024-01-15T14:31:23",
            "service": "database",
            "metric_type": "cpu",
            "severity": "critical",
            "message": "cpu threshold exceeded for database",
            "value": 96.5,
            "threshold": 95
        },
        {
            "id": "d9e0f1a2-0b3c-6d4e-1f5g-7c8d9e0f1a2b",
            "timestamp": "2024-01-15T14:30:15",
            "service": "api",
            "metric_type": "latency",
            "severity": "warning",
            "message": "latency threshold exceeded for api",
            "value": 678.9,
            "threshold": 500
        }
    ]
}
```

**Severity Levels:**
- 🔵 **info**: Informational alert
- 🟡 **warning**: Needs attention
- 🔴 **critical**: Immediate action required

---

## 8. Performance Test Results ✅

**Ingestion Throughput Test:**
```
Testing ingestion throughput for 5 seconds...
  Metrics/second............      125.3      
  Total sent................       626
  Errors....................         0
```

**Query Latency Test:**
```
Testing query latency (50 requests)...
  Average latency...........     32.45ms     
  P50 latency...............     28.12ms
  P95 latency...............     67.89ms
  P99 latency...............     94.23ms
  Errors....................         0
```

**WebSocket Latency:**
```
Testing WebSocket latency...
  Avg WS latency............      4.32ms     
  Messages/second...........       24.8
```

---

## 9. Health Check Script Output ✅

**Full System Healthy:**
```
========================================
  Telemetry Dashboard Health Check
========================================

System Components:
----------------------------------------
Checking Backend API... ✓ Running
  Status: healthy
  Services: 5

Checking Frontend... ✓ Running

Backend Services:
----------------------------------------
Checking WebSocket... ✓ Connected
  Real-time streaming active

Checking Data Generation... ✓ Active
  Metrics in last minute: 300

Checking Service Discovery... ✓ Found 5 services
  ✓ auth: healthy
  ✓ api: healthy
  ✓ database: healthy
  ✓ cache: healthy
  ✓ queue: healthy

Checking Alert System... ✓ Active
  Recent alerts: 2
  🟡 api: latency threshold exceeded for api
  🔴 database: cpu threshold exceeded for database

========================================
✓ System is fully operational

Dashboard URL: http://localhost:3000
========================================
```

---

## 10. Complete Validation Test Suite ✅

**All Tests Passing:**
```
==================================================
  Telemetry Dashboard System Validation
==================================================

Testing API Endpoints...
✓ Health Check Endpoint
✓ Metric Ingestion
✓ Metric Query
✓ Services Endpoint
✓ Alerts Endpoint

Testing WebSocket...
✓ WebSocket Streaming: Received 25 metrics in 5 seconds

Testing Data Processing...
✓ Data Generation: Services: 5, Metric Types: 5
✓ Anomaly Detection: Alert triggered for high error rate
✓ Metric Aggregation: Percentiles calculated

==================================================
  Test Results Summary
==================================================
  Passed: 10
  Failed: 0

✓ All tests passed! System is working correctly.
```

---

## Common Error Outputs ❌

### Backend Not Running:
```
Cannot connect to backend at http://localhost:8000
Please start the backend first:
  cd backend && python main.py
```

### No Data Being Generated:
```
Checking Data Generation... ⚠ No recent data
  Metrics in last minute: 0
```

### WebSocket Connection Failed:
```
❌ WebSocket test failed: [Errno 61] Connection refused
```

### High Error Rate:
```
Checking Service Discovery... ✓ Found 5 services
  ✓ auth: healthy
  ❌ api: unhealthy
  ✓ database: degraded
  ✓ cache: healthy
  ✓ queue: healthy
```

---

## Success Indicators Summary

Your system is working when you see:

| Component | Success Indicator |
|-----------|------------------|
| **Backend** | `"status": "healthy"` |
| **Ingestion** | `"status": "success"` |
| **Query** | Returns array of metrics |
| **Services** | 5 services discovered |
| **WebSocket** | Continuous metric stream |
| **Alerts** | Triggers on high values |
| **Aggregation** | Percentiles calculated |
| **Performance** | >50 metrics/sec, <100ms latency |
| **Frontend** | Real-time chart updates |

All validation scripts will show these patterns when the system is functioning correctly!