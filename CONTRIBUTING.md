# Contributing to AI Directory Cleaner

Thank you for your interest in contributing to AI Directory Cleaner! This document provides guidelines for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Development Setup

1. **Fork and Clone**:
```bash
git clone https://github.com/your-username/ai-disk-cleanup.git
cd ai-disk-cleanup
```

2. **Create Virtual Environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Development Dependencies**:
```bash
pip install -e ".[dev]"
```

4. **Install Pre-commit Hooks**:
```bash
pre-commit install
```

## 📋 Development Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Keep functions focused and small
- Use descriptive variable names

### Security Requirements

- **CRITICAL**: All security-related code must be reviewed
- Security tests must pass for all changes
- No file contents should ever be transmitted to APIs
- Path validation must be comprehensive
- All user inputs must be sanitized

### Testing

- Write tests for all new functionality
- Ensure all existing tests pass
- Target 90%+ test coverage for security-critical components
- Run security tests before submitting PRs

```bash
# Run all tests
pytest tests/

# Run security tests
pytest tests/unit/test_path_security.py tests/test_credential_store_security.py

# Run with coverage
pytest --cov=src --cov-report=html
```

## 🏗️ Project Structure

```
src/ai_disk_cleanup/
├── platforms/           # Cross-platform adapters
├── security/           # Security components
├── core/              # Core configuration and models
├── cache/             # Local caching system
├── interfaces/        # User interfaces (CLI, GUI)
└── ai_analyzer.py     # AI analysis engine
```

### Security Components

- `path_security.py` - Path validation and traversal protection
- `credential_store.py` - Secure credential storage
- `input_sanitizer.py` - Input validation and sanitization
- `secure_file_ops.py` - Secure file operations

## 🐛 Bug Reports

When filing bug reports:

1. Use the issue templates
2. Provide clear reproduction steps
3. Include system information (OS, Python version)
4. Add relevant logs and error messages
5. Security-related bugs should be marked as security-sensitive

## 💡 Feature Requests

Feature requests should:

1. Align with the project's privacy-first philosophy
2. Include use cases and expected benefits
3. Consider security implications
4. Maintain cross-platform compatibility

## 🔒 Security Contributions

Security-related contributions require:

1. Detailed explanation of the security issue
2. Comprehensive test coverage
3. Documentation of security trade-offs
4. Review by project maintainers

### Security Areas

- Path traversal protection
- Input validation and sanitization
- Cryptographic key management
- Secure file operations
- API response validation

## 📝 Documentation

- Update README.md for user-facing changes
- Update API docs for interface changes
- Document security considerations
- Include examples in docstrings

## 🚀 Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Commit** changes with clear messages
4. **Push** to your fork
5. **Create** a pull request

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass for all components
- [ ] Security tests pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)
- [ ] No sensitive information is committed

## 🧪 Testing Guidelines

### Unit Tests

- Test all public functions
- Include edge cases and error conditions
- Mock external dependencies
- Test security validations

### Integration Tests

- Test component interactions
- Test cross-platform functionality
- Test error handling scenarios
- Test security in context

### Security Tests

- Path traversal attempts
- Injection attack vectors
- Credential security
- File permission validation

## 🔍 Code Review

Reviewers should check:

- Security implications
- Performance impact
- Cross-platform compatibility
- Test coverage
- Documentation quality

## 📦 Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Tag the release
4. Create GitHub release
5. Update documentation

## 🤝 Community

- Be respectful and constructive
- Help newcomers get started
- Share knowledge and experiences
- Follow the code of conduct

## 📞 Getting Help

- Create an issue for questions
- Check existing documentation
- Join discussions in issues
- Review existing code for patterns

Thank you for contributing to AI Directory Cleaner! 🎉