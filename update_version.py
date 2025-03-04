import sys
import re

def update_version(new_version):
    # Update config.py (primary version source)
    with open('seedshield/config.py', 'r') as f:
        content = f.read()
    content = re.sub(r'VERSION = .*', f'VERSION = "{new_version}"', content)
    with open('seedshield/config.py', 'w') as f:
        f.write(content)

    # Update pyproject.toml
    with open('pyproject.toml', 'r') as f:
        content = f.read()
    content = re.sub(r'version = .*', f'version = "{new_version}"', content, count=1)
    with open('pyproject.toml', 'w') as f:
        f.write(content)
        
    # Update setup.py
    with open('setup.py', 'r') as f:
        content = f.read()
    content = re.sub(r'version="[^"]*"', f'version="{new_version}"', content)
    with open('setup.py', 'w') as f:
        f.write(content)

if __name__ == "__main__":
    update_version(sys.argv[1])