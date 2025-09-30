# Telemetry Dashboard - Detailed Validation Walkthrough

## Overview
This guide walks through each validation step, explaining what's being tested and how to verify it manually.

---

## Step 1: Start the Backend Service

### What's Happening
The FastAPI backend starts and initializes:
- SQLite database for storing metrics
- WebSocket manager for real-time streaming
- Metrics generator that creates fake data
- Background cleanup tasks

### Manual Verification
```bash
# Start the backend
cd backend
python3 main.py

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
```

### What to Check
- Port 8000 is listening
- No error messages in console
- Database file `metrics.db` is created

---

## Step 2: Health Check Endpoint Test

### What's Being Tested
The `/metrics/health` endpoint confirms the API is responsive and can report system status.

### How It Works
```python
# The test sends:
GET http://localhost:8000/metrics/health

# Expected response:
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00",
    "services_count": 5
}
```

### Manual Test
```bash
curl http://localhost:8000/metrics/health | python3 -m json.tool
```

### What Success Looks Like
- HTTP 200 status code
- JSON response with "status": "healthy"
- Services count > 0 (should be 5 after generator starts)

---

## Step 3: Metric Ingestion Test

### What's Being Tested
The system can accept and store new metrics via POST requests.

### How It Works
```python
# Test sends a metric:
POST http://localhost:8000/metrics/ingest
{
    "timestamp": "2024-01-01T12:00:00Z",
    "service": "test_service",
    "metric_type": "latency",
    "value": 123.45,
    "tags": {"test": true}
}

# Expected response:
{"status": "success"}
```

### Manual Test
```bash
# Send a test metric
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "service": "manual_test",
    "metric_type": "latency",
    "value": 99.99,
    "tags": {"source": "manual"}
  }'
```

### What Success Looks Like
- Returns `{"status": "success"}`
- No errors in backend console
- Metric is stored in database

---

## Step 4: Metric Query Test

### What's Being Tested
The system can retrieve stored metrics within a time range.

### How It Works
```python
# Test queries for recent metrics:
POST http://localhost:8000/metrics/query
{
    "start_time": "2024-01-01T11:00:00Z",
    "end_time": "2024-01-01T12:00:00Z",
    "aggregation": "raw"
}

# Returns array of metrics:
{
    "data": [
        {
            "timestamp": "2024-01-01T11:55:00",
            "service": "auth",
            "metric_type": "latency",
            "value": 45.2,
            "tags": {...}
        },
        ...
    ]
}
```

### Manual Test
```bash
# Query last 5 minutes of data
curl -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%S')'Z",
    "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "aggregation": "raw"
  }' | python3 -m json.tool
```

### What Success Looks Like
- Returns array of metrics in "data" field
- Metrics are within requested time range
- Multiple services and metric types present

---

## Step 5: Services Discovery Test

### What's Being Tested
The system can identify all active services sending metrics.

### How It Works
```python
# Test requests service list:
GET http://localhost:8000/metrics/services

# Returns service health data:
{
    "services": [
        {
            "service": "auth",
            "status": "healthy",
            "metrics": {
                "latency": {"current": 45, "avg": 50},
                "error_rate": {"current": 0.01, "avg": 0.02}
            }
        },
        ...
    ]
}
```

### Manual Test
```bash
curl http://localhost:8000/metrics/services | python3 -m json.tool
```

### What Success Looks Like
- Returns 5 services: auth, api, database, cache, queue
- Each service has status (healthy/degraded/unhealthy)
- Metrics statistics are included

---

## Step 6: WebSocket Connection Test

### What's Being Tested
Real-time metric streaming via WebSocket works correctly.

### How It Works
1. Client connects to `ws://localhost:8000/ws/metrics`
2. Server sends initial batch of recent metrics
3. Server continuously sends new metrics as they're generated
4. Client receives JSON messages with metric data

### Manual Test
```python
# Save as test_ws.py and run
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/metrics"
    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")
        
        # Receive initial data
        message = await websocket.recv()
        data = json.loads(message)
        print(f"Initial data: {data['type']}, {len(data.get('data', []))} metrics")
        
        # Receive real-time updates for 5 seconds
        for i in range(5):
            message = await websocket.recv()
            data = json.loads(message)
            if data['type'] == 'metric':
                print(f"Received metric: {data['data']['service']} - {data['data']['metric_type']}")
            elif data['type'] == 'alert':
                print(f"Alert: {data['data']['message']}")
            await asyncio.sleep(1)

asyncio.run(test_websocket())
```

### What Success Looks Like
- Connects without error
- Receives "initial" message with historical data
- Continuously receives "metric" messages
- Each metric has timestamp, service, type, and value

---

## Step 7: Data Generation Verification

### What's Being Tested
The background generator is creating realistic metric patterns.

### How It Works
The generator creates metrics for 5 services every second:
- Latency (with sine wave patterns and occasional spikes)
- Throughput (with daily patterns)
- Error rates (mostly low with rare spikes)
- CPU usage (gradual changes)
- Memory usage (slow increase with resets)

### Manual Test
```bash
# Watch metrics being generated in real-time
watch -n 1 'curl -s -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d "{
    \"start_time\": \"$(date -u -d '10 seconds ago' '+%Y-%m-%dT%H:%M:%S')Z\",
    \"end_time\": \"$(date -u '+%Y-%m-%dT%H:%M:%S')Z\",
    \"aggregation\": \"raw\"
  }" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Metrics: {len(d.get('\''data'\'', []))}\"); [print(f\"  {m['\''service'\'']}: {m['\''metric_type'\'']}: {m['\''value'\'']:.2f}\") for m in d.get('\''data'\'', [])[:5]]"'
```

### What Success Looks Like
- New metrics appear every second
- 5 services × 5 metric types = 25 metrics per second
- Values show realistic patterns (not random)

---

## Step 8: Anomaly Detection Test

### What's Being Tested
The system detects and alerts on abnormal metric values.

### How It Works
```python
# Thresholds defined in backend/processor.py:
- Latency > 1000ms = critical
- Error rate > 10% = critical  
- CPU > 95% = critical
- Memory > 95% = critical
- Throughput < 50/s = critical
```

### Manual Test
```bash
# Send a high error rate metric
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "service": "test_anomaly",
    "metric_type": "error_rate",
    "value": 0.99,
    "tags": {}
  }'

# Check if alert was created
curl http://localhost:8000/metrics/alerts?limit=1 | python3 -m json.tool
```

### What Success Looks Like
- High-value metric triggers alert
- Alert appears in `/metrics/alerts` response
- Alert has severity level (warning/critical)
- WebSocket broadcasts alert to connected clients

---

## Step 9: Metric Aggregation Test

### What's Being Tested
The system can calculate percentiles and aggregations.

### How It Works
When querying with aggregation parameter:
- Groups metrics by time interval (1m, 5m, 1h)
- Calculates P50, P95, P99 percentiles
- Computes min, max, average values

### Manual Test
```bash
# Query with 1-minute aggregation
curl -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -u -d '10 minutes ago' '+%Y-%m-%dT%H:%M:%S')'Z",
    "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "aggregation": "1m"
  }' | python3 -m json.tool
```

### What Success Looks Like
```json
{
    "data": [
        {
            "timestamp": "2024-01-01T12:00:00",
            "service": "auth",
            "metric_type": "latency",
            "p50": 45.2,
            "p95": 98.5,
            "p99": 145.3,
            "min": 22.1,
            "max": 203.4,
            "avg": 52.3,
            "count": 60
        }
    ]
}
```

---

## Step 10: Frontend Dashboard Test

### What's Being Tested
The React frontend displays real-time data correctly.

### How It Works
1. Frontend connects to WebSocket
2. Receives and buffers metric stream
3. Updates visualizations in real-time
4. Shows alerts and service health

### Manual Test
```bash
# Start frontend (if not running)
cd frontend
npm run dev

# Open browser
open http://localhost:3000
```

### What to Verify
1. **Connection Status**: Green dot showing "Connected"
2. **Stat Cards**: Current values updating every second
3. **Line Chart**: P50/P95/P99 lines moving smoothly
4. **Area Chart**: Throughput stacking for all services
5. **Bar Chart**: Error rates for each service
6. **Heatmap**: Service health matrix with colors
7. **Alerts Panel**: Recent alerts appearing

---

## Step 11: Performance Validation

### What's Being Tested
System performance under load.

### Ingestion Throughput Test
```python
# Sends metrics rapidly for 10 seconds
# Measures metrics/second rate
# Good: >100/sec, Acceptable: >50/sec
```

### Query Latency Test
```python
# Sends 100 query requests
# Measures response times
# Good: <50ms avg, Acceptable: <100ms avg
```

### Manual Load Test
```bash
# Send 100 metrics rapidly
for i in {1..100}; do
  curl -X POST http://localhost:8000/metrics/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
      "service": "load_test",
      "metric_type": "latency",
      "value": '$((RANDOM % 100))'.0
    }' &
done
wait
echo "Sent 100 metrics"
```

---

## Complete Validation Checklist

Run through this checklist to ensure everything works:

### Backend API
- [ ] Health endpoint returns "healthy"
- [ ] Can ingest new metrics
- [ ] Can query historical data
- [ ] Services are discovered (5 total)
- [ ] Alerts endpoint returns data

### WebSocket
- [ ] Can connect to WebSocket
- [ ] Receives initial data batch
- [ ] Receives continuous metric updates
- [ ] Receives alert notifications

### Data Processing
- [ ] Generator creates metrics every second
- [ ] Anomalies trigger alerts
- [ ] Aggregations calculate percentiles
- [ ] Data persists in database

### Frontend
- [ ] Dashboard loads without errors
- [ ] WebSocket shows "Connected"
- [ ] All charts render correctly
- [ ] Real-time updates visible
- [ ] Filters work properly

### Performance
- [ ] Ingestion >50 metrics/second
- [ ] Query latency <100ms
- [ ] WebSocket latency <50ms
- [ ] Handles 100 concurrent connections

---

## Troubleshooting Common Issues

### "Connection Refused" Errors
- Backend not running: `cd backend && python3 main.py`
- Wrong port: Check it's using 8000

### No Data Showing
- Generator not running: Check backend console
- Time range issue: Query recent time window
- Database issue: Delete `metrics.db` and restart

### WebSocket Disconnects
- CORS issue: Check backend CORS settings
- Network issue: Try localhost instead of 127.0.0.1
- Browser issue: Check console for errors

### Poor Performance
- Too much data: Reduce retention period
- Slow queries: Add database indexes
- Memory issue: Restart backend

---

## Success Criteria

Your system is working correctly when:

✅ All API endpoints respond with 200 status
✅ WebSocket streams data continuously  
✅ 5 services generating metrics
✅ Charts update in real-time
✅ Alerts trigger on anomalies
✅ Performance meets targets
✅ No errors in console logs