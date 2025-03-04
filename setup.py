# setup.py
import subprocess
import pathlib
import sys
from setuptools import setup, find_namespace_packages
from setuptools.command.build_py import build_py as _build_py


class PreBuild(_build_py):
    def run(self):
        # Path to pre_build.py in the same directory as setup.py
        script_path = pathlib.Path(__file__).parent / "pre_build.py"
        if script_path.exists():
            print("== Running pre_build script ==")
            # Run the script with the same Python interpreter
            subprocess.check_call([sys.executable, str(script_path)])
        else:
            print(f"WARNING: {script_path} not found; skipping pre-build step.")

        # Continue with the normal build
        super().run()


setup(
    name="seedshield",
    version="0.2.1",  # This should match VERSION in seedshield/config.py

    packages=find_namespace_packages(
        include=['seedshield', 'seedshield.*']
    ),
    include_package_data=True,
    package_data={
        'seedshield': ['data/english.txt'],
    },
    cmdclass={
        "build_py": PreBuild,
    },
)