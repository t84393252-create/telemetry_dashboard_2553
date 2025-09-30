#!/bin/bash

# Telemetry Dashboard Health Check Script
# Validates that all services are running correctly

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Telemetry Dashboard Health Check"
echo "========================================"
echo ""

# Check if backend is running
check_backend() {
    echo -n "Checking Backend API... "
    if curl -s -f -o /dev/null "http://localhost:8000/metrics/health"; then
        echo -e "${GREEN}✓ Running${NC}"
        
        # Get detailed health info
        HEALTH=$(curl -s "http://localhost:8000/metrics/health")
        echo "  Status: $(echo $HEALTH | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")"
        echo "  Services: $(echo $HEALTH | python3 -c "import sys, json; print(json.load(sys.stdin)['services_count'])")"
        return 0
    else
        echo -e "${RED}✗ Not responding${NC}"
        echo "  Start with: cd backend && python main.py"
        return 1
    fi
}

# Check if frontend is running
check_frontend() {
    echo -n "Checking Frontend... "
    if curl -s -f -o /dev/null "http://localhost:3000"; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Not responding${NC}"
        echo "  Start with: cd frontend && npm run dev"
        return 1
    fi
}

# Check WebSocket connectivity
check_websocket() {
    echo -n "Checking WebSocket... "
    
    # Use Python to test WebSocket
    python3 - <<EOF 2>/dev/null
import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws/metrics") as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=2)
            data = json.loads(msg)
            if data.get("type") == "initial":
                print("✓ Connected")
                return True
    except:
        pass
    print("✗ Not available")
    return False

asyncio.run(test())
EOF
    
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}Real-time streaming active${NC}"
        return 0
    else
        echo -e "  ${RED}WebSocket connection failed${NC}"
        return 1
    fi
}

# Check data generation
check_data_generation() {
    echo -n "Checking Data Generation... "
    
    QUERY='{
        "start_time": "'$(date -u -d '1 minute ago' '+%Y-%m-%dT%H:%M:%S')'Z",
        "end_time": "'$(date -u '+%Y-%m-%dT%H:%M:%S')'Z",
        "aggregation": "raw"
    }'
    
    RESPONSE=$(curl -s -X POST "http://localhost:8000/metrics/query" \
        -H "Content-Type: application/json" \
        -d "$QUERY" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        COUNT=$(echo $RESPONSE | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('data', [])))" 2>/dev/null)
        if [ "$COUNT" -gt "0" ]; then
            echo -e "${GREEN}✓ Active${NC}"
            echo "  Metrics in last minute: $COUNT"
            return 0
        else
            echo -e "${YELLOW}⚠ No recent data${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Query failed${NC}"
        return 1
    fi
}

# Check service discovery
check_services() {
    echo -n "Checking Service Discovery... "
    
    SERVICES=$(curl -s "http://localhost:8000/metrics/services" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        SERVICE_COUNT=$(echo $SERVICES | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('services', [])))" 2>/dev/null)
        if [ "$SERVICE_COUNT" -gt "0" ]; then
            echo -e "${GREEN}✓ Found $SERVICE_COUNT services${NC}"
            
            # List services and their status
            echo $SERVICES | python3 -c "
import sys, json
data = json.load(sys.stdin)
for svc in data.get('services', []):
    status_icon = '✓' if svc['status'] == 'healthy' else '⚠' if svc['status'] == 'degraded' else '✗'
    print(f\"  {status_icon} {svc['service']}: {svc['status']}\")
" 2>/dev/null
            return 0
        else
            echo -e "${YELLOW}⚠ No services found${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ API error${NC}"
        return 1
    fi
}

# Check for recent alerts
check_alerts() {
    echo -n "Checking Alert System... "
    
    ALERTS=$(curl -s "http://localhost:8000/metrics/alerts?limit=5" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        ALERT_COUNT=$(echo $ALERTS | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('alerts', [])))" 2>/dev/null)
        echo -e "${GREEN}✓ Active${NC}"
        echo "  Recent alerts: $ALERT_COUNT"
        
        if [ "$ALERT_COUNT" -gt "0" ]; then
            echo $ALERTS | python3 -c "
import sys, json
from datetime import datetime
data = json.load(sys.stdin)
for alert in data.get('alerts', [])[:3]:
    severity_icon = '🔴' if alert['severity'] == 'critical' else '🟡' if alert['severity'] == 'warning' else '🔵'
    print(f\"  {severity_icon} {alert['service']}: {alert['message']}\")
" 2>/dev/null
        fi
        return 0
    else
        echo -e "${RED}✗ Alert system error${NC}"
        return 1
    fi
}

# Main execution
echo "System Components:"
echo "----------------------------------------"
BACKEND_OK=$(check_backend && echo 1 || echo 0)
echo ""

FRONTEND_OK=$(check_frontend && echo 1 || echo 0)
echo ""

if [ "$BACKEND_OK" = "1" ]; then
    echo "Backend Services:"
    echo "----------------------------------------"
    check_websocket
    echo ""
    check_data_generation
    echo ""
    check_services
    echo ""
    check_alerts
    echo ""
fi

echo "========================================"
if [ "$BACKEND_OK" = "1" ] && [ "$FRONTEND_OK" = "1" ]; then
    echo -e "${GREEN}✓ System is fully operational${NC}"
    echo ""
    echo "Dashboard URL: http://localhost:3000"
elif [ "$BACKEND_OK" = "1" ]; then
    echo -e "${YELLOW}⚠ System partially operational${NC}"
    echo "  Backend is running but frontend is not accessible"
else
    echo -e "${RED}✗ System is not operational${NC}"
    echo ""
    echo "To start the system:"
    echo "  1. Backend:  cd backend && python main.py"
    echo "  2. Frontend: cd frontend && npm run dev"
    echo ""
    echo "Or use Docker:"
    echo "  docker-compose up -d"
fi
echo "========================================"