#!/bin/bash

# Crypto Arbitrage Monitor - UV Project
# File: start.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# PID files
mkdir -p pids logs
DAPHNE_PID="pids/daphne.pid"
WORKER_PID="pids/workers.pid"

case "${1:-start}" in
    start)
        echo -e "${GREEN}🚀 Starting Arbitrage Monitor...${NC}"
        
        # Check if already running
        if [ -f "$DAPHNE_PID" ] && kill -0 $(cat "$DAPHNE_PID") 2>/dev/null; then
            echo -e "${YELLOW}Already running! Use 'stop' first.${NC}"
            exit 1
        fi
        
        # Start Redis if not running
        if ! pgrep -x "redis-server" > /dev/null; then
            echo -e "${BLUE}Starting Redis...${NC}"
            redis-server --daemonize yes
        fi
        
        # Install deps and migrate
        uv sync
        uv run python manage.py migrate
        
        # Start ASGI server
        echo -e "${GREEN}Starting ASGI Server...${NC}"
        uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application > logs/daphne.log 2>&1 &
        echo $! > "$DAPHNE_PID"
        
        sleep 2
        
        # Start workers
        echo -e "${GREEN}Starting Workers...${NC}"
        uv run python manage.py start_workers > logs/workers.log 2>&1 &
        echo $! > "$WORKER_PID"
        
        echo -e "${GREEN}✅ Started! Dashboard: ${BLUE}http://localhost:8000${NC}"
        ;;
        
    stop)
        echo -e "${YELLOW}🛑 Stopping services...${NC}"
        
        if [ -f "$DAPHNE_PID" ]; then
            kill $(cat "$DAPHNE_PID") 2>/dev/null
            rm -f "$DAPHNE_PID"
            echo -e "${BLUE}ASGI stopped${NC}"
        fi
        
        if [ -f "$WORKER_PID" ]; then
            kill $(cat "$WORKER_PID") 2>/dev/null
            rm -f "$WORKER_PID"
            echo -e "${BLUE}Workers stopped${NC}"
        fi
        
        # Kill any remaining processes
        pkill -f "daphne.*config.asgi" 2>/dev/null
        pkill -f "start_workers" 2>/dev/null
        
        echo -e "${GREEN}✅ Stopped${NC}"
        ;;
        
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
        
    status)
        echo -e "${BLUE}📊 Status:${NC}"
        
        if [ -f "$DAPHNE_PID" ] && kill -0 $(cat "$DAPHNE_PID") 2>/dev/null; then
            echo -e "${GREEN}✅ ASGI: Running (PID: $(cat $DAPHNE_PID))${NC}"
        else
            echo -e "${RED}❌ ASGI: Stopped${NC}"
        fi
        
        if [ -f "$WORKER_PID" ] && kill -0 $(cat "$WORKER_PID") 2>/dev/null; then
            echo -e "${GREEN}✅ Workers: Running (PID: $(cat $WORKER_PID))${NC}"
        else
            echo -e "${RED}❌ Workers: Stopped${NC}"
        fi
        
        if pgrep -x "redis-server" > /dev/null; then
            echo -e "${GREEN}✅ Redis: Running${NC}"
        else
            echo -e "${RED}❌ Redis: Stopped${NC}"
        fi
        ;;
        
    logs)
        echo -e "${BLUE}📋 Live logs (Ctrl+C to exit):${NC}"
        tail -f logs/*.log 2>/dev/null || echo "No logs yet"
        ;;
        
    install)
        echo -e "${BLUE}📦 Installing...${NC}"
        
        # Install UV if not exists
        if ! command -v uv &> /dev/null; then
            echo -e "${YELLOW}Installing UV...${NC}"
            curl -LsSf https://astral.sh/uv/install.sh | sh
            source $HOME/.cargo/env
        fi
        
        # Sync dependencies
        uv sync
        
        # Create .env if not exists
        if [ ! -f ".env" ]; then
            cp .env.example .env
            echo -e "${YELLOW}⚠️  Edit .env file!${NC}"
        fi
        
        # Install Redis
        if ! command -v redis-server &> /dev/null; then
            echo -e "${YELLOW}Install Redis manually:${NC}"
            echo -e "${BLUE}Ubuntu:${NC} sudo apt install redis-server"
            echo -e "${BLUE}macOS:${NC} brew install redis"
        fi
        
        echo -e "${GREEN}✅ Installation done!${NC}"
        ;;
        
    *)
        echo -e "${GREEN}Usage:${NC} $0 {start|stop|restart|status|logs|install}"
        ;;
esac