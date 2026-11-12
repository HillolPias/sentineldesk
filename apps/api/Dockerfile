FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# dependencies first: this layer is cached until pyproject/uv.lock change
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["sh", "start.sh"]