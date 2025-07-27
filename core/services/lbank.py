import asyncio
import json
import logging
import websockets
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

logger = logging.getLogger(__name__)

class LBankService(BaseExchangeService):
    def __init__(self):
        super().__init__('lbank')
        self.websocket_url = 'wss://www.lbkex.net/ws/V2/'
        self.websocket = None
        self.subscribed_pairs = set()
        self.pending_subscriptions = {}
        self.ping_counter = 1
        
        # ✅ FIXED: بهینه‌سازی ping/pong برای LBank
        self.last_ping_sent_time = 0
        self.last_pong_received_time = 0
        self.server_ping_received_time = 0
        self.last_data_receive_time = 0
        self.client_ping_interval = 25      # ✅ کاهش به 25 ثانیه برای safety
        self.last_server_ping_response = 0
        self.missed_server_pings = 0
        
        # ✅ FIXED: تنظیمات مناسب برای LBank behavior
        self.MESSAGE_TIMEOUT = 90           # ✅ افزایش به 90 ثانیه
        self.DATA_TIMEOUT = 300             # ✅ 5 دقیقه برای data
        self.PING_TIMEOUT = 60              # ✅ 60 ثانیه ping timeout
        self.MAX_SILENT_PERIOD = 120        # ✅ حداکثر 2 دقیقه سکوت
        
        # Connection lifecycle management
        self.connection_health_checks = 0
        self.last_activity_time = 0
        self.proactive_ping_sent = False   # جلوگیری از ping spam
        
    async def connect(self):
        """اتصال بهینه‌شده به LBank WebSocket"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"LBank connection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # ✅ Reset تمام tracking variables
                self._reset_ping_tracking()
                
                # ✅ FIXED: پارامترهای بهینه برای LBank
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,      # Manual ping handling
                    ping_timeout=None,
                    close_timeout=15,        # کاهش timeout
                    max_size=1024*1024,      # 1MB limit
                    max_queue=32,            # Reasonable queue size
                    compression=None
                )
                
                self.is_connected = True
                self.reset_connection_state()
                self.last_activity_time = time.time()
                
                # Start tasks
                asyncio.create_task(self.health_monitor())
                asyncio.create_task(self._listen_messages())
                asyncio.create_task(self._optimized_ping_handler())
                
                logger.info("LBank WebSocket connected successfully with optimized settings")
                return True
                
            except Exception as e:
                logger.error(f"LBank connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(30, 2 ** attempt)
                    logger.info(f"LBank retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.mark_connection_dead(f"Failed after {max_retries} attempts: {e}")
                    return False

    def _reset_ping_tracking(self):
        """Reset تمام tracking variables"""
        self.last_ping_sent_time = 0
        self.last_pong_received_time = 0
        self.server_ping_received_time = 0
        self.last_data_receive_time = 0
        self.last_server_ping_response = 0
        self.missed_server_pings = 0
        self.ping_counter = 1
        self.connection_health_checks = 0
        self.last_activity_time = 0
        self.proactive_ping_sent = False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """اشتراک بهینه‌شده در trading pairs"""
        if not self.is_connected or not self.websocket:
            logger.error("LBank: Cannot subscribe - not connected")
            return False
        
        successful_subscriptions = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # ✅ طبق documentation درست LBank
                    subscribe_msg = {
                        "action": "subscribe",
                        "subscribe": "depth",
                        "pair": symbol,
                        "depth": "100"
                    }
                    
                    logger.debug(f"LBank subscribing to {symbol}...")
                    await self.websocket.send(json.dumps(subscribe_msg))
                    
                    self.pending_subscriptions[symbol] = time.time()
                    self.last_activity_time = time.time()  # ✅ Track activity
                    
                    # Reasonable delay
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"LBank subscription error for {symbol}: {e}")
        
        # Wait for confirmations
        await asyncio.sleep(3)
        
        # Count confirmed subscriptions
        for symbol in pairs:
            if symbol in self.subscribed_pairs:
                successful_subscriptions += 1
                logger.debug(f"LBank confirmed subscription for {symbol}")
            else:
                logger.warning(f"LBank no confirmation received for {symbol}")
        
        logger.info(f"LBank: Successfully subscribed to {successful_subscriptions}/{len(pairs)} pairs")
        return successful_subscriptions > 0

    async def _listen_messages(self):
        """بهینه‌سازی شده message listener"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_connected and self.websocket:
            try:
                # ✅ FIXED: timeout مناسب برای LBank
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=self.MESSAGE_TIMEOUT  # 90 ثانیه
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
                    logger.warning(f"LBank: Invalid JSON: {str(message)[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                # ✅ FIXED: مدیریت مناسب timeout
                current_time = time.time()
                time_since_activity = current_time - self.last_activity_time
                
                logger.warning(f"LBank: Message timeout ({self.MESSAGE_TIMEOUT}s), "
                             f"last activity: {time_since_activity:.1f}s ago")
                
                # تنها زمانی که واقعاً مشکل هست disconnect کن
                if time_since_activity > self.MAX_SILENT_PERIOD:
                    logger.error(f"LBank: Extended silence ({time_since_activity:.1f}s) - disconnecting")
                    self.mark_connection_dead(f"Extended silence: {time_since_activity:.1f}s")
                    break
                else:
                    # فقط warning و ادامه
                    logger.info("LBank: Timeout but still within acceptable range - continuing")
                    continue
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"LBank WebSocket connection closed: {e}")
                self.mark_connection_dead(f"Connection closed: {e}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"LBank message error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("LBank: Too many consecutive errors")
                    self.mark_connection_dead(f"Too many errors: {e}")
                    break
                
                await asyncio.sleep(2)

    async def _process_message(self, data: Dict[str, Any]):
        """پردازش بهینه‌شده پیام‌ها"""
        try:
            # ✅ Handle server ping - طبق docs دقیق
            if isinstance(data, dict) and data.get('action') == 'ping':
                await self._handle_server_ping(data)
            
            # Handle pong responses
            elif isinstance(data, dict) and data.get('action') == 'pong':
                await self._handle_pong_response(data)
            
            # Handle depth data
            elif data.get('type') == 'depth' and 'depth' in data:
                await self._process_depth_data(data)
            
            # Handle subscription confirmations
            elif 'subscribe' in data or 'subscribed' in data:
                logger.info(f"LBank subscription response: {data}")
                pair = data.get('pair', '')
                if pair and pair in self.pending_subscriptions:
                    self.subscribed_pairs.add(pair)
                    del self.pending_subscriptions[pair]
                    logger.debug(f"LBank confirmed subscription for {pair}")
            
            # Handle errors
            elif 'error' in data or data.get('success') is False:
                logger.warning(f"LBank error message: {data}")
            
            else:
                logger.debug(f"LBank unhandled message: {data}")
                
        except Exception as e:
            logger.error(f"LBank message processing error: {e}")

    async def _handle_server_ping(self, data: Dict[str, Any]):
        """✅ FIXED: مدیریت صحیح server ping"""
        try:
            current_time = time.time()
            self.server_ping_received_time = current_time
            self.last_activity_time = current_time
            
            ping_id = data.get('ping')
            
            if ping_id:
                # ✅ فوری pong بفرست - طبق docs حداکثر 1 دقیقه فرصت داریم
                pong_msg = {
                    "action": "pong", 
                    "pong": ping_id
                }
                
                await self.websocket.send(json.dumps(pong_msg))
                self.last_server_ping_response = current_time
                self.missed_server_pings = 0
                
                self.update_ping_time()
                logger.debug(f"LBank: Server ping received, responded with pong: {ping_id}")
                
                # Send heartbeat to Redis
                await self.send_heartbeat_if_needed()
                
            else:
                self.missed_server_pings += 1
                logger.warning(f"LBank: Invalid server ping format: {data}")
                
                if self.missed_server_pings >= 3:
                    logger.error("LBank: Too many invalid server pings")
                    self.mark_connection_dead("Invalid server ping format")
                
        except Exception as e:
            self.missed_server_pings += 1
            logger.error(f"LBank server ping error: {e}")
            
            if self.missed_server_pings >= 2:
                self.mark_connection_dead(f"Server ping handling failed: {e}")

    async def _handle_pong_response(self, data: Dict[str, Any]):
        """مدیریت pong responses"""
        try:
            current_time = time.time()
            self.last_pong_received_time = current_time
            self.last_activity_time = current_time
            
            pong_id = data.get('pong', 'unknown')
            response_time = current_time - self.last_ping_sent_time if self.last_ping_sent_time > 0 else 0
            
            logger.debug(f"LBank: Pong received: {pong_id} (response: {response_time:.3f}s)")
            
        except Exception as e:
            logger.error(f"LBank pong response error: {e}")

    async def _process_depth_data(self, data: Dict[str, Any]):
        """پردازش depth data"""
        try:
            self.last_data_receive_time = time.time()
            self.last_activity_time = time.time()
            
            depth_data = data.get('depth', {})
            symbol = data.get('pair', '')
            
            # Mark subscription as working
            if symbol and symbol in self.pending_subscriptions:
                self.subscribed_pairs.add(symbol)
                del self.pending_subscriptions[symbol]
                logger.debug(f"LBank confirmed subscription for {symbol} via data")
            
            # Process bid/ask data
            asks = depth_data.get('asks', [])
            bids = depth_data.get('bids', [])
            
            if asks and bids and symbol:
                # Best prices
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"LBank {symbol}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            else:
                logger.warning(f"LBank: Incomplete depth data for {symbol}")
            
        except Exception as e:
            logger.error(f"LBank depth data error: {e}")

    async def _optimized_ping_handler(self):
        """✅ FIXED: ping handler بهینه‌شده"""
        while self.is_connected and self.websocket:
            try:
                current_time = time.time()
                
                # ✅ ارسال client ping منظم
                if current_time - self.last_ping_sent_time >= self.client_ping_interval:
                    await self._send_client_ping()
                
                # ✅ بررسی health بدون aggressive timeout
                if not await self._intelligent_health_check():
                    logger.warning("LBank: Health check failed")
                    self.mark_connection_dead("Health check failed")
                    break
                
                # ✅ REMOVED: ping spam نزدیک محدودیت 10 دقیقه
                # کد قبلی که بعد از 540 ثانیه ping spam می‌کرد حذف شد
                
                await asyncio.sleep(10)  # چک هر 10 ثانیه
                
            except Exception as e:
                logger.error(f"LBank ping handler error: {e}")
                self.mark_connection_dead(f"Ping handler error: {e}")
                break

    async def _intelligent_health_check(self) -> bool:
        """✅ FIXED: health check هوشمند"""
        current_time = time.time()
        
        # 1. WebSocket state
        if hasattr(self.websocket, 'closed') and self.websocket.closed:
            logger.warning("LBank: WebSocket is closed")
            return False
        
        # 2. ✅ بررسی تعداد server ping های از دست رفته
        if self.missed_server_pings >= 2:
            logger.error(f"LBank: Too many missed server pings ({self.missed_server_pings})")
            return False
        
        # 3. ✅ بررسی مناسب server ping timeout
        if self.server_ping_received_time > 0:
            time_since_server_ping = current_time - self.server_ping_received_time
            if time_since_server_ping > 180:  # 3 دقیقه بدون server ping
                logger.warning(f"LBank: No server ping for {time_since_server_ping:.1f}s - connection may be dead")
                return False
        
        # 4. ✅ بررسی overall activity
        if self.last_activity_time > 0:
            time_since_activity = current_time - self.last_activity_time
            if time_since_activity > self.MAX_SILENT_PERIOD:  # 2 دقیقه
                logger.warning(f"LBank: No activity for {time_since_activity:.1f}s")
                return False
        
        # 5. ✅ بررسی pong response (اگر ping فرستادیم)
        if self.last_ping_sent_time > 0:
            time_since_ping = current_time - self.last_ping_sent_time
            if (time_since_ping > self.PING_TIMEOUT and 
                (self.last_pong_received_time == 0 or 
                 self.last_pong_received_time < self.last_ping_sent_time)):
                logger.warning(f"LBank: No pong response for {time_since_ping:.1f}s - server not responding to our pings")
                return False
        
        return True

    async def _send_client_ping(self):
        """ارسال client ping"""
        try:
            if not self.websocket or not self.is_connected:
                return
                
            current_time = time.time()
            ping_id = f"keep-alive-{self.ping_counter}-{int(current_time)}"
            
            ping_msg = {
                "action": "ping",
                "ping": ping_id
            }
            
            await self.websocket.send(json.dumps(ping_msg))
            self.last_ping_sent_time = current_time
            self.last_activity_time = current_time
            self.ping_counter += 1
            
            logger.debug(f"LBank: Client ping sent: {ping_id}")
            
        except Exception as e:
            logger.error(f"LBank client ping error: {e}")
            self.mark_connection_dead(f"Client ping failed: {e}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_depth_data)"""
        return None

    def reset_connection_state(self):
        """Reset connection state"""
        super().reset_connection_state()
        self._reset_ping_tracking()

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
        self.pending_subscriptions.clear()
        self._reset_ping_tracking()
        
        logger.info("LBank WebSocket disconnected cleanly")