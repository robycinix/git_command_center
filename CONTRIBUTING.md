# Contributing

Thank you for helping make Git easier to understand and safer to use.

## Principles

- Keep the exact Git command visible to the user.
- Explain risk and recovery before destructive behavior.
- Prefer existing package boundaries and typed models.
- Keep provider integrations optional and explicit about transmitted data.
- Add focused tests for behavior changes.

## Local setup

```bash
git clone https://github.com/robycinix/git_command_center.git
cd git_command_center
python -m pip install -e ".[dev]"
```

Before opening a pull request, run:

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

Use a short branch name and keep each pull request focused. Describe the user
impact, the safety implications and the verification performed.

## Code style

The project targets Python 3.13, uses full typing and is formatted for a
100-character line length. Comments should explain non-obvious decisions rather
than narrating straightforward code.

## Reporting bugs

Include the operating system, Python version, Git version, repository state and
the smallest reproducible sequence. Remove credentials, private remote URLs and
sensitive diff content before posting logs.
