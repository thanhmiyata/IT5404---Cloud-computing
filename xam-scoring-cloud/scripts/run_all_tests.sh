#!/bin/bash
# =============================================================================
# RUN ALL TESTS - Complete Demo Script
# =============================================================================
# This script runs all test suites in sequence for a complete system demo
# Usage: ./run_all_tests.sh [API_URL] [API_KEY]
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Configuration
API_URL="${1:-http://localhost:8080}"
API_KEY="${2:-change-me}"
RESULTS_DIR="./test_results_$(date +%Y%m%d_%H%M%S)"

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${BOLD}${CYAN}"
echo "============================================================================="
echo "  EXAM SCORING SYSTEM - COMPLETE TEST SUITE"
echo "============================================================================="
echo -e "${RESET}"
echo -e "Target API:    ${BLUE}${API_URL}${RESET}"
echo -e "Results Dir:   ${BLUE}${RESULTS_DIR}${RESET}"
echo -e "Timestamp:     ${BLUE}$(date)${RESET}"
echo ""

# Function to print section header
print_section() {
    echo -e "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}${CYAN}  $1${RESET}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
}

# Function to check if API is accessible
check_api() {
    print_section "Pre-flight Check: API Connectivity"
    
    echo -e "${YELLOW}Checking API at ${API_URL}...${RESET}"
    
    if curl -s -f -H "X-API-KEY: ${API_KEY}" "${API_URL}/v1/internal/stats" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ API is accessible${RESET}\n"
        return 0
    else
        echo -e "${RED}✗ API is not accessible${RESET}"
        echo -e "${YELLOW}Please ensure services are running:${RESET}"
        echo -e "  docker-compose up -d"
        echo ""
        return 1
    fi
}

# Test 1: Dashboard Monitoring
run_dashboard_test() {
    print_section "TEST 1: Dashboard Real-time Monitoring"
    
    python3 test_dashboard.py \
        --url "$API_URL" \
        --api-key "$API_KEY" \
        --duration 20 \
        --output "$RESULTS_DIR/dashboard_test.json" \
        | tee "$RESULTS_DIR/dashboard_test.log"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}✓ Dashboard test completed${RESET}"
    else
        echo -e "\n${RED}✗ Dashboard test failed${RESET}"
    fi
    
    return $exit_code
}

# Test 2: Idempotency & Reliability
run_idempotency_test() {
    print_section "TEST 2: Idempotency & Reliability"
    
    python3 test_idempotency.py \
        --url "$API_URL" \
        --api-key "$API_KEY" \
        --output "$RESULTS_DIR/idempotency_test.json" \
        | tee "$RESULTS_DIR/idempotency_test.log"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}✓ Idempotency test completed${RESET}"
    else
        echo -e "\n${RED}✗ Idempotency test failed${RESET}"
    fi
    
    return $exit_code
}

# Test 3: Spike Load Test (Async Submit + Polling)
run_spike_test() {
    print_section "TEST 3: Spike Load Test (Async Submit + Result Polling)"
    
    python3 spike_load_test.py \
        --url "$API_URL" \
        --api-key "$API_KEY" \
        --count 500 \
        --workers 50 \
        --poll \
        --poll-timeout 120 \
        --output "$RESULTS_DIR/spike_test.json" \
        | tee "$RESULTS_DIR/spike_test.log"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ $exit_code -eq 0 ]; then
        echo -e "\n${GREEN}✓ Spike load test completed${RESET}"
    else
        echo -e "\n${RED}✗ Spike load test failed${RESET}"
    fi
    
    return $exit_code
}

# Generate summary report
generate_summary() {
    print_section "TEST SUMMARY REPORT"
    
    local summary_file="$RESULTS_DIR/SUMMARY.txt"
    
    {
        echo "============================================================================="
        echo "  EXAM SCORING SYSTEM - TEST SUMMARY"
        echo "============================================================================="
        echo ""
        echo "Timestamp:     $(date)"
        echo "API URL:       $API_URL"
        echo "Results Dir:   $RESULTS_DIR"
        echo ""
        echo "-----------------------------------------------------------------------------"
        echo "  TEST RESULTS"
        echo "-----------------------------------------------------------------------------"
        echo ""
        
        # Dashboard Test
        if [ -f "$RESULTS_DIR/dashboard_test.json" ]; then
            echo "✓ Dashboard Test:        COMPLETED"
            if command -v jq &> /dev/null; then
                jq -r '.summary | "  - Total: \(.total_tests), Passed: \(.passed), Failed: \(.failed)"' "$RESULTS_DIR/dashboard_test.json" 2>/dev/null || echo "  - See dashboard_test.json for details"
            fi
        else
            echo "✗ Dashboard Test:        FAILED or SKIPPED"
        fi
        echo ""
        
        # Idempotency Test
        if [ -f "$RESULTS_DIR/idempotency_test.json" ]; then
            echo "✓ Idempotency Test:      COMPLETED"
            if command -v jq &> /dev/null; then
                jq -r '.summary | "  - Total: \(.total_tests), Passed: \(.passed), Failed: \(.failed)"' "$RESULTS_DIR/idempotency_test.json" 2>/dev/null || echo "  - See idempotency_test.json for details"
            fi
        else
            echo "✗ Idempotency Test:      FAILED or SKIPPED"
        fi
        echo ""
        
        # Spike Test
        if [ -f "$RESULTS_DIR/spike_test.json" ]; then
            echo "✓ Spike Load Test:       COMPLETED"
            if command -v jq &> /dev/null; then
                jq -r '.metrics | "  - Submissions: \(.total_submissions), Success: \(.successful), Failed: \(.failed)\n  - Avg Response: \(.avg_response_time_ms | floor)ms, P95: \(.p95_response_time_ms | floor)ms\n  - Throughput: \(.submissions_per_sec | floor) req/s"' "$RESULTS_DIR/spike_test.json" 2>/dev/null || echo "  - See spike_test.json for details"
            fi
        else
            echo "✗ Spike Load Test:       FAILED or SKIPPED"
        fi
        echo ""
        
        echo "============================================================================="
        echo ""
        echo "All test results saved to: $RESULTS_DIR"
        echo ""
        echo "Files generated:"
        ls -lh "$RESULTS_DIR" | tail -n +2 | awk '{print "  - " $9 " (" $5 ")"}'
        echo ""
        echo "============================================================================="
        
    } | tee "$summary_file"
    
    echo -e "\n${GREEN}Summary saved to: ${summary_file}${RESET}\n"
}

# Main execution
main() {
    local failed_tests=0
    
    # Check API connectivity first
    if ! check_api; then
        echo -e "${RED}Aborting: API not accessible${RESET}"
        exit 1
    fi
    
    # Run all tests
    run_dashboard_test || ((failed_tests++))
    sleep 2
    
    run_idempotency_test || ((failed_tests++))
    sleep 2
    
    run_spike_test || ((failed_tests++))
    
    # Generate summary
    generate_summary
    
    # Final result
    print_section "FINAL RESULT"
    
    if [ $failed_tests -eq 0 ]; then
        echo -e "${BOLD}${GREEN}✓ ALL TESTS PASSED${RESET}\n"
        echo -e "The system successfully demonstrates all 4 core functionalities:"
        echo -e "  ${GREEN}✓${RESET} Async Submit (202 Accepted)"
        echo -e "  ${GREEN}✓${RESET} Reliable Scoring (Idempotent)"
        echo -e "  ${GREEN}✓${RESET} Result Polling API"
        echo -e "  ${GREEN}✓${RESET} Real-time Dashboard Monitoring"
        echo ""
        exit 0
    else
        echo -e "${BOLD}${RED}✗ $failed_tests TEST(S) FAILED${RESET}\n"
        echo -e "Please check the logs in: ${BLUE}$RESULTS_DIR${RESET}"
        echo ""
        exit 1
    fi
}

# Run main function
main "$@"
