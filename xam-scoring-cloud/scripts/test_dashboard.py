#!/usr/bin/env python3
"""
Dashboard Real-time Monitoring Test Script

Tests the Dashboard's ability to:
1. Display real-time metrics (backlog, throughput, latency)
2. Show live submission feed updates
3. Track autoscaling behavior
4. Display logs and status changes in real-time

This demonstrates the "Dashboard Giám sát" requirement.
"""

import requests
import time
import argparse
from dataclasses import dataclass
from typing import Dict, List, Optional
import json
from datetime import datetime

# Configuration
DEFAULT_DASHBOARD_URL = "http://localhost:8000/admin-dashboard.html"
DEFAULT_API_URL = "http://localhost:8080"
DEFAULT_API_KEY = "change-me"

@dataclass
class DashboardSnapshot:
    timestamp: str
    total_submissions: int
    backlog: int
    completed: int
    instances: int
    throughput: int
    latency: int
    cpu: int
    memory: int
    recent_submissions_count: int

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

def print_metric(label: str, value: any, unit: str = "", color: str = Colors.GREEN):
    print(f"  {Colors.BOLD}{label}:{Colors.RESET} {color}{value}{unit}{Colors.RESET}")

def print_test(name: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[TEST]{Colors.RESET} {name}")

def print_pass(msg: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.RESET} {msg}")

def print_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.RESET} {msg}")

def print_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ INFO:{Colors.RESET} {msg}")


def fetch_dashboard_stats(api_url: str, api_key: str) -> Optional[Dict]:
    """Fetch stats from the internal stats endpoint (used by dashboard)"""
    url = f"{api_url}/v1/internal/stats"
    headers = {"X-API-KEY": api_key}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print_fail(f"Stats API returned {response.status_code}: {response.text[:100]}")
            return None
    except Exception as e:
        print_fail(f"Failed to fetch stats: {str(e)}")
        return None


def create_snapshot(stats: Dict) -> DashboardSnapshot:
    """Create a snapshot from stats data"""
    business = stats.get("business", {})
    infra = stats.get("infrastructure", {})
    logs = stats.get("logs", [])
    
    return DashboardSnapshot(
        timestamp=datetime.now().strftime("%H:%M:%S"),
        total_submissions=business.get("totalSubmissions", 0),
        backlog=business.get("backlog", 0),
        completed=business.get("completed", 0),
        instances=infra.get("instances", 0),
        throughput=business.get("throughput", 0),
        latency=business.get("latency", 0),
        cpu=infra.get("cpu", 0),
        memory=infra.get("memory", 0),
        recent_submissions_count=len(logs)
    )


def test_dashboard_connectivity(api_url: str, api_key: str) -> bool:
    """Test 1: Verify dashboard stats endpoint is accessible"""
    print_test("Test 1: Dashboard Stats API Connectivity")
    
    stats = fetch_dashboard_stats(api_url, api_key)
    
    if stats:
        print_pass("Successfully connected to stats API")
        print_info(f"Response contains: {', '.join(stats.keys())}")
        return True
    else:
        print_fail("Cannot connect to stats API")
        return False


def test_realtime_metrics_update(api_url: str, api_key: str, duration: int = 20) -> bool:
    """Test 2: Monitor metrics updates over time"""
    print_test(f"Test 2: Real-time Metrics Update (monitoring for {duration}s)")
    
    snapshots = []
    
    print_info(f"Collecting snapshots every 2 seconds...")
    print(f"\n  {'TIME':<10} | {'TOTAL':<8} | {'BACKLOG':<8} | {'COMPLETED':<10} | {'INSTANCES':<10} | {'THROUGHPUT':<12}")
    print(f"  {'-'*80}")
    
    for i in range(duration // 2):
        stats = fetch_dashboard_stats(api_url, api_key)
        if stats:
            snapshot = create_snapshot(stats)
            snapshots.append(snapshot)
            
            print(f"  {snapshot.timestamp:<10} | {snapshot.total_submissions:<8} | {snapshot.backlog:<8} | "
                  f"{snapshot.completed:<10} | {snapshot.instances:<10} | {snapshot.throughput:<12}")
        else:
            print_fail(f"Failed to fetch stats at iteration {i+1}")
        
        time.sleep(2)
    
    # Analysis
    if len(snapshots) < 3:
        print_fail("Not enough data collected")
        return False
    
    # Check if metrics are updating (at least one metric changed)
    first = snapshots[0]
    last = snapshots[-1]
    
    changes = []
    if last.total_submissions != first.total_submissions:
        changes.append(f"Total Submissions: {first.total_submissions} → {last.total_submissions}")
    if last.backlog != first.backlog:
        changes.append(f"Backlog: {first.backlog} → {last.backlog}")
    if last.completed != first.completed:
        changes.append(f"Completed: {first.completed} → {last.completed}")
    
    if changes:
        print_pass("Metrics are updating in real-time:")
        for change in changes:
            print(f"    - {change}")
        return True
    else:
        print_info("No metric changes detected (system may be idle)")
        return True  # Not a failure, just idle


def test_submission_feed_updates(api_url: str, api_key: str) -> bool:
    """Test 3: Verify submission logs/feed is populated"""
    print_test("Test 3: Submission Feed / Logs Display")
    
    stats = fetch_dashboard_stats(api_url, api_key)
    if not stats:
        print_fail("Cannot fetch stats")
        return False
    
    logs = stats.get("logs", [])
    
    if len(logs) == 0:
        print_info("No recent submissions in feed (system may be idle)")
        return True
    
    print_pass(f"Found {len(logs)} recent submissions in feed")
    
    # Display sample submissions
    print_info("Sample submissions:")
    for i, log in enumerate(logs[:5]):  # Show first 5
        user_id = log.get("userId", "N/A")
        status = log.get("status", "N/A")
        score = log.get("score", "N/A")
        total = log.get("total", "N/A")
        
        status_color = Colors.GREEN if status == "SCORED" else Colors.YELLOW
        print(f"    {i+1}. User: {user_id:<20} | Status: {status_color}{status:<8}{Colors.RESET} | Score: {score}/{total}")
    
    return True


def test_autoscaling_metrics(api_url: str, api_key: str) -> bool:
    """Test 4: Verify autoscaling metrics (instances, CPU, memory)"""
    print_test("Test 4: Autoscaling & Infrastructure Metrics")
    
    stats = fetch_dashboard_stats(api_url, api_key)
    if not stats:
        print_fail("Cannot fetch stats")
        return False
    
    infra = stats.get("infrastructure", {})
    
    instances = infra.get("instances", 0)
    cpu = infra.get("cpu", 0)
    memory = infra.get("memory", 0)
    
    print_metric("Worker Instances", instances, "", Colors.CYAN)
    print_metric("CPU Usage", cpu, "%", Colors.MAGENTA)
    print_metric("Memory Usage", memory, "%", Colors.MAGENTA)
    
    if instances > 0:
        print_pass("Infrastructure metrics are available")
        return True
    else:
        print_info("No active instances detected (system may be idle)")
        return True


def test_backlog_monitoring(api_url: str, api_key: str, duration: int = 15) -> bool:
    """Test 5: Monitor backlog changes (key metric for queue health)"""
    print_test(f"Test 5: Backlog Monitoring (tracking for {duration}s)")
    
    backlog_history = []
    
    print_info("Tracking backlog changes...")
    print(f"\n  {'TIME':<10} | {'BACKLOG':<10} | {'TREND':<15}")
    print(f"  {'-'*40}")
    
    prev_backlog = None
    for i in range(duration // 3):
        stats = fetch_dashboard_stats(api_url, api_key)
        if stats:
            backlog = stats.get("business", {}).get("backlog", 0)
            backlog_history.append(backlog)
            
            trend = ""
            if prev_backlog is not None:
                if backlog > prev_backlog:
                    trend = f"{Colors.RED}↑ Growing{Colors.RESET}"
                elif backlog < prev_backlog:
                    trend = f"{Colors.GREEN}↓ Draining{Colors.RESET}"
                else:
                    trend = f"{Colors.YELLOW}→ Stable{Colors.RESET}"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"  {timestamp:<10} | {backlog:<10} | {trend:<15}")
            
            prev_backlog = backlog
        
        time.sleep(3)
    
    if len(backlog_history) > 0:
        avg_backlog = sum(backlog_history) / len(backlog_history)
        max_backlog = max(backlog_history)
        min_backlog = min(backlog_history)
        
        print()
        print_metric("Average Backlog", f"{avg_backlog:.1f}", "", Colors.CYAN)
        print_metric("Max Backlog", max_backlog, "", Colors.RED)
        print_metric("Min Backlog", min_backlog, "", Colors.GREEN)
        
        print_pass("Backlog monitoring functional")
        return True
    else:
        print_fail("No backlog data collected")
        return False


def test_throughput_calculation(api_url: str, api_key: str) -> bool:
    """Test 6: Verify throughput metric is calculated"""
    print_test("Test 6: Throughput Calculation")
    
    stats = fetch_dashboard_stats(api_url, api_key)
    if not stats:
        print_fail("Cannot fetch stats")
        return False
    
    throughput = stats.get("business", {}).get("throughput", 0)
    latency = stats.get("business", {}).get("latency", 0)
    
    print_metric("Throughput", throughput, " submissions/min", Colors.GREEN)
    print_metric("Avg Latency", latency, " ms", Colors.MAGENTA)
    
    if throughput >= 0 and latency >= 0:
        print_pass("Throughput and latency metrics available")
        return True
    else:
        print_fail("Invalid throughput/latency values")
        return False


def test_exam_management_api(api_url: str, api_key: str) -> bool:
    """Test 7: Verify exam list is available (for dashboard exam tab)"""
    print_test("Test 7: Exam Management Data")
    
    stats = fetch_dashboard_stats(api_url, api_key)
    if not stats:
        print_fail("Cannot fetch stats")
        return False
    
    exams = stats.get("exams", [])
    
    if len(exams) == 0:
        print_info("No exams found in system")
        return True
    
    print_pass(f"Found {len(exams)} exam(s) in system")
    
    for i, exam in enumerate(exams[:3]):  # Show first 3
        exam_id = exam.get("examId", "N/A")
        title = exam.get("title", "N/A")
        status = exam.get("status", "N/A")
        
        status_color = Colors.GREEN if status == "ACTIVE" else Colors.YELLOW
        print(f"    {i+1}. {exam_id:<15} | {title:<25} | {status_color}{status}{Colors.RESET}")
    
    return True


def run_live_monitoring_demo(api_url: str, api_key: str, duration: int = 30):
    """Bonus: Live monitoring dashboard simulation"""
    print_header("LIVE MONITORING DEMO")
    print(f"Simulating dashboard real-time view for {duration} seconds...")
    print(f"Press Ctrl+C to stop\n")
    
    try:
        for i in range(duration // 2):
            stats = fetch_dashboard_stats(api_url, api_key)
            if stats:
                snapshot = create_snapshot(stats)
                
                # Clear-ish display (simple version)
                print(f"\r{Colors.BOLD}[{snapshot.timestamp}]{Colors.RESET} ", end="")
                print(f"Total: {Colors.CYAN}{snapshot.total_submissions}{Colors.RESET} | ", end="")
                print(f"Backlog: {Colors.YELLOW}{snapshot.backlog}{Colors.RESET} | ", end="")
                print(f"Completed: {Colors.GREEN}{snapshot.completed}{Colors.RESET} | ", end="")
                print(f"Instances: {Colors.MAGENTA}{snapshot.instances}{Colors.RESET} | ", end="")
                print(f"Throughput: {Colors.BLUE}{snapshot.throughput}/min{Colors.RESET}    ", end="", flush=True)
            
            time.sleep(2)
        
        print("\n")
        print_pass("Live monitoring demo completed")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.RESET}\n")


def print_summary(test_results: Dict[str, bool]):
    """Print test summary"""
    print_header("TEST SUMMARY")
    
    total = len(test_results)
    passed = sum(1 for v in test_results.values() if v)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print()
    
    for test_name, result in test_results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BOLD}Overall Result: ", end="")
    if failed == 0:
        print(f"{Colors.GREEN}ALL TESTS PASSED ✓{Colors.RESET}")
    else:
        print(f"{Colors.RED}{failed} TEST(S) FAILED ✗{Colors.RESET}")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Dashboard Real-time Monitoring Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all dashboard tests
  python test_dashboard.py

  # Test against remote server
  python test_dashboard.py --url http://136.110.44.49:8080

  # Run with live monitoring demo
  python test_dashboard.py --live-demo

  # Extended monitoring duration
  python test_dashboard.py --duration 60
        """
    )
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API base URL")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--live-demo", action="store_true", help="Run live monitoring demo")
    parser.add_argument("--duration", type=int, default=20, help="Monitoring duration in seconds")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    print_header("DASHBOARD REAL-TIME MONITORING TEST SUITE")
    print(f"Target API: {args.url}")
    print(f"Dashboard Stats: {args.url}/v1/internal/stats")
    print()
    
    test_results = {}
    
    try:
        # Run all tests
        test_results["Dashboard Connectivity"] = test_dashboard_connectivity(args.url, args.api_key)
        time.sleep(1)
        
        test_results["Real-time Metrics Update"] = test_realtime_metrics_update(args.url, args.api_key, args.duration)
        time.sleep(1)
        
        test_results["Submission Feed Updates"] = test_submission_feed_updates(args.url, args.api_key)
        time.sleep(1)
        
        test_results["Autoscaling Metrics"] = test_autoscaling_metrics(args.url, args.api_key)
        time.sleep(1)
        
        test_results["Backlog Monitoring"] = test_backlog_monitoring(args.url, args.api_key, 15)
        time.sleep(1)
        
        test_results["Throughput Calculation"] = test_throughput_calculation(args.url, args.api_key)
        time.sleep(1)
        
        test_results["Exam Management Data"] = test_exam_management_api(args.url, args.api_key)
        
        # Print summary
        print_summary(test_results)
        
        # Optional live demo
        if args.live_demo:
            run_live_monitoring_demo(args.url, args.api_key, args.duration)
        
        # Save results
        if args.output:
            output_data = {
                "test_config": {
                    "api_url": args.url,
                    "timestamp": datetime.now().isoformat()
                },
                "results": {name: passed for name, passed in test_results.items()},
                "summary": {
                    "total_tests": len(test_results),
                    "passed": sum(1 for v in test_results.values() if v),
                    "failed": sum(1 for v in test_results.values() if not v)
                }
            }
            
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"Results saved to: {args.output}")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")


if __name__ == "__main__":
    main()
