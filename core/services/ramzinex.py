import asyncio
import json
import logging
import websockets
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
        
    async def connect(self):
        """Connect to Ramzinex WebSocket"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Ramzinex connection attempt {attempt + 1}/{max_retries}")
                
                # Disable built-in ping to handle manually
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Disable built-in ping
                    ping_timeout=None,
                    close_timeout=10
                )
                
                # Send connection message طبق داکیومنت Ramzinex
                connect_msg = {'connect': {'name': 'python'}, 'id': 1}
                logger.info(f"Ramzinex sending connect: {connect_msg}")
                await self.websocket.send(json.dumps(connect_msg))
                
                # Wait for connection response
                response = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                logger.info(f"Ramzinex connection response: {response}")
                
                # Parse response to verify successful connection
                try:
                    resp_data = json.loads(response)
                    if resp_data.get('id') == 1 and 'connect' in resp_data:
                        logger.info("Ramzinex connection confirmed")
                    else:
                        logger.warning(f"Unexpected connection response: {resp_data}")
                except:
                    logger.warning(f"Could not parse connection response: {response}")
                
                self.is_connected = True
                
                # Start message listener
                asyncio.create_task(self._listen_messages())
                # Start ping handler
                asyncio.create_task(self._ping_handler())
                logger.info("Ramzinex WebSocket connected")
                return
                
            except Exception as e:
                logger.error(f"Ramzinex connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.is_connected = False
                    logger.error("Ramzinex connection failed after all retries")

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs (using pair IDs)"""
        if not self.is_connected:
            await self.connect()
        
        # Wait a bit after connection before subscribing
        await asyncio.sleep(0.5)
        
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    # Subscribe to orderbook channel - طبق نمونه داکیومنت Ramzinex
                    subscribe_msg = {
                        'subscribe': {
                            'channel': f'orderbook:{pair_id}'
                        },
                        'id': len(self.subscribed_pairs) + 2
                    }
                    
                    logger.info(f"Ramzinex sending subscription for pair {pair_id}: {subscribe_msg}")
                    await self.websocket.send(json.dumps(subscribe_msg))
                    
                    # Wait for subscription response
                    await asyncio.sleep(0.2)
                    
                    self.subscribed_pairs.add(pair_id)
                    logger.info(f"Ramzinex subscribed to pair ID {pair_id}")
                    
                except Exception as e:
                    logger.error(f"Ramzinex subscription error for pair {pair_id}: {e}")
        
        logger.info(f"Ramzinex subscription completed for {len(self.subscribed_pairs)} pairs")

    async def _listen_messages(self):
        """Listen for WebSocket messages"""
        last_message_time = asyncio.get_event_loop().time()
        
        while self.is_connected and self.websocket:
            try:
                # Add timeout to detect silent disconnections
                message = await asyncio.wait_for(self.websocket.recv(), timeout=35)
                data = json.loads(message)
                
                last_message_time = asyncio.get_event_loop().time()
                logger.debug(f"Ramzinex received: {data}")
                
                # Process different message types
                if 'push' in data and 'channel' in data['push']:
                    await self._process_orderbook_data(data['push'])
                elif 'channel' in data and data['channel'].startswith('orderbook'):
                    # Direct channel data (alternative format)
                    await self._process_orderbook_data(data)
                elif data == {} or (isinstance(data, dict) and len(data) == 0):
                    # Ping message - send pong
                    await self.websocket.send(json.dumps({}))
                    logger.info("Ramzinex pong sent in response to server ping")
                elif 'subscribe' in data:
                    # Subscription response with potential data
                    logger.info(f"Ramzinex subscription response received for ID: {data.get('id')}")
                    
                    # Check if subscription response contains publications with data
                    subscribe_data = data.get('subscribe', {})
                    publications = subscribe_data.get('publications', [])
                    
                    for publication in publications:
                        if 'data' in publication:
                            try:
                                # Parse the data field which contains JSON
                                pub_data_str = publication['data']
                                pub_data = json.loads(pub_data_str)
                                
                                # Determine pair_id from subscription ID (2 -> 432, 3 -> 13, 4 -> 643)
                                sub_id = data.get('id')
                                if sub_id == 2:
                                    pair_id = '432'
                                elif sub_id == 3:
                                    pair_id = '13' 
                                elif sub_id == 4:
                                    pair_id = '643'
                                else:
                                    logger.warning(f"Unknown subscription ID: {sub_id}")
                                    continue
                                
                                # Process the orderbook data
                                await self._process_subscription_data(pair_id, pub_data)
                                
                            except Exception as e:
                                logger.error(f"Ramzinex error parsing subscription data: {e}")
                elif 'connect' in data:
                    # Connection response (already handled in connect method)
                    logger.debug(f"Ramzinex connect response: {data}")
                else:
                    logger.info(f"Ramzinex unhandled message: {data}")
                
            except asyncio.TimeoutError:
                logger.warning("Ramzinex no message received for 35 seconds - connection may be dead")
                self.is_connected = False
                break
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"Ramzinex WebSocket connection closed: {e}")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Ramzinex message processing error: {e}")
                # Don't continue on critical errors
                if "Connection is closed" in str(e) or "Connection lost" in str(e):
                    self.is_connected = False
                    break
                continue

    async def _process_subscription_data(self, pair_id: str, orderbook_data: Dict[str, Any]):
        """Process orderbook data from Ramzinex subscription"""
        try:
            # Get buys and sells
            buys = orderbook_data.get('buys', [])
            sells = orderbook_data.get('sells', [])
            
            logger.debug(f"Ramzinex pair {pair_id}: buys={len(buys)}, sells={len(sells)}")
            
            if buys and sells:
                # طبق مشخصات Ramzinex: format is array [price, volume, total, flag, null, ?, timestamp]
                # Sells (sells): lowest price in the last list element  
                # Buys (buys): highest price in the first list element
                
                # Best bid (highest buy price) - first in buys
                if isinstance(buys[0], list) and len(buys[0]) >= 2:
                    bid_price = Decimal(str(buys[0][0]))
                    bid_volume = Decimal(str(buys[0][1]))
                else:
                    logger.warning(f"Ramzinex invalid buys format for pair {pair_id}: {buys[0] if buys else 'None'}")
                    return
                
                # Best ask (کمترین قیمت فروش) - LAST in sells (طبق توضیح شما)
                if isinstance(sells[-1], list) and len(sells[-1]) >= 2:
                    ask_price = Decimal(str(sells[-1][0]))
                    ask_volume = Decimal(str(sells[-1][1]))
                else:
                    logger.warning(f"Ramzinex invalid sells format for pair {pair_id}: {sells[-1] if sells else 'None'}")
                    return
                
                # Save price data with separate volumes
                await self.save_price_data(pair_id, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.info(f"Ramzinex pair {pair_id}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            else:
                logger.warning(f"Ramzinex pair {pair_id}: No buys or sells data")
            
        except Exception as e:
            logger.error(f"Ramzinex subscription data processing error for pair {pair_id}: {e}", exc_info=True)
    
    async def _process_orderbook_data(self, data: Dict[str, Any]):
        """Process orderbook data from Ramzinex WebSocket (push format)"""
        try:
            channel = data.get('channel', '')
            
            # Check if this is push format
            if 'pub' in data:
                pub_data = data.get('pub', {})
                logger.debug(f"Ramzinex processing push channel: {channel}")
                
                # Parse the data field which might be compressed or encoded
                data_str = pub_data.get('data', '')
                if isinstance(data_str, str):
                    try:
                        orderbook_data = json.loads(data_str)
                        logger.debug(f"Ramzinex: Parsed push orderbook data keys: {list(orderbook_data.keys()) if orderbook_data else 'None'}")
                    except:
                        logger.debug(f"Ramzinex push data not JSON, possibly compressed: {data_str[:100]}")
                        return
                else:
                    orderbook_data = data_str
                    logger.debug(f"Ramzinex: Direct push orderbook data type: {type(orderbook_data)}")
            else:
                # Direct format - data contains orderbook directly
                orderbook_data = data
                logger.debug(f"Ramzinex: Direct channel format, data keys: {list(data.keys())}")
            
            # Extract pair ID from channel name (e.g., "orderbook:2" or "orderbook-2")
            if channel.startswith('orderbook:'):
                pair_id = channel.replace('orderbook:', '')
            elif channel.startswith('orderbook-'):
                pair_id = channel.replace('orderbook-', '')
            else:
                logger.debug(f"Ramzinex: Channel {channel} doesn't match orderbook pattern")
                return
            
            # Process using the new method
            await self._process_subscription_data(pair_id, orderbook_data)
            
        except Exception as e:
            logger.error(f"Ramzinex orderbook push data processing error: {e}", exc_info=True)

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_orderbook_data)"""
        return None

    async def _ping_handler(self):
        """Monitor connection health - server sends ping, we respond with pong"""
        # According to Ramzinex docs: Server sends ping, client responds with pong
        # Monitor if we're getting regular pings from server
        logger.info("Ramzinex ping handler started - monitoring server pings")
        
        while self.is_connected and self.websocket:
            await asyncio.sleep(30)  # Check every 30 seconds
            if self.is_connected:
                logger.debug("Ramzinex connection health check - still connected")
    
    async def disconnect(self):
        """Disconnect from Ramzinex"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("Ramzinex WebSocket disconnected")