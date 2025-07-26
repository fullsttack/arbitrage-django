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
        
        # Enhanced ping/pong tracking with STRICT requirements for LBank
        self.last_ping_sent_time = 0
        self.last_pong_received_time = 0
        self.server_ping_received_time = 0
        self.last_data_receive_time = 0  # Track actual data reception
        self.client_ping_interval = 45   # Send client ping every 45 seconds (keep alive)
        self.last_server_ping_response = 0  # Track when we last responded to server ping
        self.missed_server_pings = 0     # Count missed server pings
        
        # RELAXED Health check settings for LBank's behavior
        self.MESSAGE_TIMEOUT = 300  # 5 minutes instead of 3 minutes
        self.DATA_TIMEOUT = 600     # 10 minutes for data (was 5 minutes)
        self.PING_TIMEOUT = 120     # 2 minutes ping timeout
        
        # LBank-specific behavior tracking
        self.silent_periods = []  # Track periods without any messages
        self.current_silent_start = 0
        self.max_observed_silent_period = 0
        
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
                
                # Reset all tracking
                self.last_ping_sent_time = 0
                self.last_pong_received_time = 0
                self.server_ping_received_time = 0
                self.last_data_receive_time = 0
                self.last_server_ping_response = 0
                self.missed_server_pings = 0
                self.ping_counter = 1
                self.current_silent_start = 0
                
                # Enhanced connection parameters for LBank stability
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Handle ping manually
                    ping_timeout=None,
                    close_timeout=20,     # Increased to 20 seconds
                    max_size=2**20,
                    max_queue=64,         # Increase queue size
                    compression=None      # Disable compression
                )
                
                self.is_connected = True
                self.reset_connection_state()
                
                # Start health monitoring
                asyncio.create_task(self.health_monitor())
                
                # Start message listener
                asyncio.create_task(self._listen_messages())
                
                # Start enhanced ping handler with RELAXED timing
                asyncio.create_task(self._relaxed_ping_handler())
                
                logger.info("LBank WebSocket connected successfully with relaxed timeouts")
                return True
                
            except Exception as e:
                logger.error(f"LBank connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(60, 2 ** attempt)  # Exponential backoff, max 60s
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
        """Listen for WebSocket messages with MUCH MORE TOLERANT error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 10  # Increased tolerance
        
        while self.is_connected and self.websocket:
            try:
                # Faster timeout for quicker connection issue detection
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=30  # ULTRA-FAST detection - 30 seconds
                )
                
                # Reset error counter on successful message
                consecutive_errors = 0
                current_time = time.time()
                
                # Track end of silent period
                if self.current_silent_start > 0:
                    silent_duration = current_time - self.current_silent_start
                    if silent_duration > 60:  # Only log significant silent periods
                        logger.info(f"LBank: Silent period ended - {silent_duration:.1f}s without messages")
                        self.silent_periods.append({
                            'start': self.current_silent_start,
                            'end': current_time,
                            'duration': silent_duration
                        })
                        # Keep only last 10 silent periods
                        if len(self.silent_periods) > 10:
                            self.silent_periods = self.silent_periods[-10:]
                        
                        # Update max observed
                        if silent_duration > self.max_observed_silent_period:
                            self.max_observed_silent_period = silent_duration
                            logger.info(f"LBank: New max silent period observed: {silent_duration:.1f}s")
                    
                    self.current_silent_start = 0
                
                self.update_message_time()
                self.last_data_receive_time = current_time
                
                # Parse and process message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"LBank: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                logger.warning(f"LBank: No message received for 30s - INSTANT health check")
                
                # Start tracking silent period
                if self.current_silent_start == 0:
                    self.current_silent_start = time.time()
                
                # Check if we missed server pings (critical indicator)
                current_time = time.time()
                time_since_server_ping = current_time - self.server_ping_received_time if self.server_ping_received_time > 0 else float('inf')
                
                if time_since_server_ping > 180:  # No server ping for 3 minutes = problem
                    logger.error(f"LBank: No server ping for {time_since_server_ping:.1f}s - connection likely dead")
                    self.mark_connection_dead(f"No server ping for {time_since_server_ping:.1f}s")
                    break
                
                # Try ping test before giving up
                if not await self._check_connection_with_ping():
                    self.mark_connection_dead("Timeout + ping failed")
                    break
                else:
                    logger.info("LBank: Timeout but ping successful - continuing")
                
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
                await asyncio.sleep(2)

    async def _check_connection_with_ping(self) -> bool:
        """Check if connection is still alive by sending a ping and waiting for pong"""
        try:
            # Send a test ping
            ping_id = f"health-check-{int(time.time())}"
            ping_msg = {
                "action": "ping",
                "ping": ping_id
            }
            
            await self.websocket.send(json.dumps(ping_msg))
            self.last_ping_sent_time = time.time()
            
            logger.debug("LBank: Sent health check ping during silent period")
            
            # Wait up to 30 seconds for any response (pong or any message)
            initial_message_time = self.last_message_time
            
            # Don't wait in a loop that might interfere with main message listener
            await asyncio.sleep(5)  # Single wait
            if self.last_message_time > initial_message_time:
                logger.info("LBank: Health check ping successful - got response")
                return True
            
            logger.warning("LBank: Health check ping failed - no response in 30s")
            return False
            
        except Exception as e:
            logger.error(f"LBank health check ping error: {e}")
            return False

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
                
                # ارسال فوری پونگ
                await self.websocket.send(json.dumps(pong_msg))
                self.last_server_ping_response = current_time
                self.missed_server_pings = 0  # Reset missed counter
                
                self.update_ping_time()
                logger.info(f"LBank: Server ping received, immediately responded with pong: {ping_id}")
                
                # Send heartbeat to Redis to maintain our presence
                await self.send_heartbeat_if_needed()
                
            else:
                self.missed_server_pings += 1
                logger.warning(f"LBank: Could not extract ping ID from server ping: {data} (missed: {self.missed_server_pings})")
                
                # If we miss too many server pings, connection will be terminated by server
                if self.missed_server_pings >= 3:
                    logger.error("LBank: Too many missed server pings, connection will be terminated")
                    self.mark_connection_dead("Too many missed server pings")
                
        except Exception as e:
            self.missed_server_pings += 1
            logger.error(f"LBank server ping handling error: {e} (missed: {self.missed_server_pings})")
            
            # Server ping handling خراب شدن یعنی connection مشکل داره
            if self.missed_server_pings >= 2:
                self.mark_connection_dead(f"Server ping handling failed repeatedly: {e}")
            else:
                logger.warning("LBank: Server ping failed but trying to continue...")

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

    async def _relaxed_ping_handler(self):
        """Enhanced ping handler to prevent 10-minute timeout"""
        while self.is_connected and self.websocket:
            try:
                current_time = time.time()
                
                # Send client ping to keep connection alive
                if current_time - self.last_ping_sent_time >= self.client_ping_interval:
                    await self._send_client_ping()
                
                # More relaxed health checks that account for LBank's silent periods
                if not await self._relaxed_health_check():
                    logger.warning("LBank: Relaxed health check failed")
                    self.mark_connection_dead("Relaxed health check failed")
                    break
                
                # Check if we're approaching 10-minute limit
                connection_duration = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
                if connection_duration > 540:  # 9 minutes - proactive action
                    logger.info(f"LBank: Connection approaching 10min limit ({connection_duration:.0f}s), sending keep-alive ping")
                    await self._send_client_ping()
                
                await asyncio.sleep(5)  # Check every 5 seconds for INSTANT response
                
            except Exception as e:
                logger.error(f"LBank relaxed ping handler error: {e}")
                self.mark_connection_dead(f"Ping handler error: {e}")
                break

    async def _relaxed_health_check(self) -> bool:
        """Enhanced health check that strictly monitors LBank server ping responses"""
        current_time = time.time()
        
        # 1. Check WebSocket state first
        if hasattr(self.websocket, 'closed') and self.websocket.closed:
            logger.warning("LBank: WebSocket is closed")
            return False
        
        # 2. Check if we've missed too many server pings (CRITICAL for LBank)
        if self.missed_server_pings >= 2:
            logger.error(f"LBank: Health check failed - missed {self.missed_server_pings} server pings")
            return False
        
        # 3. Check server ping response timeout (LBank requirement)
        if self.server_ping_received_time > 0:
            time_since_server_ping = current_time - self.server_ping_received_time
            # If no server ping for > 2 minutes, something is wrong
            if time_since_server_ping > 120:
                logger.warning(f"LBank: No server ping for {time_since_server_ping:.1f}s - unusual")
                # Try our own ping to check connection
                if not await self._check_connection_with_ping():
                    logger.error("LBank: No server ping AND our ping failed")
                    return False
        
        # 4. Data freshness check - but more relaxed
        if self.last_data_receive_time > 0:
            time_since_data = current_time - self.last_data_receive_time
            # Only worry if it's been more than 15 minutes without ANY data
            if time_since_data > 900:  # 15 minutes
                logger.warning(f"LBank: No actual data for {time_since_data:.1f}s")
                
                # But still try to ping before giving up
                if await self._check_connection_with_ping():
                    logger.info("LBank: No data but ping successful - probably quiet market")
                    return True
                else:
                    logger.error("LBank: No data AND ping failed - connection dead")
                    return False
        
        # 5. Message freshness - account for observed silent periods
        if self.last_message_time > 0:
            time_since_message = current_time - self.last_message_time
            
            # Use adaptive threshold based on observed behavior
            max_expected_silence = max(600, self.max_observed_silent_period * 1.5)  # At least 10 min, or 150% of max observed
            
            if time_since_message > max_expected_silence:
                logger.warning(f"LBank: No messages for {time_since_message:.1f}s (max expected: {max_expected_silence:.1f}s)")
                
                # Try ping before declaring dead
                if await self._check_connection_with_ping():
                    logger.info("LBank: Long silence but ping successful")
                    return True
                else:
                    logger.error("LBank: Long silence AND ping failed")
                    return False
        
        # 6. Our ping response check - but only if we actually sent one recently
        if self.last_ping_sent_time > 0:
            time_since_our_ping = current_time - self.last_ping_sent_time
            # Only worry if we sent a ping recently and got no response
            if (time_since_our_ping > self.PING_TIMEOUT and 
                (self.last_pong_received_time == 0 or 
                 self.last_pong_received_time < self.last_ping_sent_time)):
                logger.warning(f"LBank: No pong response to our ping for {time_since_our_ping:.1f}s")
                return False
        
        return True

    async def _send_client_ping(self):
        """Send client-initiated ping to server to maintain connection"""
        try:
            if not self.websocket or not self.is_connected:
                logger.warning("LBank: Cannot send ping - websocket not available")
                return
                
            current_time = time.time()
            ping_id = f"keep-alive-{self.ping_counter}-{int(current_time)}"
            
            ping_msg = {
                "action": "ping",
                "ping": ping_id
            }
            
            await self.websocket.send(json.dumps(ping_msg))
            self.last_ping_sent_time = current_time
            self.ping_counter += 1
            
            # Log connection duration when sending ping
            connection_duration = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
            logger.info(f"LBank: Client keep-alive ping sent: {ping_id} (connected for {connection_duration:.0f}s)")
            
        except Exception as e:
            logger.error(f"LBank client ping error: {e}")
            # اگر ping فرستادن با خطا مواجه شد، یعنی connection مشکل دارد
            self.mark_connection_dead(f"Client ping failed: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics including silent periods (NEW)"""
        current_time = time.time()
        
        # Calculate current silent period if any
        current_silent_duration = 0
        if self.current_silent_start > 0:
            current_silent_duration = current_time - self.current_silent_start
        
        # Calculate averages from historical silent periods
        if self.silent_periods:
            avg_silent_duration = sum(p['duration'] for p in self.silent_periods) / len(self.silent_periods)
            total_silent_time = sum(p['duration'] for p in self.silent_periods)
        else:
            avg_silent_duration = 0
            total_silent_time = 0
        
        base_stats = self.get_health_metrics()
        
        # Add LBank-specific stats
        base_stats.update({
            'silent_periods_count': len(self.silent_periods),
            'max_observed_silent_period': self.max_observed_silent_period,
            'avg_silent_period': avg_silent_duration,
            'total_silent_time': total_silent_time,
            'current_silent_duration': current_silent_duration,
            'last_server_ping': self.server_ping_received_time,
            'last_client_ping': self.last_ping_sent_time,
            'last_pong_received': self.last_pong_received_time,
            'client_ping_interval': self.client_ping_interval
        })
        
        return base_stats
    
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
        self.last_server_ping_response = 0
        self.missed_server_pings = 0
        self.ping_counter = 1
        self.current_silent_start = 0
        
        logger.info(f"LBank WebSocket disconnected (observed max silent period: {self.max_observed_silent_period:.1f}s)")