# Security Policy

## Supported versions

Git Command Center is currently in alpha. Security fixes are applied to the
latest release and the `main` branch.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities that could expose credentials,
execute unintended commands or destroy repository data. Use GitHub's private
security advisory reporting for this repository.

Include:

- affected version and platform;
- a minimal reproduction;
- expected and observed behavior;
- potential impact;
- any suggested mitigation.

Never include live tokens, private repository contents or personal information.

## Security boundaries

GCC does not evaluate arbitrary shell strings. Git commands are represented as
argument lists and validated before execution. Provider integrations are
disabled by default and must remain opt-in.
