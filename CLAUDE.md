# SeedShield Project Guidelines

## Build & Test Commands
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dev dependencies
pip install -e ".[test,dev]"

# Run all tests with coverage
pytest --cov=seedshield --cov-report term-missing --cov-report xml:coverage.xml --junitxml=junit.xml

# Run a single test
pytest tests/test_file.py::TestClass::test_function -v

# Linting
pylint seedshield
flake8 seedshield
mypy seedshield

# Build package
python -m build

# Docker build
docker build -t seedshield:latest .

# Release process
git tag v0.x.y  # Create new version tag
git push origin v0.x.y  # Push tag to trigger CI/CD
```

## Code Style Guidelines
- **Imports**: Standard library first, third-party second, local modules last
- **Type Annotations**: Use typing module (List, Optional, Tuple) for all functions
- **Naming**: snake_case for functions/variables, CamelCase for classes, UPPERCASE for constants
- **Documentation**: Docstrings for public interfaces, self-documenting code for internals
- **Error Handling**: Specific exceptions with proper cleanup in finally blocks
- **Line Length**: Max 100 characters
- **Indentation**: 4 spaces
- **Testing**: Extensive pytest coverage (>90%), mock external dependencies
- **Security Focus**: Proper handling of sensitive data (avoid logging/exposing seeds)
- **Code Complexity**: 
  - Maximum Cognitive Complexity of 15 per function
  - Keep methods small and focused on a single responsibility
  - Extract helper methods for complex logic
  - Use descriptive naming for extracted methods

## Project Architecture
- **Core Interface**: SecureWordInterface - Coordinates all components
- **Modular Components**:
  - **InputHandler**: Manages user input and position validation
  - **DisplayHandler**: Handles UI rendering and word masking/revealing
  - **StateHandler**: Manages application state and security timeouts
  - **UIManager**: Abstracts terminal UI operations for better testability
  - **SecureMemory**: Handles secure memory operations
- **User Interface**:
  - Clean, minimalist design with no distractions
  - Proper handling of terminal resizing
  - Detailed command menu with context-sensitive options
  - Improved error handling for user inputs
  - Proper screen transitions between modes
- **Security Features**: 
  - Auto-timeout mechanisms (halfdelay for TTY, timeout for non-TTY)
  - File logging is opt-in (--verbose only); no usage trail on disk by default
  - User-entered values and positions are never written to logs
  - Mask/reveal functionality with secure timers
  - Secure memory handling and clipboard management
  - Input validation and sanitization
- **Testing Framework**:
  - Global fixtures in conftest.py for all tests
  - Comprehensive mocking of curses functionality
  - Isolated test environment with pytest
  - 124 tests covering all components
  - 92% code coverage, exceeding 85% threshold
- **Cognitive Complexity**: Maintained ≤15 per component through clean architecture
- **CI/CD Pipeline**: GitHub Actions for automated testing, building and publishing
- **Docker Support**: Minimal secure image with optimized layers

## Current Project Status
- All tests are passing (124 tests)
- Code coverage at 92%, exceeding required threshold of 85%
- Pylint score: 10.00/10
- No type checking issues (mypy passes)
- No functions with complexity over 15
- UI improvements:
  - Clean interface with no text blocking the first line
  - Fixed 'n' key to properly return to input mode
  - Fixed initial screen to avoid premature error messages
  - Proper handling of empty input
- CI/CD pipeline configured with GitHub Actions
- Package building and PyPI publishing automated
- Test fixtures properly configured with pytest conftest.py
- TTY/non-TTY handling works correctly
- The application correctly finds wordlists in both default and custom locations
- Path handling is portable across different systems
- Security features are fully functional
- Running with pip install -e ".[test]" works correctly
- Code is regularly refactored to maintain complexity limits

## Static Analysis Tools
```bash
# Check complexity with pylint
pylint --disable=all --enable=R1702 seedshield/

# Check McCabe complexity (shows functions with complexity >= 15)
python -m mccabe --min 15 seedshield/display_handler.py seedshield/input_handler.py seedshield/secure_word_interface.py seedshield/main.py seedshield/state_handler.py seedshield/ui_manager.py seedshield/secure_memory.py seedshield/config.py

# Get full McCabe complexity report for a specific file
python -m mccabe seedshield/input_handler.py

# Run SonarQube checks (if configured)
# Alternatively, the following command can help find some SonarQube-type issues:
pylint seedshield/ --disable=all --enable=R0912,R0913,R0914,R0915,R1702,R1703,R1704,R1705,R1706,R1710,R1711,R1714,R1715,R1716,R1720,R1721,R1722,R1723,R1724

# Run mypy to check type annotations
mypy seedshield
```

## Cognitive Complexity Guidelines

Cognitive complexity is a measure of how difficult code is to understand. We strive to keep the cognitive complexity of all functions below 15 to maintain readability and testability.

### Refactoring Strategies to Reduce Complexity

When a function exceeds the cognitive complexity threshold, apply these refactoring techniques:

1. **Extract Helper Methods**: Split complex logic into smaller, focused helper methods
   - Extract conditional logic into separate methods with descriptive names
   - Create utility methods for repetitive tasks

2. **Simplify Control Flow**:
   - Reduce nested conditions by early returns or guard clauses
   - Consolidate similar conditional branches
   - Use polymorphism instead of complex type checking

3. **State Management**:
   - Extract complex state handling into dedicated methods or classes
   - Use state patterns for components with multiple states

4. **Error Handling**:
   - Centralize error handling in dedicated methods
   - Avoid deeply nested try/except blocks

### Examples

Poor (high complexity):
```python
def process_input(self, input_str):
    if not input_str:
        return None
    if input_str == 'q':
        return self.quit()
    elif input_str == 'v':
        clipboard = self.get_clipboard()
        if clipboard:
            try:
                numbers = self.parse_numbers(clipboard)
                if self.validate_numbers(numbers):
                    return numbers
                else:
                    self.show_error("Invalid numbers")
            except Exception as e:
                self.log_error(e)
                self.show_error("Error processing clipboard")
    else:
        try:
            num = int(input_str)
            if self.is_valid_range(num):
                return [num]
            else:
                self.show_error("Number out of range")
        except ValueError:
            self.show_error("Not a number")
    return None
```

Better (lower complexity):
```python
def process_input(self, input_str):
    if not input_str:
        return None
    
    if input_str == 'q':
        return self.quit()
    
    if input_str == 'v':
        return self._process_clipboard_input()
    
    return self._process_number_input(input_str)

def _process_clipboard_input(self):
    clipboard = self.get_clipboard()
    if not clipboard:
        return None
    
    try:
        numbers = self.parse_numbers(clipboard)
        if self.validate_numbers(numbers):
            return numbers
        self.show_error("Invalid numbers")
    except Exception as e:
        self._handle_clipboard_error(e)
    return None

def _process_number_input(self, input_str):
    try:
        num = int(input_str)
        if self.is_valid_range(num):
            return [num]
        self.show_error("Number out of range")
    except ValueError:
        self.show_error("Not a number")
    return None
```