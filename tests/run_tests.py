import subprocess
import time
from pathlib import Path

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

tests = []

for test in Path("tests").rglob("test_*.py"):

    if "archive" in test.parts:
        continue

    tests.append(test)

tests = sorted(tests)

passed = []
failed = []

print("=" * 70)
print("ATLAS VALIDATION SUITE")
print("=" * 70)

suite_start = time.perf_counter()

for test in tests:

    print(f"\n>>> {test}")

    start = time.perf_counter()

    result = subprocess.run(
        ["python3", str(test)]
    )

    elapsed = time.perf_counter() - start

    if result.returncode == 0:

        print(f"{GREEN}PASS{RESET} ({elapsed:.2f}s)")
        passed.append(test)

    else:

        print(f"{RED}FAIL{RESET} ({elapsed:.2f}s)")
        failed.append(test)

suite_elapsed = time.perf_counter() - suite_start

print("\n" + "=" * 70)
print(f"TOTAL TESTS : {len(tests)}")
print(f"{GREEN}PASSED{RESET}      : {len(passed)}")
print(f"{RED}FAILED{RESET}      : {len(failed)}")
print(f"TOTAL TIME  : {suite_elapsed:.2f}s")

if failed:

    print("\nFAILED TESTS:")

    for t in failed:

        print(f" - {t}")

print("=" * 70)

exit(1 if failed else 0)
