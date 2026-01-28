#!/usr/bin/env python3
"""
Load Generator Tool for Exam Scoring API.
Simulates concurrent user submissions to test system scalability.
"""

import argparse
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List

import requests

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_URL = "http://localhost:8080/v1/exams/exam_001/submissions"
DEFAULT_API_KEY = "change-me"
USER_PREFIXES = ["student", "tester", "candidate", "demo"]


@dataclass
class LoadTestConfig:
    """Configuration for the load test execution."""
    url: str
    total_requests: int
    concurrency: int
    api_key: str


class LoadGenerator:
    """
    Handles the generation and execution of synthetic load against the target API.
    """

    def __init__(self, config: LoadTestConfig):
        self.config = config
        # Use a session to pool connections (simulating keep-alive behavior closer to real browsers)
        self.session = requests.Session()
        
        # Tune connection pool to match concurrency
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=config.concurrency,
            pool_maxsize=config.concurrency
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-KEY": self.config.api_key
        })

    def _generate_payload(self, index: int) -> Dict[str, Any]:
        """Generates a random submission payload."""
        user_id = f"{random.choice(USER_PREFIXES)}_{random.randint(1000, 9999)}_{index}"
        
        # dynamic question generation (q1..q5)
        answers = [
            {"questionId": f"q{i}", "choice": random.choice(["A", "B", "C", "D"])}
            for i in range(1, 6)
        ]
        
        return {
            "userId": user_id,
            "answers": answers
        }

    def _send_single_request(self, request_id: int) -> bool:
        """Sends a single HTTP POST request and logs the result."""
        payload = self._generate_payload(request_id)
        
        try:
            start_time = time.perf_counter()
            response = self.session.post(
                self.config.url, 
                json=payload, 
                timeout=10
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code in (200, 202):
                logger.info(
                    f"[OK]   ReqID: {request_id:<4} | User: {payload['userId']:<18} | "
                    f"Status: {response.status_code} | Time: {duration_ms}ms"
                )
                return True
            else:
                logger.warning(
                    f"[FAIL] ReqID: {request_id:<4} | Status: {response.status_code} | "
                    f"Msg: {response.text[:50]}"
                )
                return False

        except requests.RequestException as e:
            logger.error(f"[ERR]  ReqID: {request_id:<4} | Exception: {str(e)}")
            return False

    def run(self):
        """Executes the load test suite."""
        logger.info("=" * 60)
        logger.info(f"Starting Load Test")
        logger.info(f"Target URL   : {self.config.url}")
        logger.info(f"Requests     : {self.config.total_requests}")
        logger.info(f"Concurrency  : {self.config.concurrency}")
        logger.info("=" * 60)

        success_count = 0
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.config.concurrency) as executor:
            # Submit all tasks
            futures = [
                executor.submit(self._send_single_request, i + 1) 
                for i in range(self.config.total_requests)
            ]
            
            # Process results as they complete
            for future in as_completed(futures):
                if future.result():
                    success_count += 1

        total_duration = time.time() - start_time
        self._print_summary(success_count, total_duration)

    def _print_summary(self, success_count: int, duration: float):
        """Prints the final summary of the test run."""
        logger.info("-" * 60)
        logger.info("Load Test Completed")
        logger.info(f"Total Time   : {duration:.2f}s")
        logger.info(f"Success Rate : {success_count}/{self.config.total_requests} ({(success_count/self.config.total_requests)*100:.1f}%)")
        logger.info(f"Avg RPS      : {self.config.total_requests / duration:.2f} req/s")
        logger.info("-" * 60)


def parse_arguments() -> LoadTestConfig:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Professional Load Generator for Exam Scoring API",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("-n", "--number", type=int, default=10, help="Total number of requests to send")
    parser.add_argument("-c", "--concurrency", type=int, default=1, help="Number of concurrent threads")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="Target API Endpoint")
    parser.add_argument("--key", type=str, default=DEFAULT_API_KEY, help="API Key for authentication")
    
    args = parser.parse_args()
    
    return LoadTestConfig(
        url=args.url,
        total_requests=args.number,
        concurrency=args.concurrency,
        api_key=args.key
    )


if __name__ == "__main__":
    try:
        config = parse_arguments()
        generator = LoadGenerator(config)
        generator.run()
    except KeyboardInterrupt:
        logger.warning("\n[STOP] Load test interrupted by user.")
    except Exception as e:
        logger.exception(f"Critical error: {e}")
