# SeedShield

A terminal viewer for BIP39 seed phrases that keeps every word masked until you deliberately
reveal it. You enter word *positions* (1-2048); SeedShield shows the matching words from the
BIP39 wordlist one at a time, and masks each one again after 3 seconds.

## Key Features

### Security
- All words masked by default; a revealed word auto-masks after 3 seconds
- Only one word is visible at a time
- No log file by default; nothing about your session is written to disk (`--verbose` is opt-in
  and writes an owner-only `seedshield.log`)
- Entered positions are never logged, even in verbose mode
- Clipboard is cleared immediately after it is read
- Screen is wiped before the terminal is restored, and the alternate screen is used, so revealed
  words don't remain in scrollback
- Best-effort memory clearing on exit (see [Limitations](#limitations))
- Strict input validation: a set of positions is either fully valid or rejected, so words are
  never silently skipped

### User Interface
- Enter several positions at once: `5 12 19` or `5,12,19`
- Sequential reveal mode (`s`)
- Mouse: hover over or click a word to reveal it
- Input from keyboard, clipboard or a file
- Scrolling for long lists; handles terminal resizing
- Linux and macOS; Windows via the optional `windows-curses` extra (not covered by CI)

## Security Guidelines

### Operating Environment
- Use an air-gapped computer whenever possible
- Prefer a clean, live Linux system; avoid shared or public computers
- Mind your surroundings: cameras, reflections, people looking over your shoulder
- Remember that a positions file on disk **is your seed**. Prefer typing positions, and securely
  delete any file you created.

### Limitations
SeedShield is a Python program, so it can only *reduce* how long secrets stay in memory. It
cannot guarantee this:
- It overwrites the wordlist strings (which include every revealed word), the typed input and
  the clipboard text after use.
- Python integers (the positions), intermediate string copies and curses' own screen buffers
  cannot be wiped reliably.
- Positions are typed on the keyboard, so SeedShield offers no protection against keyloggers
  or a compromised machine.

Treat SeedShield as one layer of a careful process, not as a guarantee.

## Installation

```bash
# From PyPI
pip install seedshield

# On Windows
pip install "seedshield[windows]"

# Docker (clipboard input is unavailable inside a container)
docker run -it --rm barlog951/seedshield
```

## Usage

```bash
# Interactive mode
seedshield

# Load positions from a file (spaces, commas or newlines between positions)
seedshield -i positions.txt

# Use a custom wordlist (must have no blank lines or duplicates)
seedshield -w custom_words.txt

# Opt-in debug log (seedshield.log in the current directory, mode 0600)
seedshield --verbose
```

### Input screen
- Type one or more positions and press Enter: `5`, `5 12 19` or `5,12,19`
- `v` + Enter: read positions from the clipboard (same format), then clear the clipboard
- `q` + Enter: quit

### Viewing screen
- `s` - reveal the next word (sequential mode)
- `r` - restart the sequence (shown after the last word)
- `n` - enter new positions
- `q` - quit, wiping the screen
- ↑↓ - scroll
- Mouse hover or click - reveal that word for 3 seconds

## Development

```bash
git clone https://github.com/Barlog951/SeedShield.git
cd SeedShield
pip install -e ".[test]"

# Unit tests plus end-to-end tests that drive the real UI through a pty
pytest

# Quality checks
pylint seedshield && flake8 seedshield && mypy seedshield
```

### Docker build
```bash
./build.sh                       # builds seedshield:<version> and seedshield:latest
docker run -it --rm seedshield   # interactive
docker run -it --rm -v "$(pwd)/positions.txt:/positions.txt:ro" seedshield -i /positions.txt
```
The image installs the package normally (no source tree) and runs as a non-root user.

### Technical Architecture
- Python 3.10+ with type hints throughout (mypy strict on definitions)
- Unit tests with mocked curses plus pty-based end-to-end tests (~95% coverage)
- Curses UI with guaranteed terminal cleanup; xterm mouse mode 1003 for hover
- Releases are cut automatically by semantic-release from conventional commits on `main`

### Code Organization
- `main.py` - entry point and argument handling
- `secure_word_interface.py` - coordinates input, display and state
- `input_handler.py` - parses and validates positions (keyboard, clipboard, file)
- `display_handler.py` - rendering and masking
- `state_handler.py` - reveal state, navigation and timeouts
- `ui_manager.py` - curses lifecycle, mouse setup and cleanup
- `secure_memory.py` - best-effort memory and clipboard clearing
- `config.py` - settings, constants and logging
- `data/english.txt` - bundled BIP39 English wordlist

## Legal Notice

### Disclaimer
SeedShield helps you view seed words more safely, but it cannot secure the machine it runs on.
You are responsible for your operating environment. Do not rely on SeedShield as your only
security measure.

### License
Released under the MIT License. See the LICENSE file for complete terms.
