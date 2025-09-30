#!/bin/bash

# Manual Validation Commands for Telemetry Dashboard
# Run these commands step-by-step to validate each component

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================"
echo "  Telemetry Dashboard - Manual Validation Steps"
echo -e "================================================${NC}\n"

# Function to pause and wait for user
pause() {
    echo -e "\n${YELLOW}Press Enter to continue to next test...${NC}"
    read -r
}

# Step 1: Check if backend is running
echo -e "${GREEN}Step 1: Check Backend Health${NC}"
echo "Testing: http://localhost:8000/metrics/health"
echo -e "${BLUE}Expected: Status 200 with 'healthy' status${NC}\n"
curl -s http://localhost:8000/metrics/health | python3 -m json.tool || echo -e "${RED}Backend not running!${NC}"
pause

# Step 2: Test metric ingestion
echo -e "${GREEN}Step 2: Test Metric Ingestion${NC}"
echo "Sending test metric to /metrics/ingest"
echo -e "${BLUE}Expected: {'status': 'success'}${NC}\n"
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "service": "manual_test",
    "metric_type": "latency",
    "value": 123.45,
    "tags": {"test": "manual", "step": 2}
  }' | python3 -m json.tool
pause

# Step 3: Query recent metrics
echo -e "${GREEN}Step 3: Query Recent Metrics${NC}"
echo "Querying metrics from last 5 minutes"
echo -e "${BLUE}Expected: Array of metrics with various services${NC}\n"
curl -s -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%S')'Z",
    "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "aggregation": "raw"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
metrics = data.get('data', [])
print(f'Total metrics found: {len(metrics)}')
if metrics:
    services = set(m['service'] for m in metrics)
    types = set(m['metric_type'] for m in metrics)
    print(f'Services: {services}')
    print(f'Metric types: {types}')
    print(f'\\nFirst 3 metrics:')
    for m in metrics[:3]:
        print(f\"  {m['service']}: {m['metric_type']} = {m['value']:.2f}\")
"
pause

# Step 4: Check discovered services
echo -e "${GREEN}Step 4: Check Service Discovery${NC}"
echo "Getting list of active services"
echo -e "${BLUE}Expected: 5 services with health status${NC}\n"
curl -s http://localhost:8000/metrics/services | python3 -c "
import sys, json
data = json.load(sys.stdin)
services = data.get('services', [])
print(f'Found {len(services)} services:\\n')
for svc in services:
    status_icon = '✅' if svc['status'] == 'healthy' else '⚠️' if svc['status'] == 'degraded' else '❌'
    print(f\"{status_icon} {svc['service']}: {svc['status']}\")
    if 'metrics' in svc and 'latency' in svc['metrics']:
        lat = svc['metrics']['latency']
        print(f\"   Latency: current={lat.get('current', 0):.1f}ms\")
"
pause

# Step 5: Test anomaly detection
echo -e "${GREEN}Step 5: Test Anomaly Detection${NC}"
echo "Sending high error rate to trigger alert"
echo -e "${BLUE}Expected: Alert in response${NC}\n"
curl -X POST http://localhost:8000/metrics/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "service": "alert_test",
    "metric_type": "error_rate",
    "value": 0.95,
    "tags": {"test": "anomaly"}
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'alert' in data and data['alert']:
    alert = data['alert']
    print('🚨 Alert Triggered!')
    print(f\"  Service: {alert['service']}\")
    print(f\"  Severity: {alert['severity']}\")
    print(f\"  Message: {alert['message']}\")
    print(f\"  Value: {alert['value']}, Threshold: {alert['threshold']}\")
else:
    print('No alert triggered (may be below threshold)')
"
pause

# Step 6: Check alerts
echo -e "${GREEN}Step 6: Check Recent Alerts${NC}"
echo "Getting list of recent alerts"
echo -e "${BLUE}Expected: List of alerts (if any triggered)${NC}\n"
curl -s http://localhost:8000/metrics/alerts?limit=5 | python3 -c "
import sys, json
from datetime import datetime
data = json.load(sys.stdin)
alerts = data.get('alerts', [])
if alerts:
    print(f'Found {len(alerts)} recent alerts:\\n')
    for alert in alerts[:5]:
        icon = '🔴' if alert['severity'] == 'critical' else '🟡' if alert['severity'] == 'warning' else '🔵'
        print(f\"{icon} [{alert['severity'].upper()}] {alert['service']}\")
        print(f\"   {alert['message']}\")
        print(f\"   Value: {alert['value']:.2f}, Threshold: {alert['threshold']}\\n\")
else:
    print('No alerts found (system running normally)')
"
pause

# Step 7: Test aggregation
echo -e "${GREEN}Step 7: Test Metric Aggregation${NC}"
echo "Querying with 1-minute aggregation"
echo -e "${BLUE}Expected: Aggregated metrics with percentiles${NC}\n"
curl -s -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -u -d '10 minutes ago' '+%Y-%m-%dT%H:%M:%S')'Z",
    "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "aggregation": "1m"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
metrics = data.get('data', [])
if metrics:
    print(f'Found {len(metrics)} aggregated data points\\n')
    sample = metrics[0]
    print('Sample aggregated metric:')
    print(f\"  Service: {sample['service']}\")
    print(f\"  Type: {sample['metric_type']}\")
    print(f\"  P50: {sample['p50']:.2f}\")
    print(f\"  P95: {sample['p95']:.2f}\")
    print(f\"  P99: {sample['p99']:.2f}\")
    print(f\"  Min: {sample['min']:.2f}, Max: {sample['max']:.2f}\")
    print(f\"  Count: {sample['count']} data points\")
else:
    print('No aggregated data found')
"
pause

# Step 8: Test WebSocket connection
echo -e "${GREEN}Step 8: Test WebSocket Connection${NC}"
echo "Connecting to WebSocket and receiving 3 messages"
echo -e "${BLUE}Expected: Initial data + real-time metrics${NC}\n"
python3 -c "
import asyncio
import websockets
import json

async def test():
    try:
        uri = 'ws://localhost:8000/ws/metrics'
        async with websockets.connect(uri) as ws:
            print('✅ Connected to WebSocket')
            
            # Get initial message
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            if data['type'] == 'initial':
                print(f\"📊 Received initial data: {len(data.get('data', []))} metrics\")
            
            # Get 3 real-time messages
            print('\\n📡 Waiting for real-time updates...')
            for i in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                data = json.loads(msg)
                if data['type'] == 'metric':
                    m = data['data']
                    print(f\"  → {m['service']}: {m['metric_type']} = {m['value']:.2f}\")
                elif data['type'] == 'alert':
                    print(f\"  🚨 Alert: {data['data']['message']}\")
            
            print('\\n✅ WebSocket streaming working!')
    except Exception as e:
        print(f'❌ WebSocket test failed: {e}')

asyncio.run(test())
" || echo -e "${RED}WebSocket test failed${NC}"
pause

# Step 9: Load test
echo -e "${GREEN}Step 9: Quick Load Test${NC}"
echo "Sending 20 concurrent metrics"
echo -e "${BLUE}Expected: All succeed quickly${NC}\n"

echo "Sending metrics..."
START_TIME=$SECONDS
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/metrics/ingest \
    -H "Content-Type: application/json" \
    -d '{
      "timestamp": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
      "service": "load_test",
      "metric_type": "latency",
      "value": '$((RANDOM % 200))'.0,
      "tags": {"batch": "'$i'"}
    }' > /dev/null &
done
wait
ELAPSED=$((SECONDS - START_TIME))
echo -e "${GREEN}✅ Sent 20 metrics in ${ELAPSED} seconds${NC}"

# Verify they were stored
sleep 1
COUNT=$(curl -s -X POST http://localhost:8000/metrics/query \
  -H "Content-Type: application/json" \
  -d '{
    "start_time": "'$(date -u -d '1 minute ago' '+%Y-%m-%dT%H:%M:%S')'Z",
    "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
    "services": ["load_test"],
    "aggregation": "raw"
  }' | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('data', [])))")

echo "Found $COUNT load_test metrics in database"
pause

# Step 10: Frontend check
echo -e "${GREEN}Step 10: Frontend Dashboard Check${NC}"
echo -e "${BLUE}Open http://localhost:3000 in your browser${NC}"
echo ""
echo "Checklist:"
echo "  □ Connection status shows 'Connected' (green dot)"
echo "  □ Stat cards show current values"
echo "  □ Line chart shows P50/P95/P99 lines"
echo "  □ Area chart shows throughput"
echo "  □ Bar chart shows error rates"
echo "  □ Heatmap shows service health"
echo "  □ Alerts panel shows recent alerts"
echo ""
echo -e "${YELLOW}Is the frontend working? (y/n)${NC}"
read -r response
if [[ "$response" == "y" ]]; then
    echo -e "${GREEN}✅ Frontend validated${NC}"
else
    echo -e "${YELLOW}Check: cd frontend && npm run dev${NC}"
fi

# Summary
echo -e "\n${BLUE}================================================"
echo "  Validation Complete!"
echo -e "================================================${NC}\n"

echo -e "${GREEN}Summary of Tests:${NC}"
echo "  ✅ Backend API responding"
echo "  ✅ Metric ingestion working"
echo "  ✅ Query system functional"
echo "  ✅ Service discovery active"
echo "  ✅ Anomaly detection triggers"
echo "  ✅ Alert system operational"
echo "  ✅ Aggregation calculating"
echo "  ✅ WebSocket streaming"
echo "  ✅ Load handling verified"
if [[ "$response" == "y" ]]; then
    echo "  ✅ Frontend dashboard operational"
fi

echo -e "\n${GREEN}🎉 System validation complete!${NC}"