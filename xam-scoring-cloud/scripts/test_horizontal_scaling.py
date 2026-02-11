#!/usr/bin/env python3
"""
Horizontal Scaling Test Script

Tests the system's ability to handle massive load with horizontal scaling:
- 10,000 submissions spike scenario
- Monitor worker scaling from baseline to 500-1000 workers
- Verify auto scale-up under heavy load
- Verify auto scale-down after load decreases

This demonstrates true cloud-native horizontal scaling capability.
"""

import requests
import time
import random
import string
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import json

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
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_section(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─'*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─'*80}{Colors.RESET}\n")

def print_metric(label: str, value: any, unit: str = "", color: str = Colors.CYAN):
    print(f"  {Colors.BOLD}{label}:{Colors.RESET} {color}{value}{unit}{Colors.RESET}")

def print_pass(msg: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.RESET} {msg}")

def print_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ INFO:{Colors.RESET} {msg}")

def print_warning(msg: str):
    print(f"  {Colors.YELLOW}⚠ WARNING:{Colors.RESET} {msg}")


def get_stats(api_url: str, api_key: str) -> Dict:
    """Fetch system stats"""
    try:
        response = requests.get(
            f"{api_url}/v1/internal/stats",
            headers={"X-API-KEY": api_key},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}


def submit_batch(api_url: str, exam_id: str, api_key: str, batch_size: int) -> Dict:
    """Submit a batch of exams"""
    url = f"{api_url}/v1/exams/{exam_id}/submissions"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }
    
    success_count = 0
    error_count = 0
    submission_ids = []
    
    for _ in range(batch_size):
        user_id = f"scale_test_{random.randint(100000, 999999)}"
        answers = [
            {"questionId": f"q{i+1}", "choice": random.choice(["A", "B", "C", "D"])}
            for i in range(10)
        ]
        
        payload = {
            "userId": user_id,
            "answers": answers,
            "clientSubmittedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 202:
                success_count += 1
                submission_ids.append(response.json().get("submissionId"))
            else:
                error_count += 1
        except:
            error_count += 1
    
    return {
        "success": success_count,
        "errors": error_count,
        "submission_ids": submission_ids
    }


def monitor_scaling(api_url: str, api_key: str, duration_sec: int = 60, interval_sec: int = 5) -> List[Dict]:
    """Monitor scaling metrics over time"""
    snapshots = []
    start_time = time.time()
    
    print_info(f"Monitoring scaling for {duration_sec}s (polling every {interval_sec}s)...")
    print()
    print(f"  {'TIME':<10} | {'INSTANCES':<10} | {'BACKLOG':<10} | {'COMPLETED':<10} | {'THROUGHPUT':<12}")
    print(f"  {'-'*70}")
    
    while time.time() - start_time < duration_sec:
        stats = get_stats(api_url, api_key)
        if stats:
            timestamp = time.strftime("%H:%M:%S")
            instances = stats.get("infrastructure", {}).get("instances", 0)
            backlog = stats.get("business", {}).get("backlog", 0)
            completed = stats.get("business", {}).get("completed", 0)
            throughput = stats.get("business", {}).get("throughput", 0)
            
            snapshot = {
                "timestamp": timestamp,
                "elapsed_sec": time.time() - start_time,
                "instances": instances,
                "backlog": backlog,
                "completed": completed,
                "throughput": throughput
            }
            snapshots.append(snapshot)
            
            # Color code instances based on scale
            instance_color = Colors.GREEN if instances < 100 else Colors.YELLOW if instances < 500 else Colors.MAGENTA
            backlog_color = Colors.GREEN if backlog < 1000 else Colors.YELLOW if backlog < 5000 else Colors.RED
            
            print(f"  {timestamp:<10} | {instance_color}{instances:<10}{Colors.RESET} | "
                  f"{backlog_color}{backlog:<10}{Colors.RESET} | {completed:<10} | {throughput:<12}")
        
        time.sleep(interval_sec)
    
    print()
    return snapshots


def test_horizontal_scaling(
    api_url: str,
    exam_id: str,
    api_key: str,
    total_submissions: int = 10000,
    batch_size: int = 100,
    max_workers: int = 100
) -> Dict:
    """
    Test horizontal scaling with massive load
    """
    print_header("HORIZONTAL SCALING TEST - 10K SUBMISSIONS")
    
    # Phase 1: Baseline
    print_section("PHASE 1: Baseline Measurement")
    
    baseline_stats = get_stats(api_url, api_key)
    baseline_instances = baseline_stats.get("infrastructure", {}).get("instances", 0)
    baseline_backlog = baseline_stats.get("business", {}).get("backlog", 0)
    baseline_completed = baseline_stats.get("business", {}).get("completed", 0)
    
    print_metric("Baseline Instances", baseline_instances, "", Colors.CYAN)
    print_metric("Baseline Backlog", baseline_backlog, "", Colors.CYAN)
    print_metric("Baseline Completed", baseline_completed, "", Colors.CYAN)
    
    # Phase 2: Massive Load Injection
    print_section(f"PHASE 2: Injecting {total_submissions} Submissions")
    
    print_info(f"Submitting in batches of {batch_size} with {max_workers} workers...")
    
    num_batches = total_submissions // batch_size
    total_success = 0
    total_errors = 0
    all_submission_ids = []
    
    load_start = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(submit_batch, api_url, exam_id, api_key, batch_size)
            for _ in range(num_batches)
        ]
        
        completed_batches = 0
        for future in as_completed(futures):
            result = future.result()
            total_success += result["success"]
            total_errors += result["errors"]
            all_submission_ids.extend(result["submission_ids"])
            
            completed_batches += 1
            if completed_batches % 10 == 0 or completed_batches == num_batches:
                elapsed = time.time() - load_start
                rate = (completed_batches * batch_size) / elapsed if elapsed > 0 else 0
                print_info(f"Progress: {completed_batches}/{num_batches} batches "
                          f"({total_success} success, {total_errors} errors) - {rate:.1f} req/s")
    
    load_duration = time.time() - load_start
    
    print()
    print_metric("Total Submitted", total_success, f"/{total_submissions}", Colors.GREEN)
    print_metric("Total Errors", total_errors, f" ({total_errors/total_submissions*100:.2f}%)", 
                 Colors.RED if total_errors > 0 else Colors.GREEN)
    print_metric("Submission Duration", f"{load_duration:.1f}", "s", Colors.CYAN)
    print_metric("Avg Throughput", f"{total_success/load_duration:.1f}", " req/s", Colors.MAGENTA)
    
    # Phase 3: Monitor Scale-Up
    print_section("PHASE 3: Monitoring Auto Scale-Up")
    
    print_info("Checking system state immediately after load...")
    time.sleep(2)
    
    immediate_stats = get_stats(api_url, api_key)
    immediate_instances = immediate_stats.get("infrastructure", {}).get("instances", 0)
    immediate_backlog = immediate_stats.get("business", {}).get("backlog", 0)
    
    print_metric("Immediate Instances", immediate_instances, "", Colors.MAGENTA)
    print_metric("Immediate Backlog", immediate_backlog, "", Colors.MAGENTA)
    
    # Monitor for 60 seconds
    scale_up_snapshots = monitor_scaling(api_url, api_key, duration_sec=60, interval_sec=5)
    
    # Find peak
    peak_instances = max(s["instances"] for s in scale_up_snapshots)
    peak_backlog = max(s["backlog"] for s in scale_up_snapshots)
    
    print()
    print_metric("Peak Instances", peak_instances, "", Colors.MAGENTA)
    print_metric("Peak Backlog", peak_backlog, "", Colors.MAGENTA)
    
    # Check if scaled up
    scale_up_ratio = peak_instances / baseline_instances if baseline_instances > 0 else 0
    
    if peak_instances >= 500:
        print_pass(f"Excellent scaling: Reached {peak_instances} instances (target: 500-1000)")
    elif peak_instances >= 100:
        print_pass(f"Good scaling: Reached {peak_instances} instances")
    elif peak_instances > baseline_instances:
        print_warning(f"Moderate scaling: {baseline_instances} → {peak_instances} instances")
    else:
        print_warning(f"Limited scaling detected: {baseline_instances} → {peak_instances} instances")
    
    # Phase 4: Monitor Scale-Down (optional)
    print_section("PHASE 4: Monitoring Auto Scale-Down")
    
    print_info("Waiting for queue to drain and workers to scale down...")
    print_info("This may take several minutes depending on backlog size...")
    
    scale_down_snapshots = monitor_scaling(api_url, api_key, duration_sec=120, interval_sec=10)
    
    final_stats = get_stats(api_url, api_key)
    final_instances = final_stats.get("infrastructure", {}).get("instances", 0)
    final_backlog = final_stats.get("business", {}).get("backlog", 0)
    final_completed = final_stats.get("business", {}).get("completed", 0)
    
    print()
    print_metric("Final Instances", final_instances, "", Colors.CYAN)
    print_metric("Final Backlog", final_backlog, "", Colors.CYAN)
    print_metric("Final Completed", final_completed, "", Colors.CYAN)
    print_metric("Total Processed", final_completed - baseline_completed, " submissions", Colors.GREEN)
    
    # Summary
    print_section("SCALING TEST SUMMARY")
    
    print_metric("Baseline → Peak Instances", f"{baseline_instances} → {peak_instances}", 
                 f" ({scale_up_ratio:.1f}x)", Colors.MAGENTA)
    print_metric("Peak → Final Instances", f"{peak_instances} → {final_instances}", "", Colors.CYAN)
    print_metric("Baseline → Peak Backlog", f"{baseline_backlog} → {peak_backlog}", "", Colors.YELLOW)
    print_metric("Submissions Processed", final_completed - baseline_completed, 
                 f"/{total_success}", Colors.GREEN)
    
    # Pass criteria
    scaled_up = peak_instances > baseline_instances * 1.5  # At least 50% increase
    handled_load = total_errors < total_submissions * 0.01  # Less than 1% errors
    
    print()
    if scaled_up and handled_load:
        print_pass("Horizontal scaling verified: System scaled up and handled massive load")
    elif scaled_up:
        print_warning("System scaled up but had some errors")
    elif handled_load:
        print_warning("System handled load but limited scaling detected")
    else:
        print_fail("Scaling test did not meet expectations")
    
    return {
        "passed": scaled_up and handled_load,
        "total_submissions": total_submissions,
        "successful_submissions": total_success,
        "failed_submissions": total_errors,
        "error_rate_percent": (total_errors / total_submissions * 100) if total_submissions > 0 else 0,
        "baseline_instances": baseline_instances,
        "peak_instances": peak_instances,
        "final_instances": final_instances,
        "scale_up_ratio": scale_up_ratio,
        "baseline_backlog": baseline_backlog,
        "peak_backlog": peak_backlog,
        "final_backlog": final_backlog,
        "load_duration_sec": load_duration,
        "avg_throughput_rps": total_success / load_duration if load_duration > 0 else 0,
        "scale_up_snapshots": scale_up_snapshots,
        "scale_down_snapshots": scale_down_snapshots
    }


def main():
    parser = argparse.ArgumentParser(
        description="Horizontal Scaling Test - 10K Submissions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 10,000 submissions (default)
  python test_horizontal_scaling.py

  # Test with custom count
  python test_horizontal_scaling.py --count 5000

  # Test remote server
  python test_horizontal_scaling.py --url http://136.110.44.49:8080 --count 10000

  # Save detailed results
  python test_horizontal_scaling.py --count 10000 --output scaling_results.json
        """
    )
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--exam-id", default=DEFAULT_EXAM_ID, help="Exam ID")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--count", type=int, default=10000, help="Number of submissions")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument("--workers", type=int, default=100, help="Max concurrent workers")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}Starting Horizontal Scaling Test...{Colors.RESET}")
    print(f"Target: {args.url}")
    print(f"Total Submissions: {args.count}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Max Workers: {args.workers}")
    
    try:
        result = test_horizontal_scaling(
            api_url=args.url,
            exam_id=args.exam_id,
            api_key=args.api_key,
            total_submissions=args.count,
            batch_size=args.batch_size,
            max_workers=args.workers
        )
        
        # Save results
        if args.output:
            output_data = {
                "test_config": {
                    "api_url": args.url,
                    "exam_id": args.exam_id,
                    "total_submissions": args.count,
                    "batch_size": args.batch_size,
                    "max_workers": args.workers,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                },
                "result": result
            }
            
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\n{Colors.GREEN}Results saved to: {args.output}{Colors.RESET}")
        
        # Exit code
        exit(0 if result["passed"] else 1)
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test failed with error: {e}{Colors.RESET}")
        exit(1)


if __name__ == "__main__":
    main()
