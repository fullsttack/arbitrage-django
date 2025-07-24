# arbitrage-django

redis-cli FLUSHDB

uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application

uv run python manage.py start_workers


docker-compose exec web uv run python manage.py start_workers

# HTTP server (redirect to HTTPS)
server {
    listen 80;
    server_name pardak.ir www.pardak.ir;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name pardak.ir www.pardak.ir;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/pardak.ir/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pardak.ir/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    access_log /var/log/nginx/pardak.ir.access.log;
    error_log /var/log/nginx/pardak.ir.error.log;

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }

    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static/ {
        alias /var/www/arbitrage-django/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}