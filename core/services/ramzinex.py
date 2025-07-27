import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

try:
    from centrifuge import Client, SubscriptionEventHandler, ClientEventHandler
    CENTRIFUGE_AVAILABLE = True
except ImportError:
    CENTRIFUGE_AVAILABLE = False
    logging.error("centrifuge-python not available, Ramzinex service disabled")

logger = logging.getLogger(__name__)

class RamzinexService(BaseExchangeService):
    def __init__(self):
        super().__init__('ramzinex')
        
        # Initialize attributes regardless of centrifuge availability
        self.websocket_url = 'wss://websocket.ramzinex.com/websocket'
        self.client = None
        self.subscribed_pairs = set()
        self.pair_symbol_map = {}  # Map pair IDs to symbol formats
        self.subscriptions = {}    # Store active subscriptions
        
        # ✅ FIXED: تنظیمات خاص Ramzinex طبق مستندات
        self.PING_INTERVAL = 25             # ✅ سرور هر 25 ثانیه ping میفرسته
        self.PING_TIMEOUT = 25              # ✅ باید در 25 ثانیه جواب بدیم
        self.MESSAGE_TIMEOUT = 35           # ✅ 35 ثانیه (25 + 10 safety margin)
        self.DATA_TIMEOUT = 120             # ✅ 2 دقیقه برای data
        self.MAX_SILENT_PERIOD = 40         # ✅ حداکثر 40 ثانیه سکوت (نه 2 دقیقه!)
        
        # Connection activity tracking
        self.last_activity_time = 0
        self.last_data_receive_time = 0
        self.connection_health_checks = 0
        
        if not CENTRIFUGE_AVAILABLE:
            logger.error("centrifuge-python not available - Ramzinex service disabled")
        
    async def _build_pair_symbol_mapping(self):
        """Build mapping between pair IDs and symbol formats from database"""
        try:
            from channels.db import database_sync_to_async
            from core.models import TradingPair
            
            @database_sync_to_async
            def get_ramzinex_pairs():
                return list(TradingPair.objects.filter(
                    exchange__name='ramzinex',
                    is_active=True
                ).values('pair_id', 'symbol_format'))
            
            pairs = await get_ramzinex_pairs()
            self.pair_symbol_map = {pair['pair_id']: pair['symbol_format'] for pair in pairs if pair['pair_id']}
            logger.info(f"Ramzinex built pair-symbol mapping: {self.pair_symbol_map}")
            
        except Exception as e:
            logger.error(f"Error building Ramzinex pair-symbol mapping: {e}")
        
    async def connect(self):
        """اتصال بهینه‌شده به Ramzinex"""
        if not CENTRIFUGE_AVAILABLE:
            logger.error("Ramzinex: centrifuge-python not available")
            return False
            
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"Ramzinex connection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.client:
                    try:
                        await self.client.disconnect()
                    except:
                        pass
                
                # ✅ Reset tracking variables
                self._reset_activity_tracking()
                
                # Create client with proper event handlers
                self.client = Client(
                    address=self.websocket_url,
                    events=self._create_client_event_handler()
                )
                
                # Connect to server
                await self.client.connect()
                
                self.is_connected = True
                self.reset_connection_state()
                self.last_activity_time = time.time()
                
                # Build pair-symbol mapping after connection
                await self._build_pair_symbol_mapping()
                
                # Start health monitoring - ✅ بهینه‌شده
                asyncio.create_task(self._optimized_health_monitor())
                
                logger.info("Ramzinex WebSocket connected successfully with Ramzinex-optimized settings (25s ping cycle)")
                return True
                
            except Exception as e:
                logger.error(f"Ramzinex connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(30, 2 ** attempt)
                    logger.info(f"Ramzinex retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.mark_connection_dead(f"Failed after {max_retries} attempts: {e}")
                    return False

    def _reset_activity_tracking(self):
        """Reset تمام activity tracking variables"""
        self.last_activity_time = 0
        self.last_data_receive_time = 0
        self.connection_health_checks = 0

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs using centrifuge client - PROPER API"""
        if not self.is_connected or not self.client:
            logger.error("Ramzinex: Cannot subscribe - not connected")
            return False
        
        # Wait a bit after connection before subscribing
        await asyncio.sleep(1)
        
        successful_subscriptions = 0
        
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    channel = f'orderbook:{pair_id}'
                    
                    # Create subscription with proper event handler
                    subscription = self.client.new_subscription(
                        channel=channel,
                        events=self._create_subscription_event_handler(pair_id)
                    )
                    
                    # Subscribe to channel
                    await subscription.subscribe()
                    
                    # Store subscription
                    self.subscriptions[pair_id] = subscription
                    
                    # ✅ Track activity
                    self.last_activity_time = time.time()
                    
                    logger.info(f"Ramzinex sent subscription for pair ID {pair_id} on channel {channel}")
                    
                    # Small delay between subscriptions
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Ramzinex subscription error for pair {pair_id}: {e}")
        
        # Wait for subscription confirmations
        await asyncio.sleep(3)
        
        # Count actually confirmed subscriptions
        successful_subscriptions = len(self.subscribed_pairs)
        logger.info(f"Ramzinex: Successfully subscribed to {successful_subscriptions}/{len(pairs)} pairs")
        return successful_subscriptions > 0

    def _create_client_event_handler(self):
        """Create client event handler for connection lifecycle"""
        class RamzinexClientHandler(ClientEventHandler):
            def __init__(self, service):
                super().__init__()
                self.service = service
            
            async def on_connecting(self, ctx):
                logger.debug("Ramzinex: Connecting to WebSocket...")
                self.service.last_activity_time = time.time()
            
            async def on_connected(self, ctx):
                logger.info("Ramzinex: Connected to WebSocket")
                self.service.last_activity_time = time.time()
                self.service.update_message_time()
            
            async def on_disconnected(self, ctx):
                logger.warning(f"Ramzinex: Disconnected - {ctx}")
                self.service.mark_connection_dead(f"Disconnected: {ctx}")
            
            async def on_error(self, ctx):
                logger.error(f"Ramzinex: Client error - {ctx}")
        
        return RamzinexClientHandler(self)
    
    def _create_subscription_event_handler(self, pair_id: str):
        """Create subscription event handler for a specific pair"""
        class RamzinexSubscriptionHandler(SubscriptionEventHandler):
            def __init__(self, pair_id, service):
                super().__init__()
                self.pair_id = pair_id
                self.service = service
            
            async def on_subscribing(self, ctx):
                logger.debug(f"Ramzinex: Subscribing to {self.pair_id}")
                self.service.last_activity_time = time.time()
            
            async def on_subscribed(self, ctx):
                logger.debug(f"Ramzinex: Successfully subscribed to {self.pair_id}")
                self.service.subscribed_pairs.add(self.pair_id)
                self.service.update_message_time()
                self.service.last_activity_time = time.time()
            
            async def on_unsubscribed(self, ctx):
                logger.debug(f"Ramzinex: Unsubscribed from {self.pair_id}")
                if self.pair_id in self.service.subscribed_pairs:
                    self.service.subscribed_pairs.remove(self.pair_id)
            
            async def on_error(self, ctx):
                logger.error(f"Ramzinex: Subscription error for {self.pair_id} - {ctx}")
            
            async def on_publication(self, ctx):
                # Handle published data
                await self.service._on_publication_async(ctx, self.pair_id)
        
        return RamzinexSubscriptionHandler(pair_id, self)
    
    async def _on_publication_async(self, ctx, pair_id: str):
        """Handle published data from Ramzinex"""
        try:
            current_time = time.time()
            self.update_message_time()
            self.last_activity_time = current_time
            self.last_data_receive_time = current_time
            
            # Get data from context - centrifuge provides ctx.pub.data
            if hasattr(ctx, 'pub') and hasattr(ctx.pub, 'data'):
                orderbook_data = ctx.pub.data
            elif hasattr(ctx, 'data'):
                orderbook_data = ctx.data
            else:
                logger.warning(f"Ramzinex: No data in publication context for {pair_id}: {ctx}")
                return
            
            # Data should already be a dict from centrifuge
            if isinstance(orderbook_data, dict):
                # Process the orderbook data directly
                await self._process_orderbook_data(pair_id, orderbook_data)
            elif isinstance(orderbook_data, (str, bytes)):
                # Fallback: parse JSON if it's a string
                if isinstance(orderbook_data, bytes):
                    orderbook_data = orderbook_data.decode('utf-8')
                
                try:
                    parsed_data = json.loads(orderbook_data)
                    await self._process_orderbook_data(pair_id, parsed_data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Ramzinex: Invalid JSON in published data for {pair_id}: {e}")
                    return
            else:
                logger.warning(f"Ramzinex: Unexpected data format for {pair_id}: {type(orderbook_data)}")
                return
            
        except Exception as e:
            logger.error(f"Ramzinex publish event processing error for {pair_id}: {e}")

    async def _process_orderbook_data(self, pair_id: str, orderbook_data: Dict[str, Any]):
        """Process orderbook data from Ramzinex with new complex format"""
        try:
            # Track data processing
            self.last_data_receive_time = time.time()
            self.last_activity_time = time.time()
            
            # Get buys and sells arrays
            buys = orderbook_data.get('buys', [])
            sells = orderbook_data.get('sells', [])
            
            logger.debug(f"Ramzinex pair {pair_id}: buys={len(buys)}, sells={len(sells)}")
            
            if buys and sells:
                # Format: [price, volume, total_value, boolean, null, count, timestamp]
                # Best bid (highest buy price) - first in buys array (sorted descending)
                if isinstance(buys[0], list) and len(buys[0]) >= 2:
                    bid_price = Decimal(str(buys[0][0]))    # First element is price
                    bid_volume = Decimal(str(buys[0][1]))   # Second element is volume
                else:
                    logger.warning(f"Ramzinex invalid buys format for pair {pair_id}: {buys[0] if buys else 'None'}")
                    return
                
                # Best ask (lowest sell price) - LAST in sells array (طبق مستندات ramzinex)
                if isinstance(sells[-1], list) and len(sells[-1]) >= 2:
                    ask_price = Decimal(str(sells[-1][0]))   # First element is price  
                    ask_volume = Decimal(str(sells[-1][1]))  # Second element is volume
                else:
                    logger.warning(f"Ramzinex invalid sells format for pair {pair_id}: {sells[-1] if sells else 'None'}")
                    return
                
                # Get symbol format from mapping, fallback to pair_id if not found
                symbol_format = self.pair_symbol_map.get(pair_id, pair_id)
                
                # Save price data
                await self.save_price_data(symbol_format, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"Ramzinex {symbol_format} (pair_id: {pair_id}): bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            else:
                logger.warning(f"Ramzinex pair {pair_id}: No buys or sells data")
            
        except Exception as e:
            logger.error(f"Ramzinex orderbook data processing error for pair {pair_id}: {e}")

    async def _optimized_health_monitor(self):
        """✅ FIXED: Health monitor بهینه‌شده برای Ramzinex (25s ping cycle)"""
        while self.is_connected:
            try:
                # ✅ Health check هوشمند
                if not await self._intelligent_health_check():
                    logger.warning("Ramzinex: Health check failed")
                    self.mark_connection_dead("Health check failed")
                    break
                
                # ✅ چک هر 5 ثانیه (برای 25s ping cycle)
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Ramzinex health monitor error: {e}")
                self.mark_connection_dead(f"Health monitor error: {e}")
                break

    async def _intelligent_health_check(self) -> bool:
        """✅ FIXED: Health check طبق مستندات Ramzinex (25s ping/pong)"""
        current_time = time.time()
        
        # 1. ✅ بررسی activity - خیلی مهم برای Ramzinex (25s ping rule)
        if self.last_activity_time > 0:
            time_since_activity = current_time - self.last_activity_time
            
            # اگر بیش از 40 ثانیه سکوت = مشکل (25s ping + 15s margin)
            if time_since_activity > self.MAX_SILENT_PERIOD:  # 40 ثانیه
                logger.warning(f"Ramzinex: No activity for {time_since_activity:.1f}s (ping timeout likely) - connection will be reset")
                return False
        
        # 2. ✅ بررسی message reception - سخت‌گیرانه برای Ramzinex
        if self.last_message_time > 0:
            time_since_message = current_time - self.last_message_time
            
            # Ramzinex has 25s ping cycle, so be strict about messages
            if time_since_message > self.MESSAGE_TIMEOUT:  # 35 ثانیه
                logger.warning(f"Ramzinex: No messages for {time_since_message:.1f}s (expected ping every 25s) - connection will be reset")
                return False
        
        # 3. ✅ بررسی data reception - متعادل
        if self.last_data_receive_time > 0:
            time_since_data = current_time - self.last_data_receive_time
            
            # برای data کمی بیشتر تحمل (بازارهای آرام)
            if time_since_data > self.DATA_TIMEOUT:  # 2 دقیقه
                logger.info(f"Ramzinex: No data for {time_since_data:.1f}s (quiet market)")
                
                # فقط بعد از سکوت خیلی طولانی disconnect
                if time_since_data > 600:  # 10 دقیقه
                    logger.warning(f"Ramzinex: Extended quiet period - {time_since_data:.1f}s without data")
                    return False
        
        return True

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_orderbook_data)"""
        return None

    def reset_connection_state(self):
        """Reset connection state"""
        super().reset_connection_state()
        self._reset_activity_tracking()

    async def disconnect(self):
        """Disconnect from Ramzinex"""
        await super().disconnect()
        
        # Unsubscribe from all channels
        for pair_id, subscription in self.subscriptions.items():
            try:
                await subscription.unsubscribe()
            except Exception as e:
                logger.warning(f"Error unsubscribing from {pair_id}: {e}")
        
        # Close centrifuge client
        if self.client:
            try:
                await self.client.disconnect()
            except:
                pass
        
        self.client = None
        self.subscribed_pairs.clear()
        self.subscriptions.clear()
        self.pair_symbol_map.clear()
        self._reset_activity_tracking()
        logger.info("Ramzinex centrifuge client disconnected")