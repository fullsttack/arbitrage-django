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
        
        # Background tasks tracking
        self.background_tasks = []
        self._listen_task_running = False
        
        logger.info(f"{self.exchange_name}: Service initialized")

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
        logger.debug(f"{self.exchange_name}: Message #{self.message_count} received at {self.last_message_time}")

    def is_healthy(self) -> bool:
        """🔍 Simple health check"""
        if not self.is_connected:
            logger.debug(f"{self.exchange_name}: Health check - not connected")
            return False
        
        current_time = time.time()
        
        # Check message flow (45s timeout instead of 30s)
        if self.last_message_time > 0:
            time_since_last = current_time - self.last_message_time
            logger.debug(f"{self.exchange_name}: Health check - last message {time_since_last:.1f}s ago")
            
            if time_since_last > 45:  # Increased from 30 to 45
                logger.warning(f"{self.exchange_name}: Health check failed - no messages for {time_since_last:.1f}s")
                return False
        
        return True

    def mark_dead(self, reason: str = ""):
        """💀 Mark connection as dead"""
        logger.warning(f"{self.exchange_name}: Marking as dead - {reason}")
        self.is_connected = False
        if reason:
            logger.warning(f"{self.exchange_name}: {reason}")

    async def connect_with_retries(self, max_retries: int = 3) -> bool:
        """🔄 Simple connection with retries"""
        logger.info(f"{self.exchange_name}: Starting connection with retries (max: {max_retries})")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"{self.exchange_name}: Reconnect attempt {attempt + 1}")
                logger.debug(f"{self.exchange_name}: Subscribed pairs before connect: {getattr(self, 'subscribed_pairs', 'N/A')}")
                logger.debug(f"{self.exchange_name}: Background tasks before connect: {len(self.background_tasks)}")
                logger.debug(f"{self.exchange_name}: Listen task running: {self._listen_task_running}")
                
                if await self.connect():
                    logger.info(f"{self.exchange_name}: Connection successful")
                    return True
                    
                wait_time = 2 ** attempt
                logger.info(f"{self.exchange_name}: Attempt {attempt + 1} failed, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"{self.exchange_name} attempt {attempt + 1}: {e}")
        
        logger.error(f"{self.exchange_name}: All reconnect attempts failed")
        return False

    async def reset_state(self):
        """🔄 Reset internal state for reconnection"""
        logger.debug(f"{self.exchange_name}: Resetting state - before: tasks={len(self.background_tasks)}, listen_running={self._listen_task_running}")
        
        # Cancel existing background tasks FIRST
        await self.cancel_background_tasks()
        
        # Reset timing
        self.last_message_time = 0
        self.last_data_time = 0
        self.message_count = 0
        
        # Reset broadcast throttle
        self._last_broadcast.clear()
        
        # Reset connection state
        self.is_connected = False
        self.websocket = None
        self._listen_task_running = False
        
        logger.debug(f"{self.exchange_name}: State reset completed - after: tasks={len(self.background_tasks)}, listen_running={self._listen_task_running}")

    async def cancel_background_tasks(self):
        """🛑 Cancel all background tasks"""
        if not self.background_tasks:
            logger.debug(f"{self.exchange_name}: No background tasks to cancel")
            return
            
        logger.warning(f"{self.exchange_name}: Canceling {len(self.background_tasks)} background tasks")
        
        # Set listen task flag to false first
        self._listen_task_running = False
        
        canceled_count = 0
        for i, task in enumerate(self.background_tasks):
            if not task.done():
                try:
                    task.cancel()
                    canceled_count += 1
                    logger.debug(f"{self.exchange_name}: Canceled background task {i+1}")
                except Exception as e:
                    logger.warning(f"{self.exchange_name}: Error canceling task {i+1}: {e}")
        
        # Wait for tasks to complete with timeout
        if self.background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.background_tasks, return_exceptions=True),
                    timeout=5.0
                )
                logger.debug(f"{self.exchange_name}: All tasks completed gracefully")
            except asyncio.TimeoutError:
                logger.warning(f"{self.exchange_name}: Some tasks didn't complete within 5s")
        
        self.background_tasks.clear()
        logger.warning(f"{self.exchange_name}: Background tasks cleanup completed - canceled: {canceled_count}")

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
        """👂 Enhanced message listening loop with race condition protection"""
        # Prevent multiple listen loops
        if self._listen_task_running:
            logger.error(f"{self.exchange_name}: Listen loop already running! Aborting.")
            return
            
        self._listen_task_running = True
        logger.info(f"{self.exchange_name}: Starting listen loop")
        
        try:
            while self.is_connected and self.websocket and self._listen_task_running:
                try:
                    # Log every 10 seconds to see if we're still waiting for messages
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                    
                    # Log RAW message for debugging
                    logger.debug(f"{self.exchange_name}: RAW MESSAGE: {message[:200]}{'...' if len(message) > 200 else ''}")
                    
                    self.update_message_time()
                    await self.handle_message(message)
                    
                except asyncio.TimeoutError:
                    # Not an error, just no message received in 10s
                    current_time = time.time()
                    if self.last_message_time > 0:
                        silence_duration = current_time - self.last_message_time
                        logger.debug(f"{self.exchange_name}: No message for {silence_duration:.1f}s (timeout check)")
                    continue
                    
                except asyncio.CancelledError:
                    logger.info(f"{self.exchange_name}: Listen loop canceled")
                    break
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Listen error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"{self.exchange_name}: Listen loop error: {e}")
            
        finally:
            self._listen_task_running = False
            self.mark_dead("Listen loop terminated")
            logger.info(f"{self.exchange_name}: Listen loop ended")

    async def health_monitor(self):
        """💓 Simple health monitoring"""
        logger.debug(f"{self.exchange_name}: Starting health monitor")
        
        try:
            while self.is_connected and not asyncio.current_task().cancelled():
                await asyncio.sleep(10)
                if not self.is_healthy():
                    self.mark_dead("Health check failed")
                    break
        except asyncio.CancelledError:
            logger.debug(f"{self.exchange_name}: Health monitor canceled")
        except Exception as e:
            logger.error(f"{self.exchange_name}: Health monitor error: {e}")
                
        logger.debug(f"{self.exchange_name}: Health monitor ended")

    async def disconnect(self):
        """🔌 Clean disconnect"""
        logger.info(f"{self.exchange_name}: Starting disconnect")
        logger.debug(f"{self.exchange_name}: Current state - connected: {self.is_connected}, subscribed: {getattr(self, 'subscribed_pairs', 'N/A')}")
        
        # Mark as disconnected first to stop loops
        self.is_connected = False
        self._listen_task_running = False
        
        # Cancel background tasks first
        await self.cancel_background_tasks()
        
        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
                logger.debug(f"{self.exchange_name}: WebSocket closed")
            except Exception as e:
                logger.warning(f"{self.exchange_name}: Error closing websocket: {e}")
        
        # Reset state
        await self.reset_state()
        
        logger.info(f"{self.exchange_name}: Disconnect completed")