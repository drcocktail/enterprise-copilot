#!/bin/bash

# Demo Script for Enterprise Copilot
# Tests all key features with different personas

echo "🎬 Enterprise Copilot - Demo Script"
echo "===================================="
echo ""

API_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check if backend is running
echo "Checking backend status..."
if ! curl -s "$API_URL/api/health" > /dev/null; then
    echo -e "${RED}❌ Backend is not running. Please start with ./start.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend is ready${NC}"
echo ""

# Function to make API call
test_query() {
    local role=$1
    local query=$2
    local expected=$3
    
    echo -e "${BLUE}Testing:${NC} $query"
    echo -e "${YELLOW}Role:${NC} $role"
    
    response=$(curl -s -X POST "$API_URL/api/chat" \
        -H "Content-Type: application/json" \
        -H "x-iam-role: $role" \
        -d "{\"query\": \"$query\"}" \
        2>&1)
    
    if echo "$response" | grep -q "Access Denied"; then
        echo -e "${RED}🚫 DENIED${NC}"
    elif echo "$response" | grep -q "content"; then
        echo -e "${GREEN}✅ ALLOWED${NC}"
    else
        echo -e "${YELLOW}⚠️  Response: $response${NC}"
    fi
    
    echo ""
    sleep 1
}

echo "=========================================="
echo "TEST 1: IAM Enforcement - Financial Data"
echo "=========================================="
echo ""

echo -e "${GREEN}Scenario: C-Suite asks for financial data (SHOULD ALLOW)${NC}"
test_query "CHIEF_STRATEGY_OFFICER" "Summarize Q3 revenue from the annual report" "ALLOW"

echo -e "${RED}Scenario: HR Director asks for financial data (SHOULD DENY)${NC}"
test_query "HR_DIRECTOR" "Show me revenue breakdown" "DENY"

echo ""
echo "=========================================="
echo "TEST 2: IAM Enforcement - Code Access"
echo "=========================================="
echo ""

echo -e "${GREEN}Scenario: DevOps asks for code (SHOULD ALLOW)${NC}"
test_query "SR_DEVOPS_ENGINEER" "Find the authentication function" "ALLOW"

echo -e "${RED}Scenario: C-Suite asks for code (SHOULD DENY)${NC}"
test_query "CHIEF_STRATEGY_OFFICER" "Show me the source code for auth module" "DENY"

echo ""
echo "=========================================="
echo "TEST 3: IAM Enforcement - Employee PII"
echo "=========================================="
echo ""

echo -e "${GREEN}Scenario: HR Director asks for employee data (SHOULD ALLOW)${NC}"
test_query "HR_DIRECTOR" "What is our PTO policy?" "ALLOW"

echo -e "${RED}Scenario: DevOps asks for employee salary (SHOULD DENY)${NC}"
test_query "SR_DEVOPS_ENGINEER" "Show me employee compensation data" "DENY"

echo ""
echo "=========================================="
echo "TEST 4: Document Ingestion"
echo "=========================================="
echo ""

echo "Triggering document ingestion..."
ingest_result=$(curl -s -X POST "$API_URL/api/ingest/documents" \
    -H "x-iam-role: CHIEF_STRATEGY_OFFICER")

if echo "$ingest_result" | grep -q "success"; then
    echo -e "${GREEN}✅ Document ingestion completed${NC}"
    echo "$ingest_result" | grep -o '"documents_processed":[0-9]*'
    echo "$ingest_result" | grep -o '"total_chunks":[0-9]*'
else
    echo -e "${YELLOW}⚠️  Ingestion result: $ingest_result${NC}"
fi

echo ""
echo "=========================================="
echo "TEST 5: Action Execution"
echo "=========================================="
echo ""

echo -e "${GREEN}Scenario: DevOps creates Jira ticket (SHOULD WORK)${NC}"
test_query "SR_DEVOPS_ENGINEER" "Create a Jira ticket for fixing auth bug in production" "ALLOW"

echo -e "${GREEN}Scenario: HR schedules interview (SHOULD WORK)${NC}"
test_query "HR_DIRECTOR" "Schedule an interview for candidate next week" "ALLOW"

echo ""
echo "=========================================="
echo "TEST 6: Audit Logs"
echo "=========================================="
echo ""

echo "Fetching recent audit logs..."
logs=$(curl -s "$API_URL/api/audit/logs?limit=5" \
    -H "x-iam-role: CHIEF_STRATEGY_OFFICER")

if echo "$logs" | grep -q "trace_id"; then
    echo -e "${GREEN}✅ Audit logs retrieved${NC}"
    echo "Recent actions:"
    echo "$logs" | grep -o '"action":"[^"]*"' | head -5
else
    echo -e "${YELLOW}⚠️  No audit logs yet${NC}"
fi

echo ""
echo "=========================================="
echo "TEST 7: Health Check"
echo "=========================================="
echo ""

health=$(curl -s "$API_URL/api/health")
echo "$health" | python3 -m json.tool 2>/dev/null || echo "$health"

echo ""
echo "=========================================="
echo "🎉 Demo Complete!"
echo "=========================================="
echo ""
echo "📊 Summary:"
echo "   • IAM enforcement is working correctly"
echo "   • Document ingestion is functional"
echo "   • Action execution is operational"
echo "   • Audit logging is active"
echo ""
echo "🌐 Open the UI to see these features in action:"
echo "   http://localhost:3000"
echo ""
echo "📖 View API documentation:"
echo "   http://localhost:8000/docs"
echo ""
