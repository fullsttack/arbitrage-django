import asyncio
import json
import logging
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
        
    async def connect(self):
        """Connect to Wallex WebSocket with enhanced error handling"""
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
                
                # Simplified connection parameters - only use supported ones
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=20,  # Built-in ping every 20 seconds
                    ping_timeout=10,   # Wait 10 seconds for pong
                    close_timeout=10
                )
                
                self.is_connected = True
                self.reset_connection_state()
                
                # Start health monitoring
                asyncio.create_task(self.health_monitor())
                
                # Start message listener
                asyncio.create_task(self._listen_messages())
                
                # Start connection health checker
                asyncio.create_task(self._connection_health_checker())
                
                logger.info("Wallex WebSocket connected successfully")
                return True
                
            except Exception as e:
                logger.error(f"Wallex connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(30, 2 ** attempt)
                    logger.info(f"Wallex retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.mark_connection_dead(f"Failed after {max_retries} attempts: {e}")
                    return False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs with response validation"""
        if not self.is_connected or not self.websocket:
            logger.error("Wallex: Cannot subscribe - not connected")
            return False
        
        successful_subscriptions = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Subscribe to orderbook updates (buyDepth and sellDepth)
                    subscribe_buy = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    subscribe_sell = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    
                    logger.info(f"Wallex subscribing to {symbol}...")
                    await self.websocket.send(json.dumps(subscribe_buy))
                    await asyncio.sleep(0.2)  # Wait for potential response
                    await self.websocket.send(json.dumps(subscribe_sell))
                    
                    # Track pending subscription
                    self.pending_subscriptions[symbol] = time.time()
                    
                    await asyncio.sleep(0.3)  # Wait for potential subscription data
                    
                except Exception as e:
                    logger.error(f"Wallex subscription error for {symbol}: {e}")
        
        # Wait a bit and check for actual data reception
        await asyncio.sleep(2)
        
        # Count actually working subscriptions (those receiving data)
        for symbol in pairs:
            if symbol in self.partial_data or any(symbol in channel for channel in self.subscribed_pairs):
                successful_subscriptions += 1
                self.subscribed_pairs.add(symbol)
                logger.info(f"Wallex confirmed subscription for {symbol}")
            else:
                logger.warning(f"Wallex no data received for {symbol}")
        
        logger.info(f"Wallex: Successfully subscribed to {successful_subscriptions}/{len(pairs)} pairs")
        return successful_subscriptions > 0

    async def _listen_messages(self):
        """Listen for WebSocket messages with enhanced error handling"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_connected and self.websocket:
            try:
                # Add timeout to detect silent disconnections
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=self.MESSAGE_TIMEOUT + 30  # Give extra time for first messages
                )
                
                consecutive_errors = 0
                self.update_message_time()
                
                # Parse message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Wallex: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                logger.warning(f"Wallex: No message received for {self.MESSAGE_TIMEOUT + 30} seconds - connection may be dead")
                self.mark_connection_dead("Message timeout")
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

    async def _process_message(self, data):
        """Process messages from Wallex WebSocket"""
        try:
            # Process depth data - Wallex format: [channel_name, data_array]
            if isinstance(data, list) and len(data) == 2:
                await self._process_depth_data(data)
            
            # Handle subscription confirmations
            elif isinstance(data, dict):
                if 'result' in data or 'success' in data:
                    logger.debug(f"Wallex subscription response: {data}")
                elif 'error' in data:
                    logger.warning(f"Wallex error: {data}")
                else:
                    logger.debug(f"Wallex unhandled message: {data}")
            
            else:
                logger.debug(f"Wallex unhandled message format: {data}")
                
        except Exception as e:
            logger.error(f"Wallex message processing error: {e}")

    async def _process_depth_data(self, data: list):
        """Process depth data from Wallex WebSocket"""
        try:
            channel_name = data[0]  # e.g., "USDTTMN@buyDepth" 
            orders_data = data[1]   # Array of order objects
            
            # Extract symbol and type from channel name
            if '@buyDepth' in channel_name:
                symbol = channel_name.replace('@buyDepth', '')
                order_type = 'buy'
            elif '@sellDepth' in channel_name:
                symbol = channel_name.replace('@sellDepth', '')
                order_type = 'sell'
            else:
                logger.debug(f"Wallex: Unknown channel format: {channel_name}")
                return
            
            # Mark subscription as successful when we receive data
            if symbol in self.pending_subscriptions:
                logger.info(f"Wallex: Confirmed subscription for {symbol} via data reception")
                del self.pending_subscriptions[symbol]
            
            if not orders_data:
                logger.debug(f"Wallex: Empty orders data for {channel_name}")
                return
            
            # Validate order data structure
            if not isinstance(orders_data, list) or not orders_data:
                logger.warning(f"Wallex: Invalid orders data format for {channel_name}: {orders_data}")
                return
            
            # Store the latest price from this channel
            if order_type == 'buy' and orders_data:
                # Best bid (highest buy price) is first in buy orders
                best_order = orders_data[0]
                if isinstance(best_order, dict) and 'price' in best_order and 'quantity' in best_order:
                    bid_price = Decimal(str(best_order['price']))
                    bid_volume = Decimal(str(best_order['quantity']))
                    
                    # Store bid data temporarily until we get ask data
                    await self._store_partial_data(symbol, bid_price=bid_price, bid_volume=bid_volume)
                else:
                    logger.warning(f"Wallex: Invalid buy order format: {best_order}")
                
            elif order_type == 'sell' and orders_data:
                # Best ask (lowest sell price) is first in sell orders
                best_order = orders_data[0]
                if isinstance(best_order, dict) and 'price' in best_order and 'quantity' in best_order:
                    ask_price = Decimal(str(best_order['price']))
                    ask_volume = Decimal(str(best_order['quantity']))
                    
                    # Store ask data temporarily until we get bid data
                    await self._store_partial_data(symbol, ask_price=ask_price, ask_volume=ask_volume)
                else:
                    logger.warning(f"Wallex: Invalid sell order format: {best_order}")
            
        except Exception as e:
            logger.error(f"Wallex depth data processing error: {e}")
    
    async def _store_partial_data(self, symbol: str, bid_price=None, ask_price=None, bid_volume=None, ask_volume=None):
        """Store partial order book data and save when both bid and ask are available"""
        try:
            if symbol not in self.partial_data:
                self.partial_data[symbol] = {}
            
            # Update partial data
            if bid_price is not None:
                self.partial_data[symbol]['bid_price'] = bid_price
                self.partial_data[symbol]['bid_volume'] = bid_volume
                self.partial_data[symbol]['bid_time'] = time.time()
            
            if ask_price is not None:
                self.partial_data[symbol]['ask_price'] = ask_price
                self.partial_data[symbol]['ask_volume'] = ask_volume
                self.partial_data[symbol]['ask_time'] = time.time()
            
            # Check if we have both bid and ask data
            data = self.partial_data[symbol]
            required_fields = ['bid_price', 'ask_price', 'bid_volume', 'ask_volume']
            
            if all(key in data for key in required_fields):
                # Check if data is not too old (max 30 seconds)
                current_time = time.time()
                bid_age = current_time - data.get('bid_time', 0)
                ask_age = current_time - data.get('ask_time', 0)
                
                if bid_age <= 30 and ask_age <= 30:
                    await self.save_price_data(
                        symbol,
                        data['bid_price'],
                        data['ask_price'],
                        data['bid_volume'],
                        data['ask_volume']
                    )
                    logger.debug(f"Wallex {symbol}: bid={data['bid_price']}({data['bid_volume']}), ask={data['ask_price']}({data['ask_volume']})")
                else:
                    logger.warning(f"Wallex {symbol}: Data too old - bid: {bid_age:.1f}s, ask: {ask_age:.1f}s")
            
        except Exception as e:
            logger.error(f"Wallex partial data storage error for {symbol}: {e}")

    async def _connection_health_checker(self):
        """Additional connection health checker for Wallex"""
        while self.is_connected and self.websocket:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.is_connected:
                    # Clean up old partial data
                    current_time = time.time()
                    symbols_to_clean = []
                    
                    for symbol, data in self.partial_data.items():
                        bid_time = data.get('bid_time', 0)
                        ask_time = data.get('ask_time', 0)
                        
                        if current_time - max(bid_time, ask_time) > 60:  # Data older than 1 minute
                            symbols_to_clean.append(symbol)
                    
                    for symbol in symbols_to_clean:
                        del self.partial_data[symbol]
                        logger.debug(f"Wallex: Cleaned old partial data for {symbol}")
                    
                    # Check WebSocket connection state
                    if hasattr(self.websocket, 'closed') and self.websocket.closed:
                        logger.warning("Wallex: WebSocket is closed but marked as connected")
                        self.mark_connection_dead("WebSocket closed")
                        break
                        
            except Exception as e:
                logger.error(f"Wallex connection health checker error: {e}")
                break

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_depth_data)"""
        return None

    async def disconnect(self):
        """Disconnect from Wallex"""
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
        logger.info("Wallex WebSocket disconnected")