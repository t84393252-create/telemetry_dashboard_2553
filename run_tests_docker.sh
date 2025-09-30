#!/bin/bash

# Docker-based test runner script
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================"
echo "  Docker-Based Test Suite"
echo -e "========================================${NC}\n"

# Parse arguments
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}Running unit tests in Docker...${NC}"
        docker-compose -f docker-compose.test.yml run --rm test-runner python validate_system.py
        ;;
    e2e)
        echo -e "${YELLOW}Running E2E tests in Docker...${NC}"
        docker-compose -f docker-compose.test.yml run --rm test-runner python e2e_test.py
        ;;
    performance)
        echo -e "${YELLOW}Running performance tests in Docker...${NC}"
        docker-compose -f docker-compose.test.yml run --rm test-runner python performance_test.py
        ;;
    all)
        echo -e "${YELLOW}Running all tests in Docker...${NC}"
        docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
        ;;
    clean)
        echo -e "${YELLOW}Cleaning up test containers...${NC}"
        docker-compose -f docker-compose.test.yml down -v
        ;;
    *)
        echo "Usage: $0 [unit|e2e|performance|all|clean]"
        exit 1
        ;;
esac

echo -e "\n${GREEN}Docker tests complete!${NC}"