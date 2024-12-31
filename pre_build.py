import pytest
import sys

print("Running tests before build...")

exit_code = pytest.main(["tests/"])
if exit_code != 0:
    print("Tests failed! Build aborted.")
    sys.exit(1)

print("Tests passed! Proceeding with build...")