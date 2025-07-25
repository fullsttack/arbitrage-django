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
        self.pending_subscriptions = {}  # Track pending subscriptions
        self.ping_counter = 1
        
        # Enhanced ping/pong tracking
        self.last_ping_sent_time = 0
        self.last_pong_received_time = 0
        self.server_ping_received_time = 0
        self.last_data_receive_time = 0  # Track actual data reception
        self.client_ping_interval = 15  # Send client ping every 15s (aggressive keep-alive)
        
    async def connect(self):
        """Connect to LBank WebSocket with enhanced ping/pong handling"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"LBank connection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # Reset ping/pong tracking
                self.last_ping_sent_time = 0
                self.last_pong_received_time = 0
                self.server_ping_received_time = 0
                self.last_data_receive_time = 0
                self.ping_counter = 1
                
                # Simplified connection parameters
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Handle ping manually
                    ping_timeout=None,
                    close_timeout=10,
                    max_size=2**20
                )
                
                self.is_connected = True
                self.reset_connection_state()
                
                # Start enhanced health monitoring
                asyncio.create_task(self.health_monitor())
                
                # Start message listener
                asyncio.create_task(self._listen_messages())
                
                # Start enhanced ping handler
                asyncio.create_task(self._enhanced_ping_handler())
                
                logger.info("LBank WebSocket connected successfully")
                return True
                
            except Exception as e:
                logger.error(f"LBank connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(30, 2 ** attempt)  # Exponential backoff, max 30s
                    logger.info(f"LBank retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.mark_connection_dead(f"Failed after {max_retries} attempts: {e}")
                    return False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs with response validation"""
        if not self.is_connected or not self.websocket:
            logger.error("LBank: Cannot subscribe - not connected")
            return False
        
        successful_subscriptions = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Subscribe to depth updates - according to official LBank docs
                    subscribe_msg = {
                        "action": "subscribe",
                        "subscribe": "depth",
                        "pair": symbol,
                        "depth": "100"  # Official docs use "100"
                    }
                    
                    logger.info(f"LBank subscribing to {symbol}...")
                    await self.websocket.send(json.dumps(subscribe_msg))
                    
                    # Track pending subscription
                    self.pending_subscriptions[symbol] = time.time()
                    
                    # Small delay between subscriptions
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"LBank subscription error for {symbol}: {e}")
        
        # Wait for subscription confirmations or data
        await asyncio.sleep(3)
        
        # Count actually working subscriptions
        for symbol in pairs:
            # Check if we received data or confirmation for this symbol
            if symbol in self.subscribed_pairs:
                successful_subscriptions += 1
                logger.info(f"LBank confirmed subscription for {symbol}")
            else:
                logger.warning(f"LBank no confirmation received for {symbol}")
        
        logger.info(f"LBank: Successfully subscribed to {successful_subscriptions}/{len(pairs)} pairs")
        return successful_subscriptions > 0

    async def _listen_messages(self):
        """Listen for WebSocket messages with enhanced error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_connected and self.websocket:
            try:
                # Shorter timeout for better responsiveness - but not too aggressive
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=90  # 90 seconds - reasonable timeout
                )
                
                # Reset error counter on successful message
                consecutive_errors = 0
                self.update_message_time()
                self.last_data_receive_time = time.time()  # Track data reception
                
                # Parse and process message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"LBank: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                logger.debug(f"LBank: No message received for 90 seconds - checking connection health")
                # Don't immediately disconnect - check actual connection health instead  
                if not await self._check_actual_connection_health():
                    self.mark_connection_dead("Actual connection problems detected")
                    break
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"LBank WebSocket connection closed: {e}")
                self.mark_connection_dead(f"Connection closed: {e}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"LBank message processing error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("LBank: Too many consecutive errors, marking connection as dead")
                    self.mark_connection_dead(f"Too many errors: {e}")
                    break
                
                # Brief pause before continuing
                await asyncio.sleep(1)

    async def _check_ping_pong_health(self) -> bool:
        """Check ping/pong health with relaxed server ping requirement"""
        current_time = time.time()
        
        # اگر data می‌آید، یعنی connection زنده است - مهم‌ترین فاکتور
        if self.last_data_receive_time > 0:
            time_since_data = current_time - self.last_data_receive_time
            if time_since_data > 300:  # 5 دقیقه بدون data = مشکل واقعی
                logger.warning(f"LBank: No data received for {time_since_data:.1f}s")
                return False
        
        # Server ping optional - اگر نباشد مشکلی نیست
        if self.server_ping_received_time > 0:
            time_since_server_ping = current_time - self.server_ping_received_time
            if time_since_server_ping > 600:  # 10 دقیقه (relaxed)
                logger.info(f"LBank: No server ping for {time_since_server_ping:.1f}s (server may not send periodic pings)")
        
        # Client ping health - اگر خودمان ping فرستادیم ولی pong نگرفتیم
        if self.last_ping_sent_time > 0 and self.last_pong_received_time > 0:
            ping_response_time = self.last_pong_received_time - self.last_ping_sent_time
            if ping_response_time < 0:  # pong قبل از ping = مشکل timing
                time_since_our_ping = current_time - self.last_ping_sent_time
                if time_since_our_ping > 120:  # 2 دقیقه بدون pong به ping ما
                    logger.warning(f"LBank: No pong to our ping for {time_since_our_ping:.1f}s")
                    return False
        
        return True

    async def _process_message(self, data: Dict[str, Any]):
        """Process different types of messages from LBank with enhanced ping handling"""
        try:
            # Handle depth data
            if data.get('type') == 'depth' and 'depth' in data:
                await self._process_depth_data(data)
            
            # Enhanced server ping handling - multiple formats
            elif data.get('action') == 'ping' or 'ping' in data:
                await self._handle_server_ping(data)
            
            # Handle pong responses to our client pings
            elif data.get('action') == 'pong':
                await self._handle_pong_response(data)
            
            # Handle subscription confirmations
            elif 'subscribe' in data or 'subscribed' in data:
                logger.info(f"LBank subscription response: {data}")
                # Mark subscription as confirmed
                pair = data.get('pair', '')
                if pair and pair in self.pending_subscriptions:
                    self.subscribed_pairs.add(pair)
                    del self.pending_subscriptions[pair]
                    logger.info(f"LBank confirmed subscription for {pair}")
            
            # Handle errors
            elif 'error' in data or data.get('success') is False:
                logger.warning(f"LBank error message: {data}")
            
            else:
                logger.debug(f"LBank unhandled message type: {data}")
                
        except Exception as e:
            logger.error(f"LBank message processing error: {e}")

    async def _handle_server_ping(self, data: Dict[str, Any]):
        """Handle server ping according to LBank docs - CRITICAL: respond within 1 minute!"""
        try:
            current_time = time.time()
            self.server_ping_received_time = current_time
            
            ping_id = None
            
            # LBank ping format: {"action": "ping", "ping": "uuid"}
            if data.get('action') == 'ping' and 'ping' in data:
                ping_id = data['ping']
            
            # Alternative format: {"ping": "uuid"}
            elif 'ping' in data and 'action' not in data:
                ping_id = data['ping']
            
            if ping_id:
                # فوری pong بفرست - LBank در عرض 1 دقیقه انتظار داره!
                pong_msg = {
                    "action": "pong", 
                    "pong": ping_id
                }
                await self.websocket.send(json.dumps(pong_msg))
                
                self.update_ping_time()
                logger.info(f"LBank: Server ping received, immediately responded with pong: {ping_id}")
            else:
                logger.warning(f"LBank: Could not extract ping ID from server ping: {data}")
                
        except Exception as e:
            logger.error(f"LBank server ping handling error: {e}")
            # Server ping handling خراب شدن یعنی connection مشکل داره
            self.mark_connection_dead(f"Server ping handling failed: {e}")

    async def _handle_pong_response(self, data: Dict[str, Any]):
        """Handle pong responses to our client pings"""
        try:
            current_time = time.time()
            self.last_pong_received_time = current_time
            
            pong_id = data.get('pong', 'unknown')
            response_time = current_time - self.last_ping_sent_time if self.last_ping_sent_time > 0 else 0
            
            logger.debug(f"LBank: Pong received for client ping: {pong_id} (response time: {response_time:.3f}s)")
            
        except Exception as e:
            logger.error(f"LBank pong response handling error: {e}")

    async def _process_depth_data(self, data: Dict[str, Any]):
        """Process depth data from LBank WebSocket"""
        try:
            # Update data receive time for health monitoring
            self.last_data_receive_time = time.time()
            
            depth_data = data.get('depth', {})
            symbol = data.get('pair', '')
            
            # Mark subscription as working when we receive data
            if symbol and symbol in self.pending_subscriptions:
                self.subscribed_pairs.add(symbol)
                del self.pending_subscriptions[symbol]
                logger.info(f"LBank confirmed subscription for {symbol} via data reception")
            
            # Get best bid and ask
            asks = depth_data.get('asks', [])
            bids = depth_data.get('bids', [])
            
            if asks and bids and symbol:
                # Best ask (lowest sell price)  
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                
                # Best bid (highest buy price)
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                # Save price data with separate volumes
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"LBank {symbol}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            else:
                logger.warning(f"LBank: Incomplete depth data for {symbol}")
            
        except Exception as e:
            logger.error(f"LBank depth data processing error: {e}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_depth_data)"""
        return None

    async def _enhanced_ping_handler(self):
        """Final ping handler based on official LBank documentation"""
        while self.is_connected and self.websocket:
            try:
                current_time = time.time()
                
                # کلید موفقیت: Client ping proactive بفرست (طبق داکیومنت مجاز است)
                if current_time - self.last_ping_sent_time >= self.client_ping_interval:
                    await self._send_client_ping()
                
                # فقط روی actual problems چک کن
                if not await self._check_actual_connection_health():
                    logger.warning("LBank: Actual connection health check failed")
                    self.mark_connection_dead("Actual connection health check failed")
                    break
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"LBank ping handler error: {e}")
                self.mark_connection_dead(f"Ping handler error: {e}")
                break

    async def _check_actual_connection_health(self) -> bool:
        """Check ONLY actual problems, not expected server behavior"""
        current_time = time.time()
        
        # 1. اصلی‌ترین چک: آیا depth data می‌آید؟
        if self.last_data_receive_time > 0:
            time_since_data = current_time - self.last_data_receive_time
            if time_since_data > 300:  # 5 دقیقه بدون data = مشکل واقعی
                logger.warning(f"LBank: No depth data for {time_since_data:.1f}s - connection dead")
                return False
            elif time_since_data > 120:  # 2 دقیقه - هشدار
                logger.debug(f"LBank: No new data for {time_since_data:.1f}s (monitoring...)")
        
        # 2. WebSocket خودش بسته شده؟
        if hasattr(self.websocket, 'closed') and self.websocket.closed:
            logger.warning("LBank: WebSocket is closed")
            return False
        
        # 3. اگر ما ping فرستادیم ولی server پاسخ نداد (این مشکل واقعی است)
        if self.last_ping_sent_time > 0:
            time_since_our_ping = current_time - self.last_ping_sent_time
            # اگر 90 ثانیه گذشت و هنوز pong نگرفتیم
            if (time_since_our_ping > 90 and 
                (self.last_pong_received_time == 0 or 
                 self.last_pong_received_time < self.last_ping_sent_time)):
                logger.warning(f"LBank: No pong response to our ping for {time_since_our_ping:.1f}s")
                return False
        
        # Server ping status - فقط info، نه warning
        if self.server_ping_received_time > 0:
            time_since_server_ping = current_time - self.server_ping_received_time
            if time_since_server_ping > 600:  # 10 دقیقه
                logger.debug(f"LBank: No server ping for {time_since_server_ping:.1f}s (server sends periodically when needed)")
        else:
            logger.debug("LBank: No server ping received yet (server sends periodically when needed)")
        
        # مهم: Server ping نیامدن مشکل نیست! Server "periodically" می‌فرسته
        # یعنی ممکنه هر 5 دقیقه، هر 10 دقیقه، یا اصلاً نفرسته
        
        return True

    async def _send_client_ping(self):
        """Send client-initiated ping to server to maintain connection"""
        try:
            current_time = time.time()
            ping_id = f"client-ping-{self.ping_counter}-{int(current_time)}"
            
            ping_msg = {
                "action": "ping",
                "ping": ping_id
            }
            
            await self.websocket.send(json.dumps(ping_msg))
            self.last_ping_sent_time = current_time
            self.ping_counter += 1
            
            logger.debug(f"LBank client ping sent: {ping_id}")
            
        except Exception as e:
            logger.error(f"LBank client ping error: {e}")
            # اگر ping فرستادن با خطا مواجه شد، یعنی connection مشکل دارد
            self.mark_connection_dead(f"Client ping failed: {e}")
    
    async def disconnect(self):
        """Disconnect from LBank"""
        await super().disconnect()
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.websocket = None
        self.subscribed_pairs.clear()
        self.pending_subscriptions.clear()
        
        # Reset ping/pong tracking
        self.last_ping_sent_time = 0
        self.last_pong_received_time = 0
        self.server_ping_received_time = 0
        self.last_data_receive_time = 0
        self.ping_counter = 1
        
        logger.info("LBank WebSocket disconnected")