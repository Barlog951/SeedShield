import sys
import re

def update_version(new_version):
    # Update __init__.py
    with open('seedshield/__init__.py', 'r') as f:
        content = f.read()
    content = re.sub(r'__version__ = .*', f'__version__ = "{new_version}"', content)
    with open('seedshield/__init__.py', 'w') as f:
        f.write(content)

    # Update pyproject.toml
    with open('pyproject.toml', 'r') as f:
        content = f.read()
    content = re.sub(r'version = .*', f'version = "{new_version}"', content)
    with open('pyproject.toml', 'w') as f:
        f.write(content)

if __name__ == "__main__":
    update_version(sys.argv[1])