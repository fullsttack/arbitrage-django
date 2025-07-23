# Dockerfile for Django Arbitrage Application with uv
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy uv files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create staticfiles directory
RUN mkdir -p staticfiles

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Wait for PostgreSQL\n\
until uv run python -c "import psycopg2; psycopg2.connect(host='"'"'$DB_HOST'"'"', port='"'"'$DB_PORT'"'"', user='"'"'$DB_USER'"'"', password='"'"'$DB_PASSWORD'"'"', dbname='"'"'$DB_NAME'"'"')"; do\n\
  echo "Waiting for PostgreSQL..."\n\
  sleep 2\n\
done\n\
\n\
# Wait for Redis\n\
until uv run python -c "import redis; redis.Redis(host='"'"'$REDIS_HOST'"'"', port=$REDIS_PORT).ping()"; do\n\
  echo "Waiting for Redis..."\n\
  sleep 2\n\
done\n\
\n\
echo "Running migrations..."\n\
uv run python manage.py migrate\n\
\n\
echo "Seeding database..."\n\
uv run python manage.py seeder\n\
\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["uv", "run", "daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]