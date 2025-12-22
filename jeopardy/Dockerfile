# Dockerfile for Fly.io deployment
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create volume mount point for persistent data
RUN mkdir -p /data/uploads

# Expose port
EXPOSE 8080

# Run the application
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:create_app()"]
