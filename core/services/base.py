import asyncio
import json
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional
import redis.asyncio as redis
from django.conf import settings
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class BaseExchangeService(ABC):
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.redis_client = None
        self.is_connected = False
        self.channel_layer = get_channel_layer()
        
    async def init_redis(self):
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )

    async def save_price_data(self, symbol: str, bid_price: Decimal, ask_price: Decimal, volume: Decimal = Decimal('0')):
        """Save price data and broadcast to WebSocket"""
        await self.init_redis()
        
        timestamp = asyncio.get_event_loop().time()
        
        price_data = {
            'exchange': self.exchange_name,
            'symbol': symbol,
            'bid_price': str(bid_price),
            'ask_price': str(ask_price),
            'volume': str(volume),
            'timestamp': timestamp
        }
        
        # Save to Redis
        key = f"prices:{self.exchange_name}:{symbol}"
        await self.redis_client.setex(key, 10, json.dumps(price_data))
        
        # Broadcast to WebSocket
        if self.channel_layer:
            await self.channel_layer.group_send(
                'price_updates',
                {
                    'type': 'send_price_update',
                    'price_data': {
                        'exchange': self.exchange_name,
                        'symbol': symbol,
                        'bid_price': float(bid_price),
                        'ask_price': float(ask_price),
                        'volume': float(volume),
                        'timestamp': timestamp
                    }
                }
            )

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def subscribe_to_pairs(self, pairs: list):
        pass

    @abstractmethod
    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass

    async def disconnect(self):
        self.is_connected = False
        if self.redis_client:
            await self.redis_client.close()