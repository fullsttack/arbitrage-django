import asyncio
import json
import logging
import time
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
        self.is_receiving_data = False
        self.channel_layer = get_channel_layer()
        
        # Connection health tracking
        self.last_message_time = 0
        self.last_ping_time = 0
        self.last_data_time = 0
        self.connection_start_time = 0
        
        # Health check settings
        self.MESSAGE_TIMEOUT = 180  # No message for 3 minutes = dead connection
        self.DATA_TIMEOUT = 300     # No price data for 5 minutes = problem
        self.PING_TIMEOUT = 60      # Ping response timeout
        
        # Throttling for broadcasts
        self._last_broadcast_time = {}
        
    async def init_redis(self):
        """Initialize Redis connection"""
        if not redis_manager.is_connected:
            await redis_manager.connect()

    async def save_price_data(self, symbol: str, bid_price: Decimal, ask_price: Decimal, 
                             bid_volume: Decimal = Decimal('0'), ask_volume: Decimal = Decimal('0')):
        """Save price data and broadcast to WebSocket"""
        await self.init_redis()
        
        # Update data tracking
        self.last_data_time = time.time()
        self.is_receiving_data = True
        
        # Save to Redis
        await redis_manager.save_price_data(
            exchange=self.exchange_name,
            symbol=symbol,
            bid_price=float(bid_price),
            ask_price=float(ask_price),
            bid_volume=float(bid_volume),
            ask_volume=float(ask_volume)
        )
        
        # Throttled broadcast to prevent channel overflow
        if self.channel_layer:
            current_time = time.time()
            key = f"{self.exchange_name}_{symbol}"
            
            # Only broadcast if more than 5 seconds has passed since last broadcast for this symbol
            if current_time - self._last_broadcast_time.get(key, 0) > 5:
                price_data = {
                    'exchange': self.exchange_name,
                    'symbol': symbol,
                    'bid_price': float(bid_price),
                    'ask_price': float(ask_price),
                    'bid_volume': float(bid_volume),
                    'ask_volume': float(ask_volume),
                    'timestamp': time.time()
                }
                
                try:
                    await self.channel_layer.group_send(
                        'arbitrage_updates',
                        {
                            'type': 'send_price_update',
                            'price_data': price_data
                        }
                    )
                    self._last_broadcast_time[key] = current_time
                except Exception as e:
                    # Channel is full, skip this broadcast and throttle more aggressively
                    logger.debug(f"Skipped broadcast for {key}: {e}")
                    # Increase throttling when channel is full
                    self._last_broadcast_time[key] = current_time + 10  # Skip next 10 seconds
        
        logger.debug(f"Saved and broadcast {self.exchange_name} {symbol}: bid={bid_price}, ask={ask_price}")

    def update_message_time(self):
        """Update last message timestamp"""
        self.last_message_time = time.time()
    
    def update_ping_time(self):
        """Update last ping timestamp"""
        self.last_ping_time = time.time()

    def is_connection_healthy(self) -> bool:
        """Check if connection is healthy"""
        current_time = time.time()
        
        # Check if we're receiving any messages
        if self.last_message_time > 0:
            message_age = current_time - self.last_message_time
            if message_age > self.MESSAGE_TIMEOUT:
                logger.warning(f"{self.exchange_name}: No messages for {message_age:.1f}s - connection may be dead")
                return False
        
        # Check if we're receiving price data
        if self.last_data_time > 0:
            data_age = current_time - self.last_data_time
            if data_age > self.DATA_TIMEOUT:
                logger.warning(f"{self.exchange_name}: No price data for {data_age:.1f}s - may have subscription issues")
                return False
        
        return True

    def mark_connection_dead(self, reason: str = "Unknown"):
        """Mark connection as dead and log reason"""
        self.is_connected = False
        self.is_receiving_data = False
        logger.error(f"{self.exchange_name} connection marked as dead: {reason}")

    def reset_connection_state(self):
        """Reset all connection tracking"""
        current_time = time.time()
        self.connection_start_time = current_time
        self.last_message_time = current_time
        self.last_ping_time = current_time
        self.last_data_time = 0  # Will be set when first data arrives
        self.is_receiving_data = False

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
        self.mark_connection_dead("Manual disconnect")
        
    async def health_monitor(self):
        """Monitor connection health continuously"""
        while self.is_connected:
            try:
                if not self.is_connection_healthy():
                    self.mark_connection_dead("Health check failed")
                    break
                    
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"{self.exchange_name} health monitor error: {e}")
                break