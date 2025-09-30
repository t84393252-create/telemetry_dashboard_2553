# Telemetry Dashboard - Testing Guide

## Overview

This document describes how to validate and test the Telemetry Dashboard system to ensure it's working correctly.

## Quick Start Validation

### 1. Automated Test Suite
Run the complete test suite with a single command:

```bash
# Run all tests (starts services automatically)
./run_tests.sh

# Quick tests only (skip performance tests)
./run_tests.sh --quick

# API tests only (skip frontend)
./run_tests.sh --skip-frontend
```

### 2. Manual Health Check
Check if services are running:

```bash
# Run health check
./health_check.sh
```

## Available Test Scripts

### 1. `validate_system.py`
Comprehensive validation of all system components:

- ✅ API endpoint testing
- ✅ WebSocket connectivity
- ✅ Data generation verification
- ✅ Anomaly detection
- ✅ Metric aggregation
- ✅ Service discovery

**Run individually:**
```bash
python3 validate_system.py
```

### 2. `performance_test.py`
Performance benchmarking:

- 📊 Ingestion throughput (metrics/second)
- ⚡ Query latency (P50, P95, P99)
- 🔌 WebSocket latency
- 🔄 Concurrent connection handling
- 💾 Data retention validation

**Run individually:**
```bash
python3 performance_test.py
```

### 3. `health_check.sh`
Quick system health verification:

- 🟢 Service status
- 📡 WebSocket connectivity
- 📈 Data generation status
- 🔔 Alert system status
- 🏥 Service health matrix

**Run individually:**
```bash
./health_check.sh
```

## Manual Testing Steps

### 1. Start the System

```bash
# Using Docker
docker-compose up -d

# OR manually
cd backend && python3 main.py &
cd frontend && npm run dev &
```

### 2. Verify Backend API

```bash
# Check health
curl http://localhost:8000/metrics/health

# Query recent metrics
curl -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -u -d '1 minute ago' '+%Y-%m-%dT%H:%M:%S')'Z",
    "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "aggregation": "raw"
  }'

# Get services
curl http://localhost:8000/metrics/services

# Check alerts
curl http://localhost:8000/metrics/alerts
```

### 3. Test WebSocket Connection

```python
# Python WebSocket test
python3 -c "
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8000/ws/metrics') as ws:
        print('Connected to WebSocket')
        for i in range(5):
            msg = await ws.recv()
            data = json.loads(msg)
            print(f'Received: {data['type']}')

asyncio.run(test())
"
```

### 4. Verify Frontend Dashboard

1. Open http://localhost:3000 in browser
2. Check for:
   - ✅ Real-time metric updates
   - ✅ All charts rendering
   - ✅ WebSocket connection indicator (green)
   - ✅ Service filter dropdown populated
   - ✅ Stat cards showing current values

### 5. Test Metric Ingestion

```bash
# Send a test metric
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "service": "test_service",
    "metric_type": "latency",
    "value": 150.5,
    "tags": {"endpoint": "/test", "region": "us-east"}
  }'
```

### 6. Test Anomaly Detection

```bash
# Send metric that triggers alert
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "service": "test_service",
    "metric_type": "error_rate",
    "value": 0.95,
    "tags": {"test": true}
  }'

# Check if alert was created
curl http://localhost:8000/metrics/alerts?limit=1
```

## Expected Test Results

### System Validation (`validate_system.py`)
All tests should pass:
- ✅ Health Check Endpoint
- ✅ Metric Ingestion
- ✅ Metric Query
- ✅ Services Endpoint
- ✅ Alerts Endpoint
- ✅ WebSocket Streaming
- ✅ Data Generation
- ✅ Anomaly Detection
- ✅ Metric Aggregation

### Performance Benchmarks (`performance_test.py`)

**Good Performance:**
- Ingestion: >100 metrics/second
- Query latency: <50ms average
- WebSocket latency: <10ms
- Concurrent connections: 100% success rate

**Acceptable Performance:**
- Ingestion: 50-100 metrics/second
- Query latency: 50-100ms average
- WebSocket latency: 10-50ms
- Concurrent connections: >95% success rate

### Health Check (`health_check.sh`)

**Healthy System:**
- Backend API: ✅ Running
- Frontend: ✅ Running
- WebSocket: ✅ Connected
- Data Generation: ✅ Active
- Services: 5 discovered
- All services: healthy status

## Troubleshooting

### Backend Won't Start
```bash
# Check if port is in use
lsof -i :8000

# Check Python dependencies
cd backend
pip install -r requirements.txt

# Check logs
python3 main.py
```

### Frontend Won't Start
```bash
# Check if port is in use
lsof -i :3000

# Reinstall dependencies
cd frontend
rm -rf node_modules
npm install

# Check logs
npm run dev
```

### WebSocket Connection Fails
1. Check CORS settings in backend
2. Verify backend is running
3. Check browser console for errors
4. Try different browser

### No Data Showing
1. Check if data generator is running
2. Query recent metrics via API
3. Check browser console for WebSocket errors
4. Verify time ranges in queries

## Performance Tuning

If tests show poor performance:

1. **Reduce data retention**: Edit `backend/main.py` cleanup intervals
2. **Increase buffer sizes**: Edit `backend/processor.py` buffer settings
3. **Optimize queries**: Add database indexes in `backend/storage.py`
4. **Reduce generation rate**: Edit `backend/generator.py` sleep interval

## CI/CD Integration

For continuous integration:

```yaml
# Example GitHub Actions workflow
name: Test Telemetry Dashboard

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - uses: actions/setup-node@v2
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install -r requirements-test.txt
          cd frontend && npm install
      
      - name: Run tests
        run: ./run_tests.sh --quick --skip-frontend
```

## Summary

The validation suite ensures:
1. **Functionality**: All endpoints and features work
2. **Performance**: System meets performance requirements
3. **Reliability**: WebSocket connections are stable
4. **Data Integrity**: Metrics are stored and retrieved correctly
5. **Real-time Updates**: Dashboard receives live data

Run `./run_tests.sh` for complete validation!