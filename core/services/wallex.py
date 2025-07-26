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
        
        # Enhanced connection management
        self.last_data_receive_time = 0
        self.connection_restart_count = 0
        self.MAX_RESTARTS_PER_HOUR = 10  # محدودیت restart
        self.restart_times = []  # Track restart times
        
        # Subscription confirmation tracking  
        self.confirmed_subscriptions = set()
        self.subscription_timeout = 30  # Wait 30s for subscription confirmation
        
        # Wallex-specific optimizations
        self.USE_ALL_PRICE_CHANNEL = False  # Alternative approach
        
    async def connect(self):
        """Enhanced connection with IP throttling awareness"""
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
                
                # Reset all counters and tracking
                self.pong_count = 0
                self.message_count_per_channel.clear()
                self.last_server_ping_time = 0
                self.last_data_receive_time = 0
                self.confirmed_subscriptions.clear()
                
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
                self.restart_times.append(current_time)
                self.connection_restart_count += 1
                
                # Start monitoring tasks
                asyncio.create_task(self.health_monitor())
                asyncio.create_task(self._listen_messages())
                asyncio.create_task(self._enhanced_health_checker())
                
                logger.info(f"Wallex WebSocket connected successfully (restart #{self.connection_restart_count})")
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

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Enhanced subscription with better tracking and fallback"""
        if not self.is_connected or not self.websocket:
            logger.error("Wallex: Cannot subscribe - not connected")
            return False
        
        logger.info(f"Wallex: Starting subscription to {len(pairs)} pairs: {pairs}")
        
        # Option 1: Try individual subscriptions first
        success_count = await self._subscribe_individual_pairs(pairs)
        
        # Wait longer for confirmations (Wallex can be slow to respond)
        logger.info("Wallex: Waiting for subscription confirmations...")
        await asyncio.sleep(10)  # Increased from 5 to 10 seconds
        
        # Check actual confirmations
        confirmed_count = len(self.confirmed_subscriptions)
        logger.info(f"Wallex: {confirmed_count}/{len(pairs)} subscriptions confirmed")
        
        # DO NOT use all@price as fallback - it returns ALL symbols, not just ours
        # We need individual @trade subscriptions to work properly
        
        # Only accept if we have individual subscriptions working
        if confirmed_count > 0:
            logger.info(f"Wallex: Successfully subscribed to {confirmed_count}/{len(pairs)} individual pairs")
            return True
        else:
            logger.error("Wallex: No individual subscriptions confirmed - individual @trade channels not working")
            return False

    async def _subscribe_individual_pairs(self, pairs: List[str]) -> int:
        """Subscribe to individual trading pairs using correct Wallex format"""
        successful_subscriptions = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Add delay between subscriptions to avoid rate limiting
                    if successful_subscriptions > 0:
                        await asyncio.sleep(1)  # 1 second between subscriptions
                    
                    # Subscribe to buyDepth and sellDepth for each symbol (طابق مستندات Wallex)
                    # Format: ["subscribe", {"channel": "SYMBOL@buyDepth"}] and ["subscribe", {"channel": "SYMBOL@sellDepth"}]
                    
                    # Subscribe to buy depth
                    buy_subscribe_msg = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    logger.info(f"Wallex subscribing to {symbol}@buyDepth...")
                    await self.websocket.send(json.dumps(buy_subscribe_msg))
                    
                    # Small delay between subscriptions
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to sell depth
                    sell_subscribe_msg = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    logger.info(f"Wallex subscribing to {symbol}@sellDepth...")
                    await self.websocket.send(json.dumps(sell_subscribe_msg))
                    
                    # Track pending subscription
                    self.pending_subscriptions[symbol] = time.time()
                    
                    # Initialize message counters for both channels
                    self.message_count_per_channel[f"{symbol}@buyDepth"] = 0
                    self.message_count_per_channel[f"{symbol}@sellDepth"] = 0
                    
                    successful_subscriptions += 1
                    
                except Exception as e:
                    logger.error(f"Wallex subscription error for {symbol}: {e}")
        
        return successful_subscriptions

    async def _subscribe_all_price_channel(self):
        """Fallback: Subscribe to all@price channel for all symbols"""
        try:
            subscribe_msg = ["subscribe", {"channel": "all@price"}]
            logger.info("Wallex: Subscribing to all@price channel as fallback")
            await self.websocket.send(json.dumps(subscribe_msg))
            self.USE_ALL_PRICE_CHANNEL = True
        except Exception as e:
            logger.error(f"Wallex all@price subscription error: {e}")

    async def _listen_messages(self):
        """Enhanced message listener with better error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 3  # More strict
        
        while self.is_connected and self.websocket:
            try:
                # Faster timeout for quicker detection of issues
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=15  # 15 seconds timeout for INSTANT detection
                )
                
                consecutive_errors = 0
                self.update_message_time()
                self.last_data_receive_time = time.time()
                
                # Parse message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Wallex: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                logger.warning("Wallex: Message timeout (15s) - INSTANT health check")
                if not await self._check_connection_health():
                    break
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Wallex WebSocket connection closed: {e}")
                self.mark_connection_dead(f"Connection closed: {e}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Wallex message processing error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Wallex: Too many consecutive errors, marking connection as dead")
                    self.mark_connection_dead(f"Too many errors: {e}")
                    break
                
                await asyncio.sleep(1)

    async def _check_connection_health(self) -> bool:
        """Enhanced connection health check"""
        current_time = time.time()
        
        # Check if we received any data recently
        if self.last_data_receive_time > 0:
            time_since_data = current_time - self.last_data_receive_time
            if time_since_data > 120:  # 2 minutes without data
                logger.warning(f"Wallex: No data received for {time_since_data:.1f}s - possible server throttling")
                return False
        
        # Check WebSocket state
        if hasattr(self.websocket, 'closed') and self.websocket.closed:
            logger.warning("Wallex: WebSocket is closed")
            return False
        
        # Send a ping to test connection
        try:
            ping_id = f"health-check-{int(current_time)}"
            ping_msg = {"ping": ping_id}
            await self.websocket.send(json.dumps(ping_msg))
            logger.debug("Wallex: Sent health check ping")
        except Exception as e:
            logger.error(f"Wallex: Failed to send health check ping: {e}")
            return False
        
        return True

    async def _process_message(self, data):
        """Enhanced message processing with subscription tracking"""
        try:
            # Handle server PING
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
            
            # Process data based on channel type
            if isinstance(data, list) and len(data) == 2:
                channel_name = data[0]
                
                # Handle all@price channel specifically (not used for our implementation)
                if channel_name == "all@price":
                    await self._process_all_price_data(data)
                # Handle buyDepth and sellDepth channels (main implementation)
                elif '@buyDepth' in channel_name or '@sellDepth' in channel_name:
                    await self._process_depth_data(data)
                # Handle other channel types
                else:
                    logger.debug(f"Wallex: Unknown channel type: {channel_name}")
            
            else:
                logger.info(f"Wallex unhandled message format: {str(data)[:200]}...")
                
        except Exception as e:
            logger.error(f"Wallex message processing error: {e}")

    async def _process_all_price_data(self, data: list):
        """Process all@price channel data"""
        try:
            price_info = data[1]
            symbol = price_info.get('symbol', '')
            price = price_info.get('price', 0)
            
            if symbol and price:
                # Convert to standard format for consistency
                price_decimal = Decimal(str(price))
                
                # For all@price, we only get the current price, not bid/ask separately
                # Use price as both bid and ask with small spread
                spread = price_decimal * Decimal('0.001')  # 0.1% spread assumption
                bid_price = price_decimal - spread
                ask_price = price_decimal + spread
                
                await self.save_price_data(
                    symbol, 
                    bid_price, 
                    ask_price, 
                    Decimal('1000'),  # Default volume
                    Decimal('1000')
                )
                
                logger.debug(f"Wallex all@price {symbol}: {price}")
                
        except Exception as e:
            logger.error(f"Wallex all@price processing error: {e}")

    async def _process_depth_data(self, data: list):
        """Process buyDepth and sellDepth data from Wallex"""
        try:
            channel_name = data[0]  # e.g., "DOGEUSDT@buyDepth" or "DOGEUSDT@sellDepth"
            orders_data = data[1]   # Array of order objects
            
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
                logger.info(f"Wallex: Confirmed subscription for {symbol}")
                
            # Remove from pending
            if symbol in self.pending_subscriptions:
                del self.pending_subscriptions[symbol]
            
            # Count messages
            if channel_name not in self.message_count_per_channel:
                self.message_count_per_channel[channel_name] = 0
            self.message_count_per_channel[channel_name] += 1
            
            # Process order data - format: [{"quantity": 255.75, "price": 82131, "sum": 21005003.25}, ...]
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
        """Optimized partial data storage with reduced saves"""
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

    async def _handle_server_ping(self, data: Dict[str, Any]):
        """Handle server PING with PONG limit awareness"""
        try:
            ping_id = data.get('ping')
            if ping_id:
                # Check PONG limit
                if self.pong_count >= 95:  # Conservative limit
                    logger.warning(f"Wallex: PONG limit approaching ({self.pong_count}/100), reconnecting preemptively")
                    self.mark_connection_dead("PONG limit approaching")
                    return
                
                # Send PONG response
                pong_msg = {"pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                
                self.pong_count += 1
                self.last_server_ping_time = time.time()
                self.update_ping_time()
                
                logger.debug(f"Wallex PONG sent ({self.pong_count}/100)")
                
        except Exception as e:
            logger.error(f"Wallex PING handling error: {e}")

    async def _enhanced_health_checker(self):
        """Enhanced health checker with proactive reconnection"""
        while self.is_connected and self.websocket:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds for INSTANT detection
                
                if not self.is_connected:
                    break
                
                current_time = time.time()
                
                # Check data flow - more tolerant for quiet markets
                if self.last_data_receive_time > 0:
                    time_since_data = current_time - self.last_data_receive_time
                    if time_since_data > 180:  # 3 minutes without data (increased from 90s)
                        logger.warning(f"Wallex: No data for {time_since_data:.1f}s - reconnecting proactively")
                        self.mark_connection_dead("Proactive reconnect - no data")
                        break
                
                # Check 25-minute limit (before 30-minute Wallex limit)
                if self.connection_start_time > 0:
                    connection_age = current_time - self.connection_start_time
                    if connection_age > 1500:  # 25 minutes
                        logger.info("Wallex: Approaching 30min limit, reconnecting...")
                        self.mark_connection_dead("25min proactive reconnect")
                        break
                
                # Check PONG count
                if self.pong_count >= 90:  # Before hitting 100 limit
                    logger.warning(f"Wallex: PONG count high ({self.pong_count}/100), reconnecting...")
                    self.mark_connection_dead("High PONG count")
                    break
                
                # Clean old partial data
                self._cleanup_old_data(current_time)
                
            except Exception as e:
                logger.error(f"Wallex enhanced health checker error: {e}")
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
        self.pong_count = 0
        self.message_count_per_channel.clear()
        self.last_server_ping_time = 0
        self.last_data_receive_time = 0
        self.confirmed_subscriptions.clear()

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
        self.message_count_per_channel.clear()
        self.confirmed_subscriptions.clear()
        self.connection_start_time = 0
        self.pong_count = 0
        self.last_server_ping_time = 0
        self.last_data_receive_time = 0
        
        logger.info("Wallex WebSocket disconnected cleanly")