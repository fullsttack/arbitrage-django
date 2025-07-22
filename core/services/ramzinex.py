import asyncio
import json
import logging
import websockets
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

logger = logging.getLogger(__name__)

class RamzinexService(BaseExchangeService):
    def __init__(self):
        super().__init__('ramzinex')
        self.websocket_url = 'wss://websocket.ramzinex.com/websocket'
        self.websocket = None
        self.subscribed_pairs = set()
        self.connection_id = None
        self.subscription_id_counter = 2
        self.subscription_map = {}  # Map subscription IDs to pair IDs
        
        # Centrifugo specific settings
        self.CENTRIFUGO_TIMEOUT = 25  # Server will disconnect after 25 seconds without pong
        self.PONG_SAFETY_MARGIN = 20  # Send pong every 20 seconds to be safe
        
    async def connect(self):
        """Connect to Ramzinex WebSocket with Centrifugo protocol"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info(f"Ramzinex connection attempt {attempt + 1}/{max_retries}")
                
                # Close existing connection if any
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                # Simplified connection parameters - only use supported ones
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Handle ping manually for Centrifugo
                    ping_timeout=None,
                    close_timeout=10
                )
                
                # Send connection message according to Centrifugo protocol
                connect_msg = {
                    'connect': {'name': 'python-arbitrage'},
                    'id': 1
                }
                
                logger.info(f"Ramzinex sending connect: {connect_msg}")
                await self.websocket.send(json.dumps(connect_msg))
                
                # Wait for connection response with timeout
                try:
                    response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
                    logger.info(f"Ramzinex connection response: {response}")
                    
                    resp_data = json.loads(response)
                    if resp_data.get('id') == 1 and 'connect' in resp_data:
                        connect_result = resp_data.get('connect', {})
                        self.connection_id = connect_result.get('client')
                        logger.info(f"Ramzinex connection confirmed, client ID: {self.connection_id}")
                        
                        self.is_connected = True
                        self.reset_connection_state()
                        
                        # Start health monitoring
                        asyncio.create_task(self.health_monitor())
                        
                        # Start message listener
                        asyncio.create_task(self._listen_messages())
                        
                        # Start ping handler for Centrifugo
                        asyncio.create_task(self._ping_handler())
                        
                        logger.info("Ramzinex WebSocket connected successfully")
                        return True
                    else:
                        logger.error(f"Ramzinex: Unexpected connection response: {resp_data}")
                        continue
                        
                except asyncio.TimeoutError:
                    logger.error("Ramzinex: Connection response timeout")
                    continue
                except json.JSONDecodeError as e:
                    logger.error(f"Ramzinex: Invalid connection response: {e}")
                    continue
                
            except Exception as e:
                logger.error(f"Ramzinex connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = min(30, 2 ** attempt)
                    logger.info(f"Ramzinex retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.mark_connection_dead(f"Failed after {max_retries} attempts: {e}")
                    return False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs using Centrifugo protocol"""
        if not self.is_connected or not self.websocket:
            logger.error("Ramzinex: Cannot subscribe - not connected")
            return False
        
        # Wait a bit after connection before subscribing
        await asyncio.sleep(1)
        
        successful_subscriptions = 0
        
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    self.subscription_id_counter += 1
                    subscription_id = self.subscription_id_counter
                    
                    # Subscribe to orderbook channel
                    subscribe_msg = {
                        'subscribe': {
                            'channel': f'orderbook:{pair_id}'
                        },
                        'id': subscription_id
                    }
                    
                    logger.info(f"Ramzinex sending subscription for pair {pair_id}: {subscribe_msg}")
                    await self.websocket.send(json.dumps(subscribe_msg))
                    
                    # Store mapping for later reference
                    self.subscription_map[subscription_id] = pair_id
                    
                    # Wait for subscription response
                    await asyncio.sleep(0.5)
                    
                    self.subscribed_pairs.add(pair_id)
                    successful_subscriptions += 1
                    logger.info(f"Ramzinex subscribed to pair ID {pair_id} with subscription ID {subscription_id}")
                    
                except Exception as e:
                    logger.error(f"Ramzinex subscription error for pair {pair_id}: {e}")
        
        logger.info(f"Ramzinex: Successfully subscribed to {successful_subscriptions}/{len(pairs)} pairs")
        return successful_subscriptions > 0

    async def _listen_messages(self):
        """Listen for WebSocket messages with Centrifugo protocol handling"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.is_connected and self.websocket:
            try:
                # Centrifugo timeout is 25 seconds, so we use 30 seconds timeout
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=30
                )
                
                consecutive_errors = 0
                self.update_message_time()
                
                # Handle empty ping message from server
                if message.strip() == '{}':
                    await self._handle_server_ping()
                    continue
                
                # Parse JSON message
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Ramzinex: Invalid JSON received: {message[:100]}...")
                    continue
                
                await self._process_message(data)
                
            except asyncio.TimeoutError:
                logger.warning("Ramzinex: No message received for 30 seconds - connection may be dead")
                self.mark_connection_dead("Message timeout")
                break
                
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Ramzinex WebSocket connection closed: {e}")
                self.mark_connection_dead(f"Connection closed: {e}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Ramzinex message processing error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Ramzinex: Too many consecutive errors, marking connection as dead")
                    self.mark_connection_dead(f"Too many errors: {e}")
                    break
                
                await asyncio.sleep(1)

    async def _process_message(self, data: Dict[str, Any]):
        """Process different types of Centrifugo messages"""
        try:
            # Handle push messages (real-time data)
            if 'push' in data and 'channel' in data['push']:
                await self._process_push_data(data['push'])
            
            # Handle subscription responses
            elif 'subscribe' in data:
                await self._handle_subscription_response(data)
            
            # Handle connect responses (already handled in connect method)
            elif 'connect' in data:
                logger.debug(f"Ramzinex connect response: {data}")
            
            # Handle disconnect messages
            elif 'disconnect' in data:
                logger.warning(f"Ramzinex server disconnect: {data}")
                self.mark_connection_dead(f"Server disconnect: {data}")
            
            # Handle error messages
            elif 'error' in data:
                logger.error(f"Ramzinex error: {data}")
            
            else:
                logger.debug(f"Ramzinex unhandled message: {data}")
                
        except Exception as e:
            logger.error(f"Ramzinex message processing error: {e}")

    async def _handle_server_ping(self):
        """Handle server ping (empty JSON object)"""
        try:
            # Respond with pong (empty JSON object)
            await self.websocket.send('{}')
            self.update_ping_time()
            logger.debug("Ramzinex pong sent in response to server ping")
        except Exception as e:
            logger.error(f"Ramzinex ping response error: {e}")

    async def _handle_subscription_response(self, data: Dict[str, Any]):
        """Handle subscription response with potential data"""
        try:
            subscribe_data = data.get('subscribe', {})
            sub_id = data.get('id')
            
            logger.info(f"Ramzinex subscription response received for ID: {sub_id}")
            
            # Check if subscription response contains publications with data
            publications = subscribe_data.get('publications', [])
            
            for publication in publications:
                if 'data' in publication:
                    try:
                        # Parse the data field which contains JSON
                        pub_data_str = publication['data']
                        pub_data = json.loads(pub_data_str)
                        
                        # Get pair_id from subscription mapping
                        pair_id = self.subscription_map.get(sub_id)
                        if pair_id:
                            await self._process_orderbook_data(pair_id, pub_data)
                        else:
                            logger.warning(f"Ramzinex: Unknown subscription ID: {sub_id}")
                            
                    except Exception as e:
                        logger.error(f"Ramzinex error parsing subscription data: {e}")
                        
        except Exception as e:
            logger.error(f"Ramzinex subscription response handling error: {e}")

    async def _process_push_data(self, push_data: Dict[str, Any]):
        """Process push data from Centrifugo"""
        try:
            channel = push_data.get('channel', '')
            pub_data = push_data.get('pub', {})
            
            # Extract pair ID from channel name (e.g., "orderbook:432")
            if channel.startswith('orderbook:'):
                pair_id = channel.replace('orderbook:', '')
                
                # Parse the data field
                data_str = pub_data.get('data', '')
                if isinstance(data_str, str):
                    try:
                        orderbook_data = json.loads(data_str)
                        await self._process_orderbook_data(pair_id, orderbook_data)
                    except:
                        logger.debug(f"Ramzinex push data not JSON, possibly compressed: {data_str[:100]}")
                else:
                    await self._process_orderbook_data(pair_id, data_str)
                    
        except Exception as e:
            logger.error(f"Ramzinex push data processing error: {e}")

    async def _process_orderbook_data(self, pair_id: str, orderbook_data: Dict[str, Any]):
        """Process orderbook data from Ramzinex"""
        try:
            # Get buys and sells
            buys = orderbook_data.get('buys', [])
            sells = orderbook_data.get('sells', [])
            
            logger.debug(f"Ramzinex pair {pair_id}: buys={len(buys)}, sells={len(sells)}")
            
            if buys and sells:
                # According to Ramzinex docs: format is [price, volume, total, flag, null, ?, timestamp]
                # Buys: highest price in first element
                # Sells: lowest price in last element
                
                # Best bid (highest buy price) - first in buys
                if isinstance(buys[0], list) and len(buys[0]) >= 2:
                    bid_price = Decimal(str(buys[0][0]))
                    bid_volume = Decimal(str(buys[0][1]))
                else:
                    logger.warning(f"Ramzinex invalid buys format for pair {pair_id}: {buys[0] if buys else 'None'}")
                    return
                
                # Best ask (lowest sell price) - LAST in sells
                if isinstance(sells[-1], list) and len(sells[-1]) >= 2:
                    ask_price = Decimal(str(sells[-1][0]))
                    ask_volume = Decimal(str(sells[-1][1]))
                else:
                    logger.warning(f"Ramzinex invalid sells format for pair {pair_id}: {sells[-1] if sells else 'None'}")
                    return
                
                # Save price data
                await self.save_price_data(pair_id, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"Ramzinex pair {pair_id}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            else:
                logger.warning(f"Ramzinex pair {pair_id}: No buys or sells data")
            
        except Exception as e:
            logger.error(f"Ramzinex orderbook data processing error for pair {pair_id}: {e}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_orderbook_data)"""
        return None

    async def _ping_handler(self):
        """Monitor connection health - server sends ping, we respond with pong"""
        logger.info("Ramzinex ping handler started - monitoring server pings")
        
        while self.is_connected and self.websocket:
            try:
                await asyncio.sleep(self.PONG_SAFETY_MARGIN)
                
                if self.is_connected:
                    # Check if we received a ping recently
                    current_time = time.time()
                    if self.last_ping_time > 0:
                        ping_age = current_time - self.last_ping_time
                        if ping_age > self.CENTRIFUGO_TIMEOUT:
                            logger.warning(f"Ramzinex: No ping from server for {ping_age:.1f}s - connection may be dead")
                            self.mark_connection_dead("Server ping timeout")
                            break
                    
                    logger.debug("Ramzinex connection health check - still connected")
                    
            except Exception as e:
                logger.error(f"Ramzinex ping handler error: {e}")
                break
    
    async def disconnect(self):
        """Disconnect from Ramzinex"""
        await super().disconnect()
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.websocket = None
        self.subscribed_pairs.clear()
        self.subscription_map.clear()
        self.connection_id = None
        logger.info("Ramzinex WebSocket disconnected")