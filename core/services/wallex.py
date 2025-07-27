import asyncio
import json
import logging
import random
import websockets
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

logger = logging.getLogger(__name__)

class WallexService(BaseExchangeService):
    def __init__(self):
        super().__init__('wallex')
        self.websocket_url = 'wss://api.wallex.ir/ws'
        self.websocket = None
        self.subscribed_pairs = set()
        self.partial_data = {}  # Store partial orderbook data
        self.pending_subscriptions = {}  # Track pending subscriptions
        self.connection_start_time = 0  # Track connection time for 30min limit
        self.message_count_per_channel = {}  # Track message count per channel
        self.pong_count = 0  # Track PONG responses (100 max)
        self.last_server_ping_time = 0  # Track last server ping
        
        # ✅ FIXED: تنظیمات طبق مستندات Wallex
        self.SERVER_PING_INTERVAL = 20      # ✅ سرور هر 20 ثانیه ping میفرسته
        self.MESSAGE_TIMEOUT = 30           # ✅ 30 ثانیه (20s + 10s margin)
        self.DATA_TIMEOUT = 180             # ✅ 3 دقیقه برای data
        self.MAX_SILENT_PERIOD = 40         # ✅ حداکثر 40 ثانیه سکوت
        self.CONNECTION_LIMIT = 1500        # ✅ 25 دقیقه (proactive قبل از 30 min)
        self.MAX_PONG_COUNT = 95            # ✅ کمی قبل از 100
        
        # Enhanced connection management
        self.last_data_receive_time = 0
        self.last_activity_time = 0
        self.connection_restart_count = 0
        self.MAX_RESTARTS_PER_HOUR = 10  # محدودیت restart
        self.restart_times = []  # Track restart times
        
        # Subscription confirmation tracking  
        self.confirmed_subscriptions = set()
        self.subscription_timeout = 30  # Wait 30s for subscription confirmation

    async def connect(self):
        """اتصال بهینه‌شده طبق مستندات Wallex"""
        # Clean old restart times (older than 1 hour)
        current_time = time.time()
        self.restart_times = [t for t in self.restart_times if current_time - t < 3600]
        
        # Check restart rate limit
        if len(self.restart_times) >= self.MAX_RESTARTS_PER_HOUR:
            wait_time = 3600 - (current_time - self.restart_times[0])
            logger.warning(f"Wallex: Too many restarts ({len(self.restart_times)}/hour), waiting {wait_time:.0f}s")
            await asyncio.sleep(min(300, wait_time))  # Max 5 minute wait
            return False
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"Wallex connection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # ✅ Reset all tracking
                self._reset_connection_tracking()
                
                # Add random delay to avoid IP rate limiting
                if attempt > 0:
                    delay = random.uniform(2, 8)  # 2-8 seconds
                    logger.info(f"Wallex: Adding random delay {delay:.1f}s to avoid IP throttling")
                    await asyncio.sleep(delay)
                
                # Enhanced connection parameters
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Manual ping handling
                    ping_timeout=None,   
                    close_timeout=10,
                    max_size=2**20,      
                    max_queue=16,        # Smaller queue to prevent memory issues
                    compression=None     # Disable compression for simplicity
                )
                
                self.is_connected = True
                self.reset_connection_state()
                self.connection_start_time = time.time()
                self.last_activity_time = time.time()
                self.restart_times.append(current_time)
                self.connection_restart_count += 1
                
                # Start monitoring tasks
                asyncio.create_task(self.health_monitor())
                asyncio.create_task(self._listen_messages())
                asyncio.create_task(self._wallex_optimized_health_checker())
                
                logger.info(f"Wallex WebSocket connected successfully with Wallex-optimized settings (restart #{self.connection_restart_count})")
                return True
                
            except Exception as e:
                logger.error(f"Wallex connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = min(60, (2 ** attempt) + random.uniform(0, 5))
                    logger.info(f"Wallex retrying in {wait_time:.1f} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.mark_connection_dead(f"Failed after {max_retries} attempts: {e}")
                    return False

    def _reset_connection_tracking(self):
        """Reset تمام tracking variables"""
        self.pong_count = 0
        self.message_count_per_channel.clear()
        self.last_server_ping_time = 0
        self.last_data_receive_time = 0
        self.last_activity_time = 0
        self.confirmed_subscriptions.clear()

    async def subscribe_to_pairs(self, pairs: List[str]):
        """اشتراک بهینه‌شده طبق مستندات Wallex"""
        if not self.is_connected or not self.websocket:
            logger.error("Wallex: Cannot subscribe - not connected")
            return False
        
        logger.info(f"Wallex: Starting subscription to {len(pairs)} pairs: {pairs}")
        
        # Subscribe to individual pairs - طبق مستندات Wallex
        success_count = await self._subscribe_individual_pairs(pairs)
        
        # Wait for confirmations
        logger.info("Wallex: Waiting for subscription confirmations...")
        await asyncio.sleep(10)  # اندکی بیشتر منتظر بمون
        
        # Check actual confirmations
        confirmed_count = len(self.confirmed_subscriptions)
        logger.info(f"Wallex: {confirmed_count}/{len(pairs)} subscriptions confirmed")
        
        if confirmed_count > 0:
            logger.info(f"Wallex: Successfully subscribed to {confirmed_count}/{len(pairs)} individual pairs")
            return True
        else:
            logger.error("Wallex: No individual subscriptions confirmed")
            return False

    async def _subscribe_individual_pairs(self, pairs: List[str]) -> int:
        """Subscribe طبق مستندات Wallex - buyDepth و sellDepth"""
        successful_subscriptions = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Delay between subscriptions to avoid rate limiting
                    if successful_subscriptions > 0:
                        await asyncio.sleep(1)  # 1 second between subscriptions
                    
                    # ✅ طبق مستندات Wallex: ["subscribe", {"channel": "SYMBOL@buyDepth"}]
                    
                    # Subscribe to buy depth
                    buy_subscribe_msg = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    logger.debug(f"Wallex subscribing to {symbol}@buyDepth...")
                    await self.websocket.send(json.dumps(buy_subscribe_msg))
                    self.last_activity_time = time.time()
                    
                    # Small delay between subscriptions
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to sell depth
                    sell_subscribe_msg = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    logger.debug(f"Wallex subscribing to {symbol}@sellDepth...")
                    await self.websocket.send(json.dumps(sell_subscribe_msg))
                    self.last_activity_time = time.time()
                    
                    # Track pending subscription
                    self.pending_subscriptions[symbol] = time.time()
                    
                    # Initialize message counters for both channels
                    self.message_count_per_channel[f"{symbol}@buyDepth"] = 0
                    self.message_count_per_channel[f"{symbol}@sellDepth"] = 0
                    
                    successful_subscriptions += 1
                    
                except Exception as e:
                    logger.error(f"Wallex subscription error for {symbol}: {e}")
        
        return successful_subscriptions

    async def _listen_messages(self):
        """✅ FIXED: Message listener طبق تنظیمات Wallex"""
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.is_connected and self.websocket:
            try:
                # ✅ FIXED: timeout مناسب برای Wallex (20s server ping)
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=self.MESSAGE_TIMEOUT  # 30 ثانیه
                )
                
                consecutive_errors = 0
                current_time = time.time()
                self.update_message_time()
                self.last_data_receive_time = current_time
                self.last_activity_time = current_time
                
                # Parse message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Wallex: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                # ✅ FIXED: مدیریت timeout بهتر
                current_time = time.time()
                time_since_activity = current_time - self.last_activity_time
                
                logger.warning(f"Wallex: Message timeout ({self.MESSAGE_TIMEOUT}s), "
                             f"last activity: {time_since_activity:.1f}s ago")
                
                # فقط در صورت سکوت طولانی disconnect
                if time_since_activity > self.MAX_SILENT_PERIOD:
                    logger.error(f"Wallex: Extended silence ({time_since_activity:.1f}s) - disconnecting")
                    self.mark_connection_dead(f"Extended silence: {time_since_activity:.1f}s")
                    break
                else:
                    logger.info("Wallex: Timeout but acceptable - server may be busy")
                    continue
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Wallex WebSocket connection closed: {e}")
                self.mark_connection_dead(f"Connection closed: {e}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Wallex message error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Wallex: Too many consecutive errors")
                    self.mark_connection_dead(f"Too many errors: {e}")
                    break
                
                await asyncio.sleep(1)

    async def _process_message(self, data):
        """پردازش پیام‌های Wallex"""
        try:
            current_time = time.time()
            self.last_activity_time = current_time
            
            # ✅ Handle server PING - طبق مستندات Wallex
            if isinstance(data, dict) and 'ping' in data:
                await self._handle_server_ping(data)
                return
            
            # Handle subscription confirmations
            if isinstance(data, dict) and ('result' in data or 'success' in data):
                logger.info(f"Wallex subscription response: {data}")
                return
                
            # Handle errors
            if isinstance(data, dict) and 'error' in data:
                logger.warning(f"Wallex error: {data}")
                return
            
            # ✅ Process depth data - format: [channel_name, data_array]
            if isinstance(data, list) and len(data) == 2:
                channel_name = data[0]
                
                # Handle buyDepth and sellDepth channels
                if '@buyDepth' in channel_name or '@sellDepth' in channel_name:
                    await self._process_depth_data(data)
                # Handle other channel types
                else:
                    logger.debug(f"Wallex: Unknown channel type: {channel_name}")
            
            else:
                logger.debug(f"Wallex unhandled message format: {str(data)[:200]}...")
                
        except Exception as e:
            logger.error(f"Wallex message processing error: {e}")

    async def _handle_server_ping(self, data: Dict[str, Any]):
        """✅ FIXED: مدیریت server ping طبق مستندات Wallex"""
        try:
            ping_id = data.get('ping')
            if ping_id:
                current_time = time.time()
                
                # ✅ چک محدودیت PONG (100 max)
                if self.pong_count >= self.MAX_PONG_COUNT:
                    logger.warning(f"Wallex: PONG limit approaching ({self.pong_count}/100) - will reconnect proactively")
                    self.mark_connection_dead("PONG limit approaching")
                    return
                
                # ✅ Send PONG response
                pong_msg = {"pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                
                self.pong_count += 1
                self.last_server_ping_time = current_time
                self.last_activity_time = current_time
                self.update_ping_time()
                
                logger.debug(f"Wallex: PONG sent for ping {ping_id} ({self.pong_count}/100)")
                
        except Exception as e:
            logger.error(f"Wallex PING handling error: {e}")
            self.mark_connection_dead(f"PING handling failed: {e}")

    async def _process_depth_data(self, data: list):
        """Process buyDepth and sellDepth data"""
        try:
            channel_name = data[0]  # e.g., "DOGEUSDT@buyDepth"
            orders_data = data[1]   # Array of order objects
            
            current_time = time.time()
            self.last_data_receive_time = current_time
            self.last_activity_time = current_time
            
            # Extract symbol and order type from channel
            if '@buyDepth' in channel_name:
                symbol = channel_name.replace('@buyDepth', '')
                order_type = 'buy'
            elif '@sellDepth' in channel_name:
                symbol = channel_name.replace('@sellDepth', '')
                order_type = 'sell'
            else:
                logger.debug(f"Wallex: Unknown channel format: {channel_name}")
                return
            
            # Mark subscription as confirmed
            if symbol not in self.confirmed_subscriptions:
                self.confirmed_subscriptions.add(symbol)
                logger.debug(f"Wallex: Confirmed subscription for {symbol}")
                
            # Remove from pending
            if symbol in self.pending_subscriptions:
                del self.pending_subscriptions[symbol]
            
            # Count messages
            if channel_name not in self.message_count_per_channel:
                self.message_count_per_channel[channel_name] = 0
            self.message_count_per_channel[channel_name] += 1
            
            # ✅ Process order data - طبق مستندات: {"quantity": 255.75, "price": 82131, "sum": 21005003.25}
            if orders_data and isinstance(orders_data, list) and orders_data:
                best_order = orders_data[0]  # First order is the best price
                if isinstance(best_order, dict) and 'price' in best_order and 'quantity' in best_order:
                    price = Decimal(str(best_order['price']))
                    volume = Decimal(str(best_order['quantity']))
                    
                    if order_type == 'buy':
                        await self._store_partial_data_optimized(symbol, bid_price=price, bid_volume=volume)
                        logger.debug(f"Wallex {symbol} buyDepth: price={price}, volume={volume}")
                    else:  # sell
                        await self._store_partial_data_optimized(symbol, ask_price=price, ask_volume=volume)
                        logger.debug(f"Wallex {symbol} sellDepth: price={price}, volume={volume}")
                else:
                    logger.warning(f"Wallex: Invalid order format in {channel_name}: {best_order}")
            else:
                logger.warning(f"Wallex: No orders in {channel_name}")
            
        except Exception as e:
            logger.error(f"Wallex depth data processing error: {e}")

    async def _store_partial_data_optimized(self, symbol: str, bid_price=None, ask_price=None, bid_volume=None, ask_volume=None):
        """Store partial data and save when complete"""
        try:
            if symbol not in self.partial_data:
                self.partial_data[symbol] = {}
            
            current_time = time.time()
            data = self.partial_data[symbol]
            
            # Update data
            if bid_price is not None:
                data['bid_price'] = bid_price
                data['bid_volume'] = bid_volume
                data['bid_time'] = current_time
            
            if ask_price is not None:
                data['ask_price'] = ask_price
                data['ask_volume'] = ask_volume
                data['ask_time'] = current_time
            
            # Save only when we have both bid and ask
            required_fields = ['bid_price', 'ask_price', 'bid_volume', 'ask_volume']
            if all(key in data for key in required_fields):
                last_save_time = data.get('last_save_time', 0)
                
                # Save less frequently to reduce Redis load
                if current_time - last_save_time > 3:  # Save every 3 seconds max
                    await self.save_price_data(
                        symbol,
                        data['bid_price'],
                        data['ask_price'],
                        data['bid_volume'],
                        data['ask_volume']
                    )
                    
                    data['last_save_time'] = current_time
                    logger.debug(f"Wallex {symbol}: bid={data['bid_price']}, ask={data['ask_price']} [saved]")
            
        except Exception as e:
            logger.error(f"Wallex partial data storage error for {symbol}: {e}")

    async def _wallex_optimized_health_checker(self):
        """✅ FIXED: Health checker بهینه‌شده برای Wallex"""
        while self.is_connected and self.websocket:
            try:
                current_time = time.time()
                
                if not self.is_connected:
                    break
                
                # ✅ چک محدودیت 30 دقیقه (25 دقیقه proactive)
                if self.connection_start_time > 0:
                    connection_age = current_time - self.connection_start_time
                    if connection_age > self.CONNECTION_LIMIT:  # 25 دقیقه
                        logger.info("Wallex: Approaching 30min limit, reconnecting proactively...")
                        self.mark_connection_dead("25min proactive reconnect")
                        break
                
                # ✅ چک محدودیت PONG
                if self.pong_count >= self.MAX_PONG_COUNT:  # 95 قبل از 100
                    logger.warning(f"Wallex: PONG count high ({self.pong_count}/100), reconnecting...")
                    self.mark_connection_dead("High PONG count")
                    break
                
                # ✅ چک data flow
                if self.last_data_receive_time > 0:
                    time_since_data = current_time - self.last_data_receive_time
                    if time_since_data > self.DATA_TIMEOUT:  # 3 دقیقه
                        logger.warning(f"Wallex: No data for {time_since_data:.1f}s - reconnecting")
                        self.mark_connection_dead("No data timeout")
                        break
                
                # ✅ چک activity
                if self.last_activity_time > 0:
                    time_since_activity = current_time - self.last_activity_time
                    if time_since_activity > self.MAX_SILENT_PERIOD:  # 40 ثانیه
                        logger.warning(f"Wallex: No activity for {time_since_activity:.1f}s - reconnecting")
                        self.mark_connection_dead("No activity timeout")
                        break
                
                # Clean old partial data
                self._cleanup_old_data(current_time)
                
                # ✅ چک هر 5 ثانیه (برای 20s ping cycle)
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Wallex health checker error: {e}")
                break

    def _cleanup_old_data(self, current_time: float):
        """Clean up old partial data"""
        symbols_to_clean = []
        
        for symbol, data in self.partial_data.items():
            bid_time = data.get('bid_time', 0)
            ask_time = data.get('ask_time', 0)
            max_age = max(bid_time, ask_time)
            
            if current_time - max_age > 300:  # 5 minutes old
                symbols_to_clean.append(symbol)
        
        for symbol in symbols_to_clean:
            del self.partial_data[symbol]
            logger.debug(f"Wallex: Cleaned old data for {symbol}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in message processing)"""
        return None

    def reset_connection_state(self):
        """Reset connection state"""
        super().reset_connection_state()
        self._reset_connection_tracking()

    async def disconnect(self):
        """Clean disconnect"""
        await super().disconnect()
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.websocket = None
        self.subscribed_pairs.clear()
        self.partial_data.clear()
        self.pending_subscriptions.clear()
        self._reset_connection_tracking()
        
        logger.info("Wallex WebSocket disconnected cleanly")