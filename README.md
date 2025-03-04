# SeedShield

A secure BIP39 seed phrase viewer with enterprise-grade security features, designed for safe interaction with cryptocurrency seed phrases. SeedShield emphasizes security and usability while maintaining zero data persistence.

## Key Features

### Security-First Design
- Zero data persistence - all operations occur in volatile memory
- Secure memory handling with automatic cleanup and sanitization
- Advanced masking system with consistent pattern length
- Timed reveal system with 3-second auto-mask
- Intelligent clipboard management with automatic clearing
- Comprehensive input validation and sanitization
- Anti-keylogging protection via mouse-based interaction
- Secure error handling with proper cleanup
- TTY/non-TTY mode handling for secure input
- Adaptive timeout mechanisms

### User Interface
- Interactive word reveal with hover functionality
- Sequential phrase revelation mode
- Multi-source input support (file/clipboard)
- Responsive terminal interface
- Cross-platform support (Windows/Linux/MacOS)
- Dynamic scrolling for long word lists
- Clear command feedback

## Security Guidelines

### Operating Environment
- Use an air-gapped computer whenever possible
- Run on a secure, clean operating system
  - Recommended: Live Linux distribution
  - Avoid shared or public computers
- Maintain physical security awareness
  - Check for surveillance devices
  - Use privacy screens when necessary
- Implement proper memory management
  - Clear system RAM after usage
  - Utilize secure memory wiping tools

### Usage Best Practices

#### Input Management
1. Prefer clipboard input for multiple words (use 'v' command)
2. Clipboard contents are automatically cleared after use
3. Double-check word positions before revelation
4. All input is automatically validated and sanitized
5. Invalid inputs are safely rejected

#### Word Revelation Protocol
1. Use sequential reveal mode ('s' command) for systematic checking
2. Utilize mouse hover for temporary word exposure
3. Allow auto-masking timer to complete
4. One word visible at a time for maximum security
5. Use scroll navigation for longer lists

## Installation

```bash
# Install via pip
pip install seedshield

# Install with development dependencies
pip install -e ".[test]"

# Using Docker
docker run -it --rm seedshield
docker run -it --rm -v $(pwd)/input.txt:/input.txt seedshield -i /input.txt
```

## Usage Guide

### Basic Commands
```bash
# Start interactive mode
seedshield

# Use custom wordlist
seedshield -w custom_words.txt

# Load from positions file
seedshield -i positions.txt
```

### Interactive Controls
- `v` - Import and validate clipboard data
- `n` - New input mode
- `s` - Sequential reveal mode
- `r` - Reset current sequence
- `q` - Safe exit with cleanup
- Mouse hover - Temporary reveal (3s timeout)
- ↑↓ Arrow keys - Scroll through lists

## Development

### Getting Started
```bash
# Clone repository
git clone https://github.com/Barlog951/SeedShield.git

# Setup development environment
cd seedshield
pip install -e ".[test]"

# Run test suite
pytest
```

### Docker Build

#### Building from Source
```bash
# Clone the repository
git clone https://github.com/Barlog951/SeedShield.git
cd SeedShield

# Build local image
chmod +x build.sh
./build.sh

# Test run
docker run -it --rm seedshield --help

# Run with mounted input file
docker run -it --rm -v $(pwd)/input.txt:/input.txt seedshield -i /input.txt

# Run interactive mode
docker run -it --rm seedshield
```
Note: Built image contains minimal dependencies and runs as non-root user for security.

### Technical Architecture
- Python 3.6+ with type hints throughout the codebase
- Comprehensive test suite (73% coverage) with security-focused tests
- Platform-agnostic clipboard handling for cross-platform compatibility
- Curses-based terminal interface with proper initialization and cleanup
- Fully modular design with clean component separation
- Adaptive handling for TTY and non-TTY environments
- Secure memory operations with explicit cleanup

### Code Organization
- `main.py` - Entry point and argument handling
- `secure_word_interface.py` - Core interface coordination
- `input_handler.py` - Secure input processing and validation
- `display_handler.py` - UI rendering and masking
- `state_handler.py` - State management and security timeouts
- `ui_manager.py` - Terminal UI abstraction layer
- `secure_memory.py` - Secure memory handling functions
- `config.py` - Configuration settings and constants
- `tests/` - Comprehensive test suite
- `data/` - Default wordlists

## Security Philosophy
SeedShield implements a defense-in-depth approach:
- Multiple independent security layers
- Fail-secure design principles
- Memory-safe operations
- Input validation at all levels
- Automatic security timeout mechanisms
- No data persistence
- Secure error handling

## Legal Notice

### Disclaimer
SeedShield provides secure seed phrase verification capabilities but should be used as part of a comprehensive security strategy. Users are responsible for implementing appropriate system-level security measures. While SeedShield incorporates robust security features, it should not be relied upon as a sole security measure.

### License
Released under the MIT License. See the LICENSE file for complete terms.
