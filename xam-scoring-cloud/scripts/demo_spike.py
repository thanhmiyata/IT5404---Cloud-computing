#!/usr/bin/env python3
"""
Demo Scenario Script: End-of-Exam Spike
Simulates a high burst of traffic to demonstrate autoscaling and queue processing.
"""

import argparse
import sys
import os
import subprocess
import time
import requests
import json

# Disable warnings
requests.packages.urllib3.disable_warnings()

def get_stats(url, key):
    try:
        # Adjust URL to point to stats endpoint
        # If url is .../v1/exams/..., we need base.
        # But user wraps usually provide full submission URL to load generator.
        # We assume base URL is passed or derived.
        
        # Heuristic: split by /v1/
        base = url.split("/v1/")[0]
        stats_url = f"{base}/v1/internal/stats"
        
        resp = requests.get(stats_url, headers={"X-API-KEY": key}, timeout=2)
        if resp.status_code == 200:
            return resp.json().get("business", {})
    except Exception:
        pass
    return {}

def main():
    parser = argparse.ArgumentParser(description="Demo Script: End-of-Exam Spike")
    parser.add_argument("-n", "--number", type=int, default=1000, help="Number of submissions")
    parser.add_argument("-c", "--concurrency", type=int, default=50, help="Concurrency level")
    parser.add_argument("--url", type=str, default="http://localhost:8080/v1/exams/exam_001/submissions", help="Target API URL")
    parser.add_argument("--key", type=str, default="change-me", help="API Key")
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    make_load_script = os.path.join(script_dir, "make_load.py")
    
    if not os.path.exists(make_load_script):
        print(f"Error: {make_load_script} not found.")
        sys.exit(1)

    print("\n" + "="*60)
    print("      DEMO SCENARIO: END-OF-EXAM SPIKE")
    print("="*60)
    print("Scenario: The exam has just finished.")
    print(f"Action:   {args.number} students are submitting their answers simultaneously.")
    print(f"Target:   {args.url}")
    print("-" * 60)

    # 1. Initial State
    print("\n[STEP 1] Capturing baseline metrics...")
    stats = get_stats(args.url, args.key)
    if stats:
        print(f" > Initial Backlog : {stats.get('backlog', 0)}")
        print(f" > Total Processed : {stats.get('completed', 0)}")
    else:
        print(" > Only Load Generator will run (Stats API unreachable/auth failed).")

    # 2. Burst
    print("\n[STEP 2] Simulating traffic burst...")
    time.sleep(1)
    
    cmd = [
        sys.executable, make_load_script,
        "-n", str(args.number),
        "-c", str(args.concurrency),
        "--url", args.url,
        "--key", args.key
    ]
    
    try:
        # Run load generator
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("Load generation failed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)

    # 3. Drain Monitoring
    print("\n[STEP 3] Monitoring queue processing (CTRL+C to stop)...")
    print("-" * 60)
    print(f"{'TIME':<10} | {'BACKLOG':<10} | {'COMPLETED':<10} | {'RATE (approx)'}")
    print("-" * 60)
    
    start_monitor = time.time()
    last_completed = stats.get('completed', 0) if stats else 0
    
    try:
        while True:
            stats = get_stats(args.url, args.key)
            if not stats:
                print("Stats unavailable...")
                time.sleep(2)
                continue
                
            backlog = stats.get('backlog', 0)
            completed = stats.get('completed', 0)
            
            # Simple rate calc
            now = time.time()
            if now - start_monitor > 0:
                # This is instantaneous rate since script start, rough estimate
                pass 
            
            print(f"{time.strftime('%H:%M:%S'):<10} | {backlog:<10} | {completed:<10} | Priority Processing...")
            
            if backlog == 0 and completed >= (last_completed + args.number):
                print("-" * 60)
                print("Spike absorbed. Queue empty.")
                break
                
            if backlog == 0:
                # Might be done or just empty for a moment
                # But if we just finished submitting, and backlog is 0, mostly done.
                if completed >= last_completed: # simplistic check
                     print("-" * 60)
                     print("Queue drained.")
                     break
            
            time.sleep(1.5)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

    print("="*60 + "\n")

if __name__ == "__main__":
    main()
