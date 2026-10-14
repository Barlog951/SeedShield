# Digest-pinned for reproducible builds; Dependabot (docker) bumps it weekly
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170

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
