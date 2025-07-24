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
        
    async def connect(self):
        """Connect to LBank WebSocket with enhanced error handling"""
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
                
                # Simplified connection parameters - only use supported ones
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Handle ping manually
                    ping_timeout=None,
                    close_timeout=10
                )
                
                self.is_connected = True
                self.reset_connection_state()
                
                # Start health monitoring
                asyncio.create_task(self.health_monitor())
                
                # Start message listener
                asyncio.create_task(self._listen_messages())
                
                # Start ping handler for LBank
                asyncio.create_task(self._ping_handler())
                
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
                        "depth": "100"  # Official docs use "100", not "5"
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
                # Add timeout to detect silent disconnections
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=self.MESSAGE_TIMEOUT + 30  # Give extra time for market data
                )
                
                # Reset error counter on successful message
                consecutive_errors = 0
                self.update_message_time()
                
                # Parse and process message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"LBank: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                logger.warning(f"LBank: No message received for {self.MESSAGE_TIMEOUT + 30} seconds - connection may be dead")
                self.mark_connection_dead("Message timeout")
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

    async def _process_message(self, data: Dict[str, Any]):
        """Process different types of messages from LBank"""
        try:
            # Handle depth data
            if data.get('type') == 'depth' and 'depth' in data:
                await self._process_depth_data(data)
            
            # Handle pong responses
            elif data.get('action') == 'pong':
                self.update_ping_time()
                logger.debug(f"LBank pong received: {data.get('pong', 'unknown')}")
            
            # Handle server ping - Multiple formats possible
            elif data.get('action') == 'ping':
                await self._handle_server_ping(data)
            
            # Handle other ping formats
            elif 'ping' in data and data.get('action') != 'pong':
                await self._handle_server_ping(data)
            
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
        """Handle server ping in multiple possible formats"""
        try:
            ping_id = None
            
            # Format 1: {"action": "ping", "ping": "id"}
            if data.get('action') == 'ping' and 'ping' in data:
                ping_id = data['ping']
            
            # Format 2: {"ping": "id"}
            elif 'ping' in data and len(data) == 1:
                ping_id = data['ping']
            
            # Format 3: {"ping": "id", "action": "ping"}
            elif 'ping' in data:
                ping_id = data['ping']
            
            if ping_id:
                # Respond with pong
                pong_msg = {"action": "pong", "pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                self.update_ping_time()
                logger.debug(f"LBank responded to server ping: {ping_id}")
            else:
                logger.warning(f"LBank: Could not extract ping ID from: {data}")
                
        except Exception as e:
            logger.error(f"LBank ping handling error: {e}")

    async def _process_depth_data(self, data: Dict[str, Any]):
        """Process depth data from LBank WebSocket"""
        try:
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

    async def _ping_handler(self):
        """Enhanced ping handler for LBank"""
        ping_interval = 50  # Send ping every 50 seconds (LBank tolerance is 60s)
        
        while self.is_connected and self.websocket:
            try:
                await asyncio.sleep(ping_interval)
                
                if self.is_connected and self.websocket:
                    ping_msg = {
                        "action": "ping",
                        "ping": f"client-ping-{self.ping_counter}-{int(time.time())}"
                    }
                    
                    await self.websocket.send(json.dumps(ping_msg))
                    logger.debug(f"LBank ping sent: {self.ping_counter}")
                    self.ping_counter += 1
                    
                    # Check if we got a recent pong (LBank docs say 1 minute tolerance)
                    current_time = time.time()
                    if self.last_ping_time > 0:
                        ping_age = current_time - self.last_ping_time
                        if ping_age > 90:  # 90 seconds tolerance per LBank docs (1 minute + buffer)
                            logger.warning(f"LBank: No pong for {ping_age:.1f}s - connection may be dead")
                            self.mark_connection_dead("Ping timeout")
                            break
                            
            except Exception as e:
                logger.error(f"LBank ping error: {e}")
                self.mark_connection_dead(f"Ping error: {e}")
                break
    
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
        logger.info("LBank WebSocket disconnected")