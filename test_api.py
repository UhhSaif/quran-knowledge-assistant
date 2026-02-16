"""Test script for the Quran Knowledge Assistant API."""

import requests
import json
import time
from typing import Dict, Any


class APITester:
    """Test harness for the Quran Assistant API."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0

    def print_header(self, text: str) -> None:
        """Print a formatted header."""
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def print_test(self, name: str, passed: bool, details: str = "") -> None:
        """Print test result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} - {name}")
        if details:
            print(f"      {details}")

        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def test_health(self) -> bool:
        """Test /health endpoint."""
        self.print_header("Testing Health Endpoint")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.print_test(
                    "Health endpoint responds",
                    True,
                    f"Status: {data.get('status')}, RAG Ready: {data.get('rag_ready')}"
                )
                return True
            else:
                self.print_test(
                    "Health endpoint responds",
                    False,
                    f"Status code: {response.status_code}"
                )
                return False

        except Exception as e:
            self.print_test("Health endpoint responds", False, str(e))
            return False

    def test_chat(self, message: str, expected_keywords: list = None) -> bool:
        """Test /chat endpoint."""
        print(f"\nTesting chat with query: '{message}'")

        try:
            start = time.time()
            response = requests.post(
                f"{self.base_url}/chat",
                json={"message": message, "session_id": "test"},
                timeout=60
            )
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                response_text = data.get("response", "")

                self.print_test(
                    "Chat endpoint responds",
                    True,
                    f"Latency: {latency:.0f}ms, Response length: {len(response_text)}"
                )

                # Print response preview
                preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                print(f"      Response preview: {preview}")

                # Check for expected keywords if provided
                if expected_keywords:
                    found = [kw for kw in expected_keywords if kw.lower() in response_text.lower()]
                    self.print_test(
                        "Response contains expected keywords",
                        len(found) > 0,
                        f"Found: {found}"
                    )

                return True
            else:
                self.print_test(
                    "Chat endpoint responds",
                    False,
                    f"Status code: {response.status_code}"
                )
                return False

        except Exception as e:
            self.print_test("Chat endpoint responds", False, str(e))
            return False

    def test_error_endpoint(self) -> bool:
        """Test /test-error endpoint."""
        self.print_header("Testing Error Endpoint")

        try:
            response = requests.get(f"{self.base_url}/test-error", timeout=10)

            # This endpoint should return 500
            if response.status_code == 500:
                self.print_test(
                    "Error endpoint returns 500",
                    True,
                    "Error handling working correctly"
                )
                return True
            else:
                self.print_test(
                    "Error endpoint returns 500",
                    False,
                    f"Got status code: {response.status_code}"
                )
                return False

        except Exception as e:
            self.print_test("Error endpoint responds", False, str(e))
            return False

    def test_root(self) -> bool:
        """Test root endpoint."""
        self.print_header("Testing Root Endpoint")

        try:
            response = requests.get(f"{self.base_url}/", timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.print_test(
                    "Root endpoint responds",
                    True,
                    f"Service: {data.get('service')}"
                )
                return True
            else:
                self.print_test(
                    "Root endpoint responds",
                    False,
                    f"Status code: {response.status_code}"
                )
                return False

        except Exception as e:
            self.print_test("Root endpoint responds", False, str(e))
            return False

    def run_all_tests(self) -> None:
        """Run all tests."""
        print("\n" + "=" * 60)
        print("  QURAN KNOWLEDGE ASSISTANT - API TEST SUITE")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")

        # Test root endpoint
        self.test_root()

        # Test health
        self.test_health()

        # Test chat with different query types
        self.print_header("Testing Chat Endpoint")

        # Verse search query
        self.test_chat(
            "What does the Quran say about patience?",
            expected_keywords=["patience", "surah", "verse"]
        )

        time.sleep(2)  # Rate limiting

        # Prophet query
        self.test_chat(
            "Find verses about Prophet Moses",
            expected_keywords=["moses", "musa"]
        )

        time.sleep(2)

        # Context query
        self.test_chat(
            "What's the context of Surah Al-Fatiha?",
            expected_keywords=["fatiha", "context"]
        )

        # Test error handling
        self.test_error_endpoint()

        # Print summary
        self.print_header("TEST SUMMARY")
        total = self.passed + self.failed
        print(f"Total tests: {total}")
        print(f"Passed: \033[92m{self.passed}\033[0m")
        print(f"Failed: \033[91m{self.failed}\033[0m")

        if self.failed == 0:
            print("\n\033[92m✓ ALL TESTS PASSED!\033[0m\n")
        else:
            print(f"\n\033[91m✗ {self.failed} TEST(S) FAILED\033[0m\n")


if __name__ == "__main__":
    import sys

    # Get base URL from command line or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"

    tester = APITester(base_url)
    tester.run_all_tests()
