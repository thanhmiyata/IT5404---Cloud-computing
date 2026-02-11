#!/usr/bin/env python3
"""
Spike Load Test Script - End-of-Exam Scenario

Simulates 1000 students submitting exams simultaneously at the end of exam time.
Demonstrates the system's ability to:
- Accept burst submissions (202 responses)
- Queue absorption via Pub/Sub
- Worker autoscaling under load
- Eventually process all submissions to SCORED status
"""

import requests
import time
import random
import string
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional
import json

# Configuration
DEFAULT_API_URL = "http://localhost:8080"
DEFAULT_EXAM_ID = "exam_001"
DEFAULT_API_KEY = "change-me"
DEFAULT_CONCURRENT_SUBMISSIONS = 1000
DEFAULT_MAX_WORKERS = 100  # Thread pool size


@dataclass
class SubmissionResult:
    user_id: str
    submission_id: Optional[str]
    status_code: int
    response_time_ms: float
    error: Optional[str] = None


@dataclass
class TestMetrics:
    total_submissions: int
    successful: int
    failed: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    total_duration_sec: float
    submissions_per_sec: float


def generate_user_id() -> str:
    """Generate a unique user ID"""
    return f"student_{random.randint(10000, 99999)}_{random.choice(string.ascii_lowercase)}"


def generate_answers(num_questions: int = 10) -> List[dict]:
    """Generate random answers for exam questions"""
    choices = ["A", "B", "C", "D"]
    return [
        {"questionId": f"q{i+1}", "choice": random.choice(choices)}
        for i in range(num_questions)
    ]


def submit_exam(api_url: str, exam_id: str, api_key: str, user_id: str) -> SubmissionResult:
    """Submit a single exam and return the result"""
    url = f"{api_url}/v1/exams/{exam_id}/submissions"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    payload = {
        "userId": user_id,
        "answers": generate_answers(),
        "clientSubmittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    start_time = time.time()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response_time_ms = (time.time() - start_time) * 1000

        if response.status_code == 202:
            data = response.json()
            return SubmissionResult(
                user_id=user_id,
                submission_id=data.get("submissionId"),
                status_code=response.status_code,
                response_time_ms=response_time_ms
            )
        else:
            return SubmissionResult(
                user_id=user_id,
                submission_id=None,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error=response.text[:200]
            )
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return SubmissionResult(
            user_id=user_id,
            submission_id=None,
            status_code=0,
            response_time_ms=response_time_ms,
            error=str(e)[:200]
        )


def calculate_percentile(sorted_values: List[float], percentile: float) -> float:
    """Calculate the percentile value from a sorted list"""
    if not sorted_values:
        return 0.0
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def run_spike_test(
    api_url: str,
    exam_id: str,
    api_key: str,
    num_submissions: int,
    max_workers: int
) -> tuple[List[SubmissionResult], TestMetrics]:
    """Execute the spike load test"""

    print(f"\n{'='*60}")
    print(f"  SPIKE LOAD TEST - End of Exam Scenario")
    print(f"{'='*60}")
    print(f"  Target:      {api_url}")
    print(f"  Exam ID:     {exam_id}")
    print(f"  Submissions: {num_submissions}")
    print(f"  Workers:     {max_workers}")
    print(f"{'='*60}\n")

    # Generate all user IDs upfront
    user_ids = [generate_user_id() for _ in range(num_submissions)]
    results: List[SubmissionResult] = []

    print(f"[{time.strftime('%H:%M:%S')}] Starting spike submission...")
    test_start = time.time()

    # Submit all exams concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(submit_exam, api_url, exam_id, api_key, user_id): user_id
            for user_id in user_ids
        }

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            # Progress update every 100 submissions
            if completed % 100 == 0 or completed == num_submissions:
                elapsed = time.time() - test_start
                rate = completed / elapsed if elapsed > 0 else 0
                success_count = sum(1 for r in results if r.status_code == 202)
                print(f"[{time.strftime('%H:%M:%S')}] Progress: {completed}/{num_submissions} "
                      f"({success_count} success, {completed - success_count} failed) "
                      f"- {rate:.1f} req/s")

    test_duration = time.time() - test_start

    # Calculate metrics
    successful = [r for r in results if r.status_code == 202]
    failed = [r for r in results if r.status_code != 202]
    response_times = sorted([r.response_time_ms for r in results])

    metrics = TestMetrics(
        total_submissions=num_submissions,
        successful=len(successful),
        failed=len(failed),
        avg_response_time_ms=sum(response_times) / len(response_times) if response_times else 0,
        min_response_time_ms=min(response_times) if response_times else 0,
        max_response_time_ms=max(response_times) if response_times else 0,
        p95_response_time_ms=calculate_percentile(response_times, 95),
        p99_response_time_ms=calculate_percentile(response_times, 99),
        total_duration_sec=test_duration,
        submissions_per_sec=num_submissions / test_duration if test_duration > 0 else 0
    )

    return results, metrics


def poll_completion(
    api_url: str,
    api_key: str,
    submission_ids: List[str],
    timeout_sec: int = 300,
    poll_interval_sec: int = 5
) -> dict:
    """Poll submissions until all are SCORED or timeout"""

    print(f"\n[{time.strftime('%H:%M:%S')}] Polling for completion (timeout: {timeout_sec}s)...")

    headers = {"X-API-KEY": api_key}
    start_time = time.time()

    status_counts = {"RECEIVED": 0, "SCORING": 0, "SCORED": 0, "FAILED": 0}

    while time.time() - start_time < timeout_sec:
        status_counts = {"RECEIVED": 0, "SCORING": 0, "SCORED": 0, "FAILED": 0}

        for sub_id in submission_ids:
            try:
                response = requests.get(
                    f"{api_url}/v1/submissions/{sub_id}",
                    headers=headers,
                    timeout=10
                )
                if response.status_code == 200:
                    status = response.json().get("status", "UNKNOWN")
                    if status in status_counts:
                        status_counts[status] += 1
            except:
                pass

        elapsed = time.time() - start_time
        completed = status_counts["SCORED"] + status_counts["FAILED"]
        pending = status_counts["RECEIVED"] + status_counts["SCORING"]

        print(f"[{time.strftime('%H:%M:%S')}] Status after {elapsed:.0f}s: "
              f"SCORED={status_counts['SCORED']}, SCORING={status_counts['SCORING']}, "
              f"RECEIVED={status_counts['RECEIVED']}, FAILED={status_counts['FAILED']}")

        if completed == len(submission_ids):
            print(f"\n[{time.strftime('%H:%M:%S')}] All submissions processed in {elapsed:.1f}s")
            break

        time.sleep(poll_interval_sec)

    return {
        "final_status": status_counts,
        "time_to_complete_sec": time.time() - start_time
    }


def print_results(results: List[SubmissionResult], metrics: TestMetrics):
    """Print test results summary"""

    print(f"\n{'='*60}")
    print(f"  TEST RESULTS SUMMARY")
    print(f"{'='*60}")

    print(f"\n  Submission Results:")
    print(f"    Total:      {metrics.total_submissions}")
    print(f"    Successful: {metrics.successful} ({metrics.successful/metrics.total_submissions*100:.1f}%)")
    print(f"    Failed:     {metrics.failed} ({metrics.failed/metrics.total_submissions*100:.1f}%)")

    print(f"\n  Response Time (ms):")
    print(f"    Average:    {metrics.avg_response_time_ms:.1f}")
    print(f"    Min:        {metrics.min_response_time_ms:.1f}")
    print(f"    Max:        {metrics.max_response_time_ms:.1f}")
    print(f"    P95:        {metrics.p95_response_time_ms:.1f}")
    print(f"    P99:        {metrics.p99_response_time_ms:.1f}")

    print(f"\n  Throughput:")
    print(f"    Duration:   {metrics.total_duration_sec:.2f}s")
    print(f"    Rate:       {metrics.submissions_per_sec:.1f} submissions/sec")

    # Show error breakdown if any failures
    if metrics.failed > 0:
        print(f"\n  Error Breakdown:")
        error_counts = {}
        for r in results:
            if r.status_code != 202:
                key = f"HTTP {r.status_code}" if r.status_code > 0 else "Connection Error"
                error_counts[key] = error_counts.get(key, 0) + 1
        for error_type, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"    {error_type}: {count}")

    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Spike Load Test for Exam Scoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local test with 1000 submissions
  python spike_load_test.py

  # Custom endpoint and count
  python spike_load_test.py --url http://136.110.44.49:8080 --count 500

  # Full test with completion polling
  python spike_load_test.py --poll --poll-timeout 300
        """
    )
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--exam-id", default=DEFAULT_EXAM_ID, help="Exam ID to submit to")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key for authentication")
    parser.add_argument("--count", type=int, default=DEFAULT_CONCURRENT_SUBMISSIONS,
                        help="Number of submissions")
    parser.add_argument("--workers", type=int, default=DEFAULT_MAX_WORKERS,
                        help="Max concurrent workers")
    parser.add_argument("--poll", action="store_true",
                        help="Poll submissions until all are SCORED")
    parser.add_argument("--poll-timeout", type=int, default=300,
                        help="Polling timeout in seconds")
    parser.add_argument("--output", help="Save results to JSON file")

    args = parser.parse_args()

    # Run spike test
    results, metrics = run_spike_test(
        api_url=args.url,
        exam_id=args.exam_id,
        api_key=args.api_key,
        num_submissions=args.count,
        max_workers=args.workers
    )

    # Print results
    print_results(results, metrics)

    # Optional: Poll for completion
    completion_stats = None
    if args.poll:
        submission_ids = [r.submission_id for r in results if r.submission_id]
        if submission_ids:
            completion_stats = poll_completion(
                api_url=args.url,
                api_key=args.api_key,
                submission_ids=submission_ids,
                timeout_sec=args.poll_timeout
            )

    # Optional: Save results to JSON
    output_data = {
        "test_config": {
            "api_url": args.url,
            "exam_id": args.exam_id,
            "num_submissions": args.count,
            "max_workers": args.workers
        },
        "metrics": {
            "total_submissions": metrics.total_submissions,
            "successful": metrics.successful,
            "failed": metrics.failed,
            "avg_response_time_ms": metrics.avg_response_time_ms,
            "min_response_time_ms": metrics.min_response_time_ms,
            "max_response_time_ms": metrics.max_response_time_ms,
            "p95_response_time_ms": metrics.p95_response_time_ms,
            "p99_response_time_ms": metrics.p99_response_time_ms,
            "total_duration_sec": metrics.total_duration_sec,
            "submissions_per_sec": metrics.submissions_per_sec
        },
        "completion_stats": completion_stats
    }
    print(json.dumps(output_data, indent=4))
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
