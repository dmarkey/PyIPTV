# Contributing to PyIPTV

Thank you for your interest in contributing to PyIPTV! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Qt6 development libraries (for your platform)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/PyIPTV.git
   cd PyIPTV
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up pre-commit hooks**
   ```bash
   python scripts/dev.py pre-commit
   ```

5. **Run tests to verify setup**
   ```bash
   python scripts/dev.py test
   ```

## 🛠️ Development Workflow

### Using the Development Script

We provide a convenient development script to help with common tasks:

```bash
# Install dependencies
python scripts/dev.py install

# Format code
python scripts/dev.py format

# Run linting
python scripts/dev.py lint

# Type checking
python scripts/dev.py typecheck

# Run tests
python scripts/dev.py test
python scripts/dev.py test --coverage
python scripts/dev.py test --unit
python scripts/dev.py test --integration

# Run all checks
python scripts/dev.py check

# Build package
python scripts/dev.py build

# Clean build artifacts
python scripts/dev.py clean
```

### Code Style

We use several tools to maintain code quality:

- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **bandit** for security checks

Run `python scripts/dev.py format` before committing to ensure consistent formatting.

### Testing

We use pytest for testing with the following structure:

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for component interaction
└── conftest.py     # Shared test fixtures and configuration
```

#### Test Categories

- **Unit tests** (`@pytest.mark.unit`): Test individual functions/classes in isolation
- **Integration tests** (`@pytest.mark.integration`): Test component interactions
- **UI tests** (`@pytest.mark.ui`): Test UI components (require Qt)
- **Slow tests** (`@pytest.mark.slow`): Long-running tests

#### Writing Tests

1. **Unit tests** should be fast and test single functions/methods
2. **Use fixtures** from `conftest.py` for common test data
3. **Mock external dependencies** (Qt components, file system, network)
4. **Test edge cases** and error conditions
5. **Use descriptive test names** that explain what is being tested

Example test:

```python
def test_m3u_parser_handles_empty_file(mock_cache_manager):
    """Test that M3U parser handles empty files gracefully."""
    parser = M3UParser(cache_manager=mock_cache_manager)
    channels, categories = parser.parse_m3u_from_content([])
    
    assert len(channels) == 0
    assert len(categories) == 0
```

## 📝 Contribution Guidelines

### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code following our style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Run the full test suite**
   ```bash
   python scripts/dev.py check
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(parser): add support for EXTGRP tags
fix(ui): resolve memory leak in channel list
docs: update installation instructions
test: add unit tests for settings manager
```

### Code Review Guidelines

- **Be respectful** and constructive in reviews
- **Focus on the code**, not the person
- **Explain the "why"** behind suggestions
- **Test the changes** locally when possible
- **Approve** when the code meets our standards

## 🐛 Bug Reports

When reporting bugs, please include:

1. **PyIPTV version**
2. **Operating system and version**
3. **Python version**
4. **Steps to reproduce**
5. **Expected vs actual behavior**
6. **Error messages or logs**
7. **Sample M3U file** (if relevant)

Use our bug report template in GitHub Issues.

## 💡 Feature Requests

For feature requests, please:

1. **Check existing issues** to avoid duplicates
2. **Describe the use case** and problem you're solving
3. **Propose a solution** if you have one in mind
4. **Consider the scope** - is this a core feature or plugin?

## 🏗️ Architecture Guidelines

### Code Organization

- **Separate concerns**: UI, business logic, data access
- **Use dependency injection** for testability
- **Follow Qt patterns** for UI components
- **Keep modules focused** and cohesive

### Adding New Features

1. **Design first**: Consider the API and user experience
2. **Start with tests**: Write tests for the expected behavior
3. **Implement incrementally**: Small, focused commits
4. **Document**: Add docstrings and update user documentation

### Performance Considerations

- **Profile before optimizing**: Use actual data to identify bottlenecks
- **Consider memory usage**: Especially for large playlists
- **Use Qt's threading**: For long-running operations
- **Cache appropriately**: Balance memory vs computation

## 📚 Documentation

### Code Documentation

- **Use type hints** for all function parameters and return values
- **Write docstrings** for all public functions and classes
- **Follow Google style** for docstrings
- **Include examples** for complex functions

### User Documentation

- **Update README.md** for user-facing changes
- **Add to docs/** for detailed documentation
- **Include screenshots** for UI changes
- **Update CHANGELOG.md** for releases

## 🔒 Security

- **Never commit secrets** (API keys, passwords, etc.)
- **Validate user input** especially file paths and URLs
- **Use secure defaults** for network operations
- **Report security issues** privately to the maintainers

## 📄 License

By contributing to PyIPTV, you agree that your contributions will be licensed under the MIT License.

## 🤝 Community

- **Be welcoming** to newcomers
- **Help others** learn and contribute
- **Share knowledge** through documentation and examples
- **Respect different perspectives** and experiences

## 📞 Getting Help

- **GitHub Discussions** for questions and ideas
- **GitHub Issues** for bugs and feature requests
- **Email** the maintainers for private matters

Thank you for contributing to PyIPTV! 🎉
