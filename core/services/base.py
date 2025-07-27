import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional, List
from channels.layers import get_channel_layer
from core.redis import redis_manager

logger = logging.getLogger(__name__)

class BaseExchangeService(ABC):
    """
    🚀 Simplified and Fast Base Exchange Service
    Focus: Speed, Simplicity, Efficiency
    """
    
    def __init__(self, exchange_name: str, config: Dict[str, Any]):
        self.exchange_name = exchange_name
        self.config = config
        self.websocket = None
        self.is_connected = False
        self.channel_layer = get_channel_layer()
        
        # Minimal tracking for performance
        self.last_message_time = 0
        self.last_data_time = 0
        self.message_count = 0
        
        # Simple broadcast throttle
        self._last_broadcast = {}
        
    async def init_redis(self):
        """Initialize Redis - called once"""
        if not redis_manager.is_connected:
            await redis_manager.connect()

    async def save_price_data(self, symbol: str, bid_price: Decimal, ask_price: Decimal, 
                             bid_volume: Decimal = Decimal('0'), ask_volume: Decimal = Decimal('0')):
        """💾 Fast price data save with minimal overhead"""
        current_time = time.time()
        self.last_data_time = current_time
        
        # Initialize Redis if needed
        await self.init_redis()
        
        # Save to Redis
        await redis_manager.save_price_data(
            exchange=self.exchange_name,
            symbol=symbol,
            bid_price=float(bid_price),
            ask_price=float(ask_price),
            bid_volume=float(bid_volume),
            ask_volume=float(ask_volume)
        )
        
        # Throttled broadcast (max once per 2 seconds per symbol)
        key = f"{symbol}"
        if current_time - self._last_broadcast.get(key, 0) > 2:
            try:
                await self.channel_layer.group_send('arbitrage_updates', {
                    'type': 'send_price_update',
                    'price_data': {
                        'exchange': self.exchange_name,
                        'symbol': symbol,
                        'bid_price': float(bid_price),
                        'ask_price': float(ask_price),
                        'bid_volume': float(bid_volume),
                        'ask_volume': float(ask_volume),
                        'timestamp': current_time
                    }
                })
                self._last_broadcast[key] = current_time
            except:
                pass  # Skip if channel full

    def update_message_time(self):
        """📡 Update message tracking"""
        self.last_message_time = time.time()
        self.message_count += 1

    def is_healthy(self) -> bool:
        """🔍 Simple health check"""
        if not self.is_connected:
            return False
        
        current_time = time.time()
        
        # Check message flow (30s timeout)
        if self.last_message_time > 0 and current_time - self.last_message_time > 30:
            return False
            
        return True

    def mark_dead(self, reason: str = ""):
        """💀 Mark connection as dead"""
        self.is_connected = False
        if reason:
            logger.warning(f"{self.exchange_name}: {reason}")

    async def connect_with_retries(self, max_retries: int = 3) -> bool:
        """🔄 Simple connection with retries"""
        for attempt in range(max_retries):
            try:
                if await self.connect():
                    return True
                await asyncio.sleep(2 ** attempt)  # exponential backoff
            except Exception as e:
                logger.error(f"{self.exchange_name} attempt {attempt + 1}: {e}")
        return False

    @abstractmethod
    async def connect(self) -> bool:
        """🔌 Connect to exchange"""
        pass

    @abstractmethod
    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to trading pairs"""
        pass

    @abstractmethod
    async def handle_message(self, message: str):
        """📨 Handle incoming message"""
        pass

    async def listen_loop(self):
        """👂 Simple message listening loop"""
        try:
            while self.is_connected and self.websocket:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                self.update_message_time()
                await self.handle_message(message)
        except Exception as e:
            self.mark_dead(f"Listen error: {e}")

    async def health_monitor(self):
        """💓 Simple health monitoring"""
        while self.is_connected:
            await asyncio.sleep(10)
            if not self.is_healthy():
                self.mark_dead("Health check failed")
                break

    async def disconnect(self):
        """🔌 Clean disconnect"""
        self.is_connected = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        self.websocket = None