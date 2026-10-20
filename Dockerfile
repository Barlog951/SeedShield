# Digest-pinned for reproducible builds; Dependabot (docker) bumps it weekly
FROM python:3.15-slim@sha256:2da676046630d7bf14c6764ae1143dc7fa0377a53f94bf5a642f0b214aca5bce

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Non-root user; the base image already ships the ncurses runtime and
# terminfo. No clipboard tooling: a container has no display to paste from.
RUN groupadd -r seedshield && \
    useradd -r -g seedshield seedshield

# Regular (non-editable) install; the source tree is discarded afterwards
COPY pyproject.toml README.md LICENSE MANIFEST.in /tmp/src/
COPY seedshield /tmp/src/seedshield/
RUN pip install --no-cache-dir /tmp/src && \
    rm -rf /tmp/src && \
    mkdir /app && chown seedshield:seedshield /app

WORKDIR /app
USER seedshield
ENTRYPOINT ["seedshield"]
