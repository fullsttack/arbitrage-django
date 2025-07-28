# arbitrage-django

redis-cli FLUSHDB

uv run python manage.py seeder

uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application

uv run python manage.py start_workers

uv run python manage.py collectstatic --noinput

docker-compose exec web uv run python manage.py start_workers

docker-compose exec redis redis-cli FLUSHDB

