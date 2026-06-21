FROM python:3.13-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.13-slim

LABEL org.opencontainers.image.title="Git Command Center"
LABEL org.opencontainers.image.description="Visual, guided and safety-first Git TUI"
LABEL org.opencontainers.image.source="https://github.com/robycinix/git_command_center"
LABEL org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install --no-install-recommends --yes git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels \
    && git config --system --add safe.directory '*'

WORKDIR /workspace
ENTRYPOINT ["git-command-center"]
