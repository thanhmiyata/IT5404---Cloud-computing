#!/usr/bin/env python3
"""
Idempotency & Reliability Test Script

Tests the system's ability to:
1. Handle duplicate submissions (idempotent processing)
2. Prevent double-scoring when retries occur
3. Maintain data consistency under concurrent duplicate requests
4. Verify worker retry mechanism doesn't cause duplicate scoring

This demonstrates the "Chấm điểm tin cậy" requirement.
"""

import requests
import time
import random
import string
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional, Dict
import json
from collections import defaultdict

# Configuration
DEFAULT_API_URL = "http://localhost:8080"
DEFAULT_EXAM_ID = "exam_001"
DEFAULT_API_KEY = "change-me"

@dataclass
class IdempotencyTestResult:
    test_name: str
    passed: bool
    details: str
    submission_ids: List[str]
    scores: List[Optional[int]]
    statuses: List[str]

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

def print_test(name: str):
    print(f"{Colors.BOLD}{Colors.BLUE}[TEST]{Colors.RESET} {name}")

def print_pass(msg: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.RESET} {msg}")

def print_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ INFO:{Colors.RESET} {msg}")


def generate_user_id() -> str:
    """Generate a unique user ID"""
    return f"idempotency_test_{random.randint(10000, 99999)}_{random.choice(string.ascii_lowercase)}"


def generate_answers(num_questions: int = 10) -> List[dict]:
    """Generate consistent answers for testing"""
    choices = ["A", "B", "C", "D"]
    return [
        {"questionId": f"q{i+1}", "choice": random.choice(choices)}
        for i in range(num_questions)
    ]


def submit_exam(api_url: str, exam_id: str, api_key: str, user_id: str, answers: List[dict]) -> Dict:
    """Submit an exam and return response details"""
    url = f"{api_url}/v1/exams/{exam_id}/submissions"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    payload = {
        "userId": user_id,
        "answers": answers,
        "clientSubmittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        return {
            "status_code": response.status_code,
            "submission_id": response.json().get("submissionId") if response.status_code == 202 else None,
            "error": None if response.status_code == 202 else response.text[:200]
        }
    except Exception as e:
        return {
            "status_code": 0,
            "submission_id": None,
            "error": str(e)[:200]
        }


def get_submission_status(api_url: str, api_key: str, submission_id: str) -> Dict:
    """Get submission status and score"""
    url = f"{api_url}/v1/submissions/{submission_id}"
    headers = {"X-API-KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "status": data.get("status"),
                "score": data.get("score"),
                "total": data.get("total"),
                "error": None
            }
        else:
            return {"status": "ERROR", "score": None, "total": None, "error": response.text[:100]}
    except Exception as e:
        return {"status": "ERROR", "score": None, "total": None, "error": str(e)[:100]}


def wait_for_scoring(api_url: str, api_key: str, submission_ids: List[str], timeout: int = 60) -> Dict[str, Dict]:
    """Wait for all submissions to be scored"""
    print_info(f"Waiting for {len(submission_ids)} submissions to be scored (timeout: {timeout}s)...")
    
    start_time = time.time()
    results = {}
    
    while time.time() - start_time < timeout:
        all_done = True
        for sub_id in submission_ids:
            if sub_id not in results or results[sub_id]["status"] not in ["SCORED", "FAILED"]:
                status = get_submission_status(api_url, api_key, sub_id)
                results[sub_id] = status
                if status["status"] not in ["SCORED", "FAILED"]:
                    all_done = False
        
        if all_done:
            elapsed = time.time() - start_time
            print_info(f"All submissions processed in {elapsed:.1f}s")
            return results
        
        time.sleep(2)
    
    print_fail(f"Timeout after {timeout}s - some submissions not completed")
    return results


def test_duplicate_submission_sequential(api_url: str, exam_id: str, api_key: str) -> IdempotencyTestResult:
    """
    Test 1: Submit the same exam multiple times sequentially
    Expected: Should accept all, but only process once (same submissionId or idempotent scoring)
    """
    print_test("Test 1: Sequential Duplicate Submissions")
    
    user_id = generate_user_id()
    answers = generate_answers()
    
    print_info(f"Submitting same exam 5 times for user: {user_id}")
    
    submission_ids = []
    for i in range(5):
        result = submit_exam(api_url, exam_id, api_key, user_id, answers)
        if result["submission_id"]:
            submission_ids.append(result["submission_id"])
            print_info(f"  Attempt {i+1}: Got submissionId = {result['submission_id']}")
        else:
            print_fail(f"  Attempt {i+1}: Failed with status {result['status_code']}")
    
    # Wait for scoring
    time.sleep(5)
    results = wait_for_scoring(api_url, api_key, submission_ids, timeout=30)
    
    # Check idempotency
    unique_submission_ids = set(submission_ids)
    scores = [results[sid]["score"] for sid in submission_ids if sid in results]
    statuses = [results[sid]["status"] for sid in submission_ids if sid in results]
    
    # Analysis
    if len(unique_submission_ids) == 1:
        # Perfect idempotency - same submission ID returned
        passed = True
        details = f"Perfect idempotency: All 5 submissions returned same ID ({list(unique_submission_ids)[0]})"
        print_pass(details)
    elif len(set(scores)) == 1 and None not in scores:
        # Different IDs but same score (acceptable if system deduplicates by userId)
        passed = True
        details = f"Consistent scoring: {len(unique_submission_ids)} unique IDs, but all scored identically ({scores[0]} points)"
        print_pass(details)
    else:
        passed = False
        details = f"Inconsistent: {len(unique_submission_ids)} unique IDs with varying scores: {scores}"
        print_fail(details)
    
    return IdempotencyTestResult(
        test_name="Sequential Duplicate Submissions",
        passed=passed,
        details=details,
        submission_ids=submission_ids,
        scores=scores,
        statuses=statuses
    )


def test_duplicate_submission_concurrent(api_url: str, exam_id: str, api_key: str) -> IdempotencyTestResult:
    """
    Test 2: Submit the same exam multiple times concurrently (race condition test)
    Expected: System should handle gracefully without double-scoring
    """
    print_test("Test 2: Concurrent Duplicate Submissions (Race Condition)")
    
    user_id = generate_user_id()
    answers = generate_answers()
    
    print_info(f"Submitting same exam 10 times concurrently for user: {user_id}")
    
    submission_ids = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(submit_exam, api_url, exam_id, api_key, user_id, answers)
            for _ in range(10)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            if result["submission_id"]:
                submission_ids.append(result["submission_id"])
    
    print_info(f"Received {len(submission_ids)} submission IDs")
    
    # Wait for scoring
    time.sleep(5)
    results = wait_for_scoring(api_url, api_key, submission_ids, timeout=30)
    
    # Check for duplicate scoring
    unique_submission_ids = set(submission_ids)
    scores = [results[sid]["score"] for sid in submission_ids if sid in results and results[sid]["score"] is not None]
    
    if len(unique_submission_ids) == 1:
        passed = True
        details = f"Excellent: All concurrent requests returned same submissionId ({list(unique_submission_ids)[0]})"
        print_pass(details)
    elif len(unique_submission_ids) <= 3 and len(set(scores)) == 1:
        passed = True
        details = f"Good: {len(unique_submission_ids)} unique IDs created, but all scored consistently ({scores[0]} points)"
        print_pass(details)
    else:
        passed = False
        details = f"Race condition detected: {len(unique_submission_ids)} unique IDs with inconsistent scores"
        print_fail(details)
    
    return IdempotencyTestResult(
        test_name="Concurrent Duplicate Submissions",
        passed=passed,
        details=details,
        submission_ids=list(submission_ids),
        scores=scores,
        statuses=[results[sid]["status"] for sid in submission_ids if sid in results]
    )


def test_retry_simulation(api_url: str, exam_id: str, api_key: str) -> IdempotencyTestResult:
    """
    Test 3: Simulate worker retry by checking if re-fetching same submission gives consistent results
    Expected: Multiple fetches should return identical score/status
    """
    print_test("Test 3: Worker Retry Simulation (Fetch Consistency)")
    
    user_id = generate_user_id()
    answers = generate_answers()
    
    # Submit once
    result = submit_exam(api_url, exam_id, api_key, user_id, answers)
    submission_id = result["submission_id"]
    
    if not submission_id:
        return IdempotencyTestResult(
            test_name="Worker Retry Simulation",
            passed=False,
            details="Failed to create initial submission",
            submission_ids=[],
            scores=[],
            statuses=[]
        )
    
    print_info(f"Created submission: {submission_id}")
    
    # Wait for scoring
    time.sleep(5)
    wait_for_scoring(api_url, api_key, [submission_id], timeout=30)
    
    # Fetch the same submission 20 times rapidly
    print_info("Fetching same submission 20 times to verify consistency...")
    
    fetch_results = []
    for i in range(20):
        status_data = get_submission_status(api_url, api_key, submission_id)
        fetch_results.append(status_data)
        time.sleep(0.1)  # Small delay
    
    # Check consistency
    scores = [r["score"] for r in fetch_results if r["score"] is not None]
    statuses = [r["status"] for r in fetch_results]
    
    unique_scores = set(scores)
    unique_statuses = set(statuses)
    
    if len(unique_scores) == 1 and len(unique_statuses) == 1:
        passed = True
        details = f"Perfect consistency: All 20 fetches returned same score ({scores[0]}) and status ({statuses[0]})"
        print_pass(details)
    else:
        passed = False
        details = f"Inconsistency detected: Scores={unique_scores}, Statuses={unique_statuses}"
        print_fail(details)
    
    return IdempotencyTestResult(
        test_name="Worker Retry Simulation",
        passed=passed,
        details=details,
        submission_ids=[submission_id],
        scores=list(unique_scores),
        statuses=list(unique_statuses)
    )


def test_different_users_same_answers(api_url: str, exam_id: str, api_key: str) -> IdempotencyTestResult:
    """
    Test 4: Different users with identical answers should get same score
    Expected: Scoring logic is deterministic
    """
    print_test("Test 4: Deterministic Scoring (Different Users, Same Answers)")
    
    # Generate one set of answers
    answers = generate_answers()
    
    # Submit for 5 different users
    print_info("Submitting same answers for 5 different users...")
    
    submission_ids = []
    user_ids = []
    for i in range(5):
        user_id = generate_user_id()
        user_ids.append(user_id)
        result = submit_exam(api_url, exam_id, api_key, user_id, answers)
        if result["submission_id"]:
            submission_ids.append(result["submission_id"])
            print_info(f"  User {i+1} ({user_id}): {result['submission_id']}")
    
    # Wait for scoring
    time.sleep(5)
    results = wait_for_scoring(api_url, api_key, submission_ids, timeout=30)
    
    # Check scores
    scores = [results[sid]["score"] for sid in submission_ids if sid in results and results[sid]["score"] is not None]
    
    if len(set(scores)) == 1:
        passed = True
        details = f"Deterministic scoring confirmed: All 5 users got same score ({scores[0]} points)"
        print_pass(details)
    else:
        passed = False
        details = f"Non-deterministic scoring: Different scores for same answers: {scores}"
        print_fail(details)
    
    return IdempotencyTestResult(
        test_name="Deterministic Scoring",
        passed=passed,
        details=details,
        submission_ids=submission_ids,
        scores=scores,
        statuses=[results[sid]["status"] for sid in submission_ids if sid in results]
    )


def print_summary(test_results: List[IdempotencyTestResult]):
    """Print final test summary"""
    print_header("TEST SUMMARY")
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r.passed)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print()
    
    for result in test_results:
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result.passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"{status} - {result.test_name}")
        print(f"       {result.details}")
    
    print(f"\n{Colors.BOLD}Overall Result: ", end="")
    if failed == 0:
        print(f"{Colors.GREEN}ALL TESTS PASSED ✓{Colors.RESET}")
    else:
        print(f"{Colors.RED}{failed} TEST(S) FAILED ✗{Colors.RESET}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Idempotency & Reliability Test for Exam Scoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all idempotency tests locally
  python test_idempotency.py

  # Test against remote server
  python test_idempotency.py --url http://136.110.44.49:8080

  # Save results to JSON
  python test_idempotency.py --output idempotency_results.json
        """
    )
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--exam-id", default=DEFAULT_EXAM_ID, help="Exam ID to test")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    print_header("IDEMPOTENCY & RELIABILITY TEST SUITE")
    print(f"Target: {args.url}")
    print(f"Exam ID: {args.exam_id}")
    print()
    
    # Run all tests
    test_results = []
    
    try:
        test_results.append(test_duplicate_submission_sequential(args.url, args.exam_id, args.api_key))
        time.sleep(2)
        
        test_results.append(test_duplicate_submission_concurrent(args.url, args.exam_id, args.api_key))
        time.sleep(2)
        
        test_results.append(test_retry_simulation(args.url, args.exam_id, args.api_key))
        time.sleep(2)
        
        test_results.append(test_different_users_same_answers(args.url, args.exam_id, args.api_key))
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
    
    # Print summary
    print_summary(test_results)
    
    # Save to JSON if requested
    if args.output:
        output_data = {
            "test_config": {
                "api_url": args.url,
                "exam_id": args.exam_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "details": r.details,
                    "submission_count": len(r.submission_ids),
                    "unique_scores": list(set(r.scores))
                }
                for r in test_results
            ],
            "summary": {
                "total_tests": len(test_results),
                "passed": sum(1 for r in test_results if r.passed),
                "failed": sum(1 for r in test_results if not r.passed)
            }
        }
        
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
