# Contributing to DocuMind AI Research Agent

We love your input! We want to make contributing to DocuMind AI as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests
1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

### Local Development Setup

1. **Clone your fork:**
   ```bash
   git clone https://github.com/your-username/DeepMu.git
   cd DeepMu
   ```

2. **Set up environment:**
   ```bash
   cd project
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start development services:**
   ```bash
   docker-compose up -d qdrant redis elasticsearch
   ```

4. **Run the application:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Coding Standards

### Python Code Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use meaningful variable and function names

### Code Formatting
```bash
# Install development dependencies
pip install black isort flake8 mypy

# Format code
black .
isort .

# Check linting
flake8 .

# Type checking
mypy .
```

### Documentation
- Use docstrings for all public functions and classes
- Update API documentation in `docs/API.md` for any API changes
- Add examples for new features

### Testing
- Write unit tests for all new functions
- Write integration tests for new endpoints
- Maintain test coverage above 90%
- Use meaningful test names that describe what is being tested

## Commit Messages

Use clear and meaningful commit messages:

```
feat: add hybrid search functionality
fix: resolve GPU memory leak in AI service
docs: update API documentation for search endpoints
test: add integration tests for document upload
refactor: optimize vector search performance
```

### Commit Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## Issue Reporting

### Bug Reports
Create an issue with:
- **Bug description:** Clear and concise description
- **Steps to reproduce:** Numbered steps to reproduce the behavior
- **Expected behavior:** What you expected to happen
- **Screenshots:** If applicable
- **Environment:** OS, Python version, GPU details, etc.

### Feature Requests
Create an issue with:
- **Feature description:** Clear description of the desired feature
- **Use case:** Why this feature would be useful
- **Proposed solution:** How you envision it working
- **Alternatives:** Alternative solutions you've considered

## Security Issues

If you discover a security vulnerability, please email us directly at security@deepmu.tech instead of creating a public issue.

## Code of Conduct

### Our Pledge
We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards
Examples of behavior that contributes to creating a positive environment include:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement
Project maintainers are responsible for clarifying the standards of acceptable behavior and are expected to take appropriate and fair corrective action in response to any instances of unacceptable behavior.

## Getting Help

- **Documentation:** Check the [docs/](docs/) folder
- **API Reference:** [docs/API.md](docs/API.md)
- **Deployment Guide:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Discord:** [Community Discord](https://discord.gg/documind) (coming soon)
- **Issues:** [GitHub Issues](https://github.com/Harigithub11/DeepMu/issues)

## Development Workflow

### Branch Naming
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- Documentation: `docs/description`
- Refactoring: `refactor/description`

### Testing Checklist
Before submitting a PR, ensure:
- [ ] All tests pass (`pytest tests/`)
- [ ] Code is formatted (`black . && isort .`)
- [ ] Linting passes (`flake8 .`)
- [ ] Type checking passes (`mypy .`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)

### Performance Guidelines
- Profile code changes that might affect performance
- GPU operations should be optimized for RTX 3060
- Database queries should be efficient
- API response times should remain under 2 seconds

### API Changes
For any API changes:
1. Update `docs/API.md`
2. Update OpenAPI documentation in the code
3. Add examples for new endpoints
4. Consider backward compatibility
5. Update version numbers if needed

## Release Process

### Versioning
We use [Semantic Versioning](https://semver.org/):
- MAJOR: Incompatible API changes
- MINOR: Backward-compatible functionality additions
- PATCH: Backward-compatible bug fixes

### Release Checklist
- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag release in Git

## Recognition

Contributors will be recognized in:
- README.md contributor section
- Release notes
- Project documentation
- Annual contributor appreciation

## Questions?

Don't hesitate to ask! Create an issue with the `question` label or reach out to the maintainers.

---

Thank you for contributing to DocuMind AI Research Agent! 🚀