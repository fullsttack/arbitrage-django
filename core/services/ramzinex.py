import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logging.error("websockets not available, Ramzinex service disabled")

logger = logging.getLogger(__name__)

class RamzinexService(BaseExchangeService):
    def __init__(self):
        super().__init__('ramzinex')
        
        # Initialize attributes
        self.websocket_url = 'wss://websocket.ramzinex.com/websocket'
        self.websocket = None
        self.subscribed_pairs = set()
        self.pair_symbol_map = {}  # Map pair IDs to symbol formats
        
        # Message tracking
        self.message_count = 0
        self.ping_count = 0
        self.data_count = 0
        
        # Connection activity tracking
        self.last_activity_time = 0
        self.last_data_receive_time = 0
        
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets not available - Ramzinex service disabled")
        
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
        """اتصال به Ramzinex با raw websocket"""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("Ramzinex: websockets not available")
            return False
            
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
                
                # Connect with raw websocket
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=None,  # Manual ping handling
                    ping_timeout=None,
                    close_timeout=10
                )
                
                self.is_connected = True
                self.reset_connection_state()
                self.last_activity_time = time.time()
                
                logger.info("Ramzinex: Connected successfully")
                
                # Send required connect message
                await self._send_connect_message()
                
                # Build pair-symbol mapping after connection
                await self._build_pair_symbol_mapping()
                
                # Start message handling
                asyncio.create_task(self._listen_messages())
                asyncio.create_task(self._health_monitor())
                
                logger.info("Ramzinex WebSocket connected successfully with ping/pong working")
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

    async def _send_connect_message(self):
        """ارسال پیام connect اجباری"""
        try:
            connect_msg = {
                'connect': {'name': 'js'},
                'id': 1
            }
            
            await self.websocket.send(json.dumps(connect_msg))
            logger.info("Ramzinex: Connect message sent successfully")
            
        except Exception as e:
            logger.error(f"Ramzinex: Failed to send connect message: {e}")

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs"""
        if not self.is_connected:
            logger.error("Ramzinex: Cannot subscribe - not connected")
            return False
        
        # Wait a bit after connection before subscribing
        await asyncio.sleep(1)
        
        successful_subscriptions = 0
        
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    subscribe_msg = {
                        'subscribe': {'channel': f'orderbook:{pair_id}'},
                        'id': 2 + len(self.subscribed_pairs)
                    }
                    
                    await self.websocket.send(json.dumps(subscribe_msg))
                    self.subscribed_pairs.add(pair_id)
                    successful_subscriptions += 1
                    
                    # Track activity
                    self.last_activity_time = time.time()
                    
                    logger.info(f"Ramzinex sent subscription for pair ID {pair_id}")
                    
                    # Small delay between subscriptions
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Ramzinex subscription error for pair {pair_id}: {e}")
        
        # Wait for subscription confirmations
        await asyncio.sleep(3)
        
        logger.info(f"Ramzinex: Successfully subscribed to {successful_subscriptions}/{len(pairs)} pairs")
        return successful_subscriptions > 0

    async def _listen_messages(self):
        """گوش دادن به پیام‌ها"""
        try:
            while self.is_connected:
                message = await self.websocket.recv()
                self.message_count += 1
                self.last_activity_time = time.time()
                self.update_message_time()
                
                try:
                    data = json.loads(message)
                    
                    # Handle ping (empty JSON)
                    if isinstance(data, dict) and len(data) == 0:
                        self.ping_count += 1
                        logger.debug(f"Ramzinex: PING #{self.ping_count} received - sending PONG")
                        
                        # Send pong
                        await self.websocket.send('{}')
                        
                    elif isinstance(data, dict):
                        # Handle other messages
                        if 'connect' in data:
                            logger.info(f"Ramzinex: Connect response received")
                        elif 'push' in data:
                            # This is actual data
                            await self._handle_push_data(data)
                        elif 'subscribe' in data:
                            logger.debug(f"Ramzinex: Subscription confirmed")
                    
                except json.JSONDecodeError:
                    logger.warning(f"Ramzinex: Non-JSON message: {message[:50]}")
                    
        except Exception as e:
            logger.error(f"Ramzinex: Listen error: {e}")
            self.is_connected = False
            self.mark_connection_dead(f"Listen error: {e}")

    async def _handle_push_data(self, data: Dict[str, Any]):
        """Handle push data from subscription"""
        try:
            push = data.get('push', {})
            channel = push.get('channel', '')
            pub_data = push.get('pub', {}).get('data')
            
            if channel.startswith('orderbook:') and pub_data:
                # Extract pair_id from channel
                pair_id = channel.split(':')[1]
                
                # Parse the data
                if isinstance(pub_data, dict):
                    await self._process_orderbook_data(pair_id, pub_data)
                elif isinstance(pub_data, str):
                    try:
                        parsed_data = json.loads(pub_data)
                        await self._process_orderbook_data(pair_id, parsed_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Ramzinex: Invalid JSON in data for {pair_id}")
                        
                self.data_count += 1
                self.last_data_receive_time = time.time()
                
        except Exception as e:
            logger.error(f"Ramzinex: Error handling push data: {e}")

    async def _process_orderbook_data(self, pair_id: str, orderbook_data: Dict[str, Any]):
        """Process orderbook data from Ramzinex"""
        try:
            # Track data processing
            self.last_data_receive_time = time.time()
            self.last_activity_time = time.time()
            
            # Get buys and sells arrays
            buys = orderbook_data.get('buys', [])
            sells = orderbook_data.get('sells', [])
            
            logger.debug(f"Ramzinex pair {pair_id}: buys={len(buys)}, sells={len(sells)}")
            
            if buys and sells:
                # Format: [price, volume, total_value, boolean, null, count, timestamp]
                # Best bid (highest buy price) - first in buys array (sorted descending)
                if isinstance(buys[0], list) and len(buys[0]) >= 2:
                    bid_price = Decimal(str(buys[0][0]))    # First element is price
                    bid_volume = Decimal(str(buys[0][1]))   # Second element is volume
                else:
                    logger.warning(f"Ramzinex invalid buys format for pair {pair_id}: {buys[0] if buys else 'None'}")
                    return
                
                # Best ask (lowest sell price) - LAST in sells array (طبق مستندات ramzinex)
                if isinstance(sells[-1], list) and len(sells[-1]) >= 2:
                    ask_price = Decimal(str(sells[-1][0]))   # First element is price  
                    ask_volume = Decimal(str(sells[-1][1]))  # Second element is volume
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

    async def _health_monitor(self):
        """Health monitor برای Ramzinex"""
        while self.is_connected:
            try:
                current_time = time.time()
                
                # Check if connection is alive (should get ping every 25s)
                if self.last_activity_time > 0:
                    time_since_activity = current_time - self.last_activity_time
                    
                    if time_since_activity > 45:  # 25s + 20s margin
                        logger.error(f"Ramzinex: No activity for {time_since_activity:.1f}s - disconnecting")
                        self.mark_connection_dead("No activity - ping timeout")
                        break
                
                # Check message reception
                if self.last_message_time > 0:
                    time_since_message = current_time - self.last_message_time
                    
                    if time_since_message > 40:  # Be a bit lenient
                        logger.warning(f"Ramzinex: No messages for {time_since_message:.1f}s")
                        if time_since_message > 60:  # Really disconnect after 60s
                            self.mark_connection_dead("No messages")
                            break
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Ramzinex health monitor error: {e}")
                self.mark_connection_dead(f"Health monitor error: {e}")
                break

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_orderbook_data)"""
        return None

    async def disconnect(self):
        """Disconnect from Ramzinex"""
        await super().disconnect()
        
        self.is_connected = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        self.websocket = None
        self.subscribed_pairs.clear()
        self.pair_symbol_map.clear()
        logger.info("Ramzinex disconnected")