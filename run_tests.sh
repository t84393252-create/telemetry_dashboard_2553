#!/bin/bash

# End-to-end test runner for Telemetry Dashboard
# This script orchestrates all validation tests

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)"
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)"
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    # Clean up any orphaned processes
    pkill -f "uvicorn main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    exit 0
}

trap cleanup EXIT INT TERM

print_header() {
    echo ""
    echo -e "${CYAN}========================================"
    echo -e "  $1"
    echo -e "========================================${NC}"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}✗ Python 3 is not installed${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Python 3 found${NC}"
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}✗ Node.js is not installed${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Node.js found${NC}"
    fi
    
    # Check for required Python packages
    echo -n "Checking Python packages... "
    cd "$SCRIPT_DIR/backend"
    if python3 -c "import fastapi, websockets, aiohttp, colorama" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}Installing...${NC}"
        pip install -r requirements.txt
        pip install aiohttp websockets colorama
    fi
    
    # Check for Node modules
    echo -n "Checking Node modules... "
    cd "$SCRIPT_DIR/frontend"
    if [ -d "node_modules" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}Installing...${NC}"
        npm install
    fi
}

# Start backend
start_backend() {
    print_header "Starting Backend Service"
    
    cd "$SCRIPT_DIR/backend"
    python3 main.py > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!
    
    echo "Backend starting (PID: $BACKEND_PID)..."
    
    # Wait for backend to be ready
    for i in {1..30}; do
        if curl -s -f "http://localhost:8000/metrics/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend is ready${NC}"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo -e "\n${RED}✗ Backend failed to start${NC}"
    echo "Check logs at /tmp/backend.log"
    return 1
}

# Start frontend (optional for some tests)
start_frontend() {
    print_header "Starting Frontend Service"
    
    cd "$SCRIPT_DIR/frontend"
    npm run dev > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    echo "Frontend starting (PID: $FRONTEND_PID)..."
    
    # Wait for frontend to be ready
    for i in {1..30}; do
        if curl -s -f "http://localhost:3000" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Frontend is ready${NC}"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo -e "\n${YELLOW}⚠ Frontend may not be ready${NC}"
    return 0  # Don't fail, frontend is optional for API tests
}

# Run health check
run_health_check() {
    print_header "Running Health Check"
    
    if [ -f "$SCRIPT_DIR/health_check.sh" ]; then
        bash "$SCRIPT_DIR/health_check.sh"
    else
        echo -e "${YELLOW}⚠ health_check.sh not found${NC}"
    fi
}

# Run validation tests
run_validation_tests() {
    print_header "Running Validation Tests"
    
    cd "$SCRIPT_DIR"
    python3 validate_system.py
}

# Run performance tests
run_performance_tests() {
    print_header "Running Performance Tests"
    
    cd "$SCRIPT_DIR"
    python3 performance_test.py
}

# Main test orchestration
main() {
    echo -e "${CYAN}"
    echo "================================================"
    echo "   Telemetry Dashboard - Complete Test Suite"
    echo "================================================"
    echo -e "${NC}"
    
    # Parse arguments
    SKIP_FRONTEND=false
    QUICK_TEST=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-frontend)
                SKIP_FRONTEND=true
                shift
                ;;
            --quick)
                QUICK_TEST=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --skip-frontend  Skip frontend startup (API tests only)"
                echo "  --quick         Run quick tests only (skip performance)"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Start services
    start_backend
    
    if [ "$SKIP_FRONTEND" = false ]; then
        start_frontend
    fi
    
    # Allow services to stabilize
    echo -e "\n${YELLOW}Waiting for services to stabilize...${NC}"
    sleep 3
    
    # Run tests
    run_health_check
    run_validation_tests
    
    if [ "$QUICK_TEST" = false ]; then
        run_performance_tests
    fi
    
    # Final summary
    print_header "Test Suite Complete"
    
    echo -e "${GREEN}✓ All tests completed successfully!${NC}"
    echo ""
    echo "Services are still running for manual inspection:"
    echo "  - Backend API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    
    if [ "$SKIP_FRONTEND" = false ]; then
        echo "  - Frontend Dashboard: http://localhost:3000"
    fi
    
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    
    # Keep running until interrupted
    wait
}

# Run main function
main "$@"