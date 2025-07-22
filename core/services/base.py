import asyncio
import json
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional
from channels.layers import get_channel_layer
from core.redis_manager import redis_manager

logger = logging.getLogger(__name__)

class BaseExchangeService(ABC):
    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.is_connected = False
        self.channel_layer = get_channel_layer()
        
    async def init_redis(self):
        """Initialize Redis connection"""
        if not redis_manager.is_connected:
            await redis_manager.connect()

    async def save_price_data(self, symbol: str, bid_price: Decimal, ask_price: Decimal, 
                             bid_volume: Decimal = Decimal('0'), ask_volume: Decimal = Decimal('0')):
        """Save price data and broadcast to WebSocket"""
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
        
        # Skip WebSocket broadcast for individual prices to reduce channel load
        # Prices will be available through arbitrage opportunities
        logger.debug(f"Saved {self.exchange_name} {symbol}: bid={bid_price}, ask={ask_price}")

    @abstractmethod
    async def connect(self):
        """Connect to exchange service"""
        pass

    @abstractmethod
    async def subscribe_to_pairs(self, pairs: list):
        """Subscribe to trading pairs"""
        pass

    @abstractmethod
    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data from exchange"""
        pass

    async def disconnect(self):
        """Disconnect from exchange service"""
        self.is_connected = False