#!/usr/bin/env python3
"""
Time-to-Score Test Script

Tests the system's ability to complete scoring within target time:
- P95 completion time < 30s for spike scenario

This measures end-to-end latency from submission to SCORED status.
"""

import requests
import time
import random
import string
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import json
import statistics

DEFAULT_API_URL = "http://localhost:8080"
DEFAULT_EXAM_ID = "exam_001"
DEFAULT_API_KEY = "change-me"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

def print_metric(label: str, value: any, unit: str = "", color: str = Colors.CYAN):
    print(f"  {Colors.BOLD}{label}:{Colors.RESET} {color}{value}{unit}{Colors.RESET}")

def print_pass(msg: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.RESET} {msg}")

def print_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ INFO:{Colors.RESET} {msg}")


def submit_exam(api_url: str, exam_id: str, api_key: str) -> Dict:
    """Submit an exam and return submission ID with timestamp"""
    url = f"{api_url}/v1/exams/{exam_id}/submissions"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    
    user_id = f"tts_test_{random.randint(10000, 99999)}_{random.choice(string.ascii_lowercase)}"
    answers = [
        {"questionId": f"q{i+1}", "choice": random.choice(["A", "B", "C", "D"])}
        for i in range(10)
    ]
    
    payload = {
        "userId": user_id,
        "answers": answers,
        "clientSubmittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    submit_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 202:
            return {
                "submission_id": response.json().get("submissionId"),
                "submit_time": submit_time,
                "success": True
            }
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)[:100]}


def wait_for_scored(api_url: str, api_key: str, submission_id: str, timeout: int = 60) -> Dict:
    """Wait for a submission to be SCORED and return completion time"""
    url = f"{api_url}/v1/submissions/{submission_id}"
    headers = {"X-API-KEY": api_key}
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "SCORED":
                    completion_time = time.time() - start_time
                    return {
                        "completed": True,
                        "completion_time_sec": completion_time,
                        "score": data.get("score"),
                        "total": data.get("total")
                    }
                elif status == "FAILED":
                    return {"completed": False, "error": "Scoring failed"}
        except:
            pass
        
        time.sleep(0.5)  # Poll every 500ms
    
    return {"completed": False, "error": "Timeout"}


def test_time_to_score(api_url: str, exam_id: str, api_key: str, num_submissions: int = 100) -> Dict:
    """
    Test Time-to-Score for spike scenario
    Target: P95 < 30s
    """
    print_header("TIME-TO-SCORE TEST")
    print_info(f"Submitting {num_submissions} exams concurrently...")
    
    # Phase 1: Submit all exams concurrently (spike)
    submissions = []
    submit_start = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [
            executor.submit(submit_exam, api_url, exam_id, api_key)
            for _ in range(num_submissions)
        ]
        
        for future in as_completed(futures):
            result = future.result()
            if result.get("success"):
                submissions.append(result)
    
    submit_duration = time.time() - submit_start
    
    print_metric("Submissions Created", len(submissions), f"/{num_submissions}", Colors.GREEN)
    print_metric("Submission Phase", f"{submit_duration:.1f}", "s", Colors.CYAN)
    
    # Phase 2: Wait for all to be SCORED
    print_info(f"Waiting for all {len(submissions)} submissions to be scored...")
    
    completion_times = []
    completed_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(wait_for_scored, api_url, api_key, sub["submission_id"], 60): sub
            for sub in submissions
        }
        
        for future in as_completed(futures):
            result = future.result()
            if result.get("completed"):
                completion_times.append(result["completion_time_sec"])
                completed_count += 1
            else:
                failed_count += 1
            
            # Progress update
            total_processed = completed_count + failed_count
            if total_processed % 20 == 0 or total_processed == len(submissions):
                print_info(f"Progress: {total_processed}/{len(submissions)} processed "
                          f"({completed_count} scored, {failed_count} failed/timeout)")
    
    # Calculate metrics
    if not completion_times:
        print_fail("No submissions completed successfully")
        return {"passed": False, "details": "No completions"}
    
    completion_times.sort()
    avg_time = statistics.mean(completion_times)
    p50_time = completion_times[int(len(completion_times) * 0.50)]
    p95_time = completion_times[int(len(completion_times) * 0.95)]
    p99_time = completion_times[int(len(completion_times) * 0.99)]
    max_time = max(completion_times)
    
    print()
    print_metric("Completed", completed_count, f"/{len(submissions)}", Colors.GREEN)
    print_metric("Failed/Timeout", failed_count, "", Colors.RED if failed_count > 0 else Colors.GREEN)
    print()
    print_metric("Avg Time-to-Score", f"{avg_time:.1f}", "s", Colors.CYAN)
    print_metric("P50 Time-to-Score", f"{p50_time:.1f}", "s", Colors.CYAN)
    print_metric("P95 Time-to-Score", f"{p95_time:.1f}", "s", Colors.MAGENTA)
    print_metric("P99 Time-to-Score", f"{p99_time:.1f}", "s", Colors.MAGENTA)
    print_metric("Max Time-to-Score", f"{max_time:.1f}", "s", Colors.YELLOW)
    
    # Check pass/fail
    passed = p95_time < 30
    
    print()
    if passed:
        print_pass(f"P95 time-to-score {p95_time:.1f}s < 30s target ✓")
    else:
        print_fail(f"P95 time-to-score {p95_time:.1f}s >= 30s target ✗")
    
    return {
        "passed": passed,
        "total_submissions": len(submissions),
        "completed": completed_count,
        "failed": failed_count,
        "avg_time_sec": avg_time,
        "p50_time_sec": p50_time,
        "p95_time_sec": p95_time,
        "p99_time_sec": p99_time,
        "max_time_sec": max_time,
        "details": f"P95: {p95_time:.1f}s (target: <30s)"
    }


def main():
    parser = argparse.ArgumentParser(
        description="Time-to-Score Performance Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 100 submissions
  python test_time_to_score.py

  # Test with 500 submissions
  python test_time_to_score.py --count 500

  # Test remote server
  python test_time_to_score.py --url http://136.110.44.49:8080 --count 200
        """
    )
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--exam-id", default=DEFAULT_EXAM_ID, help="Exam ID")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--count", type=int, default=100, help="Number of submissions")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    try:
        result = test_time_to_score(args.url, args.exam_id, args.api_key, args.count)
        
        # Save results
        if args.output:
            output_data = {
                "test_config": {
                    "api_url": args.url,
                    "exam_id": args.exam_id,
                    "num_submissions": args.count,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                },
                "result": result
            }
            
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\nResults saved to: {args.output}")
        
        # Exit code
        exit(0 if result["passed"] else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        exit(1)


if __name__ == "__main__":
    main()
