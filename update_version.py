import sys
import re


def update_version(new_version):
    # seedshield/config.py is the single version source;
    # pyproject.toml reads it via dynamic metadata
    with open("seedshield/config.py", "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r"VERSION = .*", f'VERSION = "{new_version}"', content)
    with open("seedshield/config.py", "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    update_version(sys.argv[1])
