import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

try:
    from centrifuge import Client
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
                
                # Create centrifuge client
                self.client = Client(
                    address=self.websocket_url,
                    name="python-arbitrage"
                )
                
                # Set up event handlers
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.on_error = self._on_error
                
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
        """Subscribe to trading pairs using centrifuge client"""
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
                    
                    # ✅ FIXED: Subscribe using centrifuge client with delta compression
                    subscription = self.client.new_subscription(channel, {
                        'recover': True,
                        'delta': 'fossil'  # ✅ طبق مستندات Ramzinex
                    })
                    
                    # Set up event handlers - must be async functions
                    def make_publication_handler(pair_id):
                        async def handler(ctx):
                            await self._on_publication(ctx, pair_id)
                        return handler
                    
                    subscription.events.on_publication = make_publication_handler(pair_id)
                    
                    # Subscribe
                    await subscription.subscribe()
                    
                    # Mark as subscribed after successful subscription
                    self.subscribed_pairs.add(pair_id)
                    
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

    # ✅ FIXED: Event handlers برای centrifuge client
    async def _on_connect(self, event):
        """Handle connection success"""
        logger.info(f"Ramzinex connected: {event}")
        self.update_message_time()
        self.last_activity_time = time.time()
    
    async def _on_disconnect(self, event):
        """Handle disconnection"""
        logger.warning(f"Ramzinex disconnected: {event}")
        self.mark_connection_dead(f"Client disconnected: {event}")
    
    async def _on_error(self, event):
        """Handle connection errors"""
        logger.error(f"Ramzinex connection error: {event}")
        self.mark_connection_dead(f"Connection error: {event}")
    
    async def _on_subscribed(self, ctx, pair_id: str):
        """Handle successful subscription"""
        logger.info(f"Ramzinex subscription successful for pair {pair_id}")
        self.subscribed_pairs.add(pair_id)
        self.update_message_time()
        self.last_activity_time = time.time()
    
    async def _on_subscription_error(self, ctx, pair_id: str):
        """Handle subscription error"""
        logger.error(f"Ramzinex subscription error for pair {pair_id}: {ctx}")
    
    async def _on_publication(self, ctx, pair_id: str):
        """✅ FIXED: Handle published data with activity tracking"""
        try:
            current_time = time.time()
            self.update_message_time()
            self.last_activity_time = current_time      # ✅ Track activity
            self.last_data_receive_time = current_time  # ✅ Track data reception
            
            # The centrifuge client automatically handles delta decompression
            # ctx.pub.data contains the decompressed data
            if hasattr(ctx, 'pub') and hasattr(ctx.pub, 'data'):
                data = ctx.pub.data
            else:
                logger.warning(f"Ramzinex: No data in publication context for {pair_id}: {ctx}")
                return
            
            if isinstance(data, (str, bytes)):
                # Parse JSON if it's a string
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                
                try:
                    orderbook_data = json.loads(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Ramzinex: Invalid JSON in published data for {pair_id}: {e}")
                    return
            elif isinstance(data, dict):
                # Already parsed
                orderbook_data = data
            else:
                logger.debug(f"Ramzinex: Unknown data format for {pair_id}: {type(data)}")
                return
            
            # Process the orderbook data
            await self._process_orderbook_data(pair_id, orderbook_data)
            
        except Exception as e:
            logger.error(f"Ramzinex publish event processing error for {pair_id}: {e}")

    async def _process_orderbook_data(self, pair_id: str, orderbook_data: Dict[str, Any]):
        """Process orderbook data from Ramzinex"""
        try:
            # ✅ Track data processing
            self.last_data_receive_time = time.time()
            self.last_activity_time = time.time()
            
            # Get buys and sells
            buys = orderbook_data.get('buys', [])
            sells = orderbook_data.get('sells', [])
            
            logger.debug(f"Ramzinex pair {pair_id}: buys={len(buys)}, sells={len(sells)}")
            
            if buys and sells:
                # ✅ CORRECT: طبق مستندات و API response Ramzinex
                # Buys: highest price first (descending order) → Best bid = buys[0]
                # Sells: highest price first (descending order) → Best ask = sells[-1] (cheapest)
                
                # Best bid (highest buy price) - first in buys
                if isinstance(buys[0], list) and len(buys[0]) >= 2:
                    bid_price = Decimal(str(buys[0][0]))
                    bid_volume = Decimal(str(buys[0][1]))
                else:
                    logger.warning(f"Ramzinex invalid buys format for pair {pair_id}: {buys[0] if buys else 'None'}")
                    return
                
                # ✅ CORRECT: Best ask (lowest sell price) - LAST in sells (cheapest!)
                if isinstance(sells[-1], list) and len(sells[-1]) >= 2:
                    ask_price = Decimal(str(sells[-1][0]))
                    ask_volume = Decimal(str(sells[-1][1]))
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
                logger.warning(f"Ramzinex: No activity for {time_since_activity:.1f}s (ping timeout likely)")
                return False
        
        # 2. ✅ بررسی message reception - سخت‌گیرانه برای Ramzinex
        if self.last_message_time > 0:
            time_since_message = current_time - self.last_message_time
            
            # Ramzinex has 25s ping cycle, so be strict about messages
            if time_since_message > self.MESSAGE_TIMEOUT:  # 35 ثانیه
                logger.warning(f"Ramzinex: No messages for {time_since_message:.1f}s (expected ping every 25s)")
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