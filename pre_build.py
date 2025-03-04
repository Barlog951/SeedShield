import pytest
import sys
import os

print("Running tests before build...")

# Skip tests in build environment
if os.environ.get('BUILD_SKIP_TESTS') == 'true':
    print("Tests skipped in build environment")
    sys.exit(0)

exit_code = pytest.main(["tests/"])
if exit_code != 0:
    print("Tests failed! Build aborted.")
    sys.exit(1)

print("Tests passed! Proceeding with build...")