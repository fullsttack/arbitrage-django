import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import List
import websockets
from .base import BaseExchangeService
from .config import get_config, get_ramzinex_display_symbol, get_ramzinex_pair_info, get_ramzinex_arbitrage_symbol

logger = logging.getLogger(__name__)

class RamzinexService(BaseExchangeService):
    """🚀 Fast and Simple Ramzinex Service with Enhanced Debugging"""
    
    def __init__(self):
        config = get_config('ramzinex')
        super().__init__('ramzinex', config)
        self.subscribed_pairs = set()
        self.pong_count = 0
        self.ping_count = 0
        
    async def connect(self) -> bool:
        """🔌 Simple connection"""
        logger.info(f"{self.exchange_name}: Attempting connection to {self.config['url']}")
        
        try:
            # Reset state before connecting
            await self.reset_state()
            
            self.websocket = await websockets.connect(
                self.config['url'],
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            # Send connect message
            connect_msg = self.config['connect_msg']
            connect_json = json.dumps(connect_msg)
            await self.websocket.send(connect_json)
            logger.info(f"{self.exchange_name}: Connect message sent: {connect_json}")
            
            logger.info(f"{self.exchange_name}: Connected successfully")
            
            # Start background tasks and track them
            listen_task = asyncio.create_task(self.listen_loop())
            health_task = asyncio.create_task(self.health_monitor())
            status_task = asyncio.create_task(self._status_monitor())
            
            self.background_tasks = [listen_task, health_task, status_task]
            
            logger.debug(f"{self.exchange_name}: Background tasks started: {len(self.background_tasks)}")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Connect failed: {e}")
            await self.reset_state()
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to pairs"""
        logger.info(f"{self.exchange_name}: Starting subscription for {len(pairs)} pairs")
        logger.debug(f"{self.exchange_name}: Current subscribed pairs: {self.subscribed_pairs}")
        logger.debug(f"{self.exchange_name}: Pairs to subscribe: {pairs}")
        
        if not self.is_connected:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - not connected")
            return False
            
        if not self.websocket:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - no websocket")
            return False
            
        success_count = 0
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    logger.debug(f"{self.exchange_name}: Subscribing to pair_id {pair_id}")
                    
                    # Check if we have mapping for this pair_id
                    pair_info = get_ramzinex_pair_info(pair_id)
                    if pair_info:
                        logger.debug(f"{self.exchange_name}: Pair {pair_id} -> {pair_info['symbol']} ({pair_info['name']})")
                    else:
                        logger.warning(f"{self.exchange_name}: No mapping for pair_id {pair_id}, skipping")
                        continue
                    
                    msg = {
                        'subscribe': {'channel': f'{self.config["subscribe_prefix"]}{pair_id}'},
                        'id': 2 + len(self.subscribed_pairs)
                    }
                    
                    msg_json = json.dumps(msg)
                    await self.websocket.send(msg_json)
                    self.subscribed_pairs.add(pair_id)
                    success_count += 1
                    
                    logger.debug(f"{self.exchange_name}: Subscribed to {pair_id} with message: {msg_json}")
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {pair_id}: {e}")
            else:
                logger.debug(f"{self.exchange_name}: Skipping {pair_id} - already subscribed")
        
        logger.info(f"{self.exchange_name}: Subscription result: {success_count}/{len(pairs)}")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 Handle incoming messages with enhanced debugging"""
        try:
            # First, let's see if it's JSON
            try:
                data = json.loads(message)
                logger.debug(f"{self.exchange_name}: JSON MESSAGE TYPE: {type(data)}")
                
                if isinstance(data, dict):
                    keys = list(data.keys())
                    logger.debug(f"{self.exchange_name}: JSON DICT KEYS: {keys}")
                    
                    # Check for specific keys
                    if 'push' in data:
                        logger.debug(f"{self.exchange_name}: PUSH MESSAGE detected")
                    elif len(data) == 0:
                        logger.debug(f"{self.exchange_name}: EMPTY JSON detected (likely ping)")
                    else:
                        logger.debug(f"{self.exchange_name}: OTHER DICT MESSAGE: {data}")
                        
                else:
                    logger.debug(f"{self.exchange_name}: JSON NON-DICT: {type(data)} - {data}")
                    
            except json.JSONDecodeError:
                logger.warning(f"{self.exchange_name}: NON-JSON MESSAGE: {message[:100]}{'...' if len(message) > 100 else ''}")
                return
            
            # Handle ping (empty JSON {})
            if isinstance(data, dict) and len(data) == 0:
                await self._handle_ping()
                
            # Handle push data
            elif isinstance(data, dict) and 'push' in data:
                await self._handle_push_data(data)
                
            # Handle connection response
            elif isinstance(data, dict) and 'connect' in data:
                logger.info(f"{self.exchange_name}: Connection response: {data}")
                
            # Handle subscription response
            elif isinstance(data, dict) and 'subscribe' in data:
                logger.info(f"{self.exchange_name}: Subscription response: {data}")
                
            # Handle other messages
            elif isinstance(data, dict):
                logger.debug(f"{self.exchange_name}: UNHANDLED DICT MESSAGE: {data}")
                
            else:
                logger.warning(f"{self.exchange_name}: UNKNOWN MESSAGE FORMAT: {type(data)} - {data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_ping(self):
        """🏓 Handle server ping (empty JSON) with detailed logging"""
        try:
            self.ping_count += 1
            logger.debug(f"{self.exchange_name}: 🏓 RECEIVED PING #{self.ping_count} (empty JSON)")
            
            if self.websocket and self.is_connected:
                await self.websocket.send('{}')  # Send pong (empty JSON)
                self.pong_count += 1
                logger.debug(f"{self.exchange_name}: 🏓 SENT PONG #{self.pong_count} (empty JSON)")
            else:
                logger.error(f"{self.exchange_name}: Cannot send PONG - no websocket or disconnected")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Ping handling error: {e}")

    async def _handle_push_data(self, data: dict):
        """📊 Process orderbook data with enhanced debugging"""
        try:
            push = data.get('push', {})
            channel = push.get('channel', '')
            pub_data = push.get('pub', {}).get('data')
            
            logger.debug(f"{self.exchange_name}: PUSH DATA - Channel: {channel}")
            
            if not channel.startswith('orderbook:'):
                logger.debug(f"{self.exchange_name}: Non-orderbook push data: {channel}")
                return
                
            if not pub_data:
                logger.warning(f"{self.exchange_name}: Push data without pub.data: {push}")
                return
                
            pair_id = channel.split(':')[1]
            logger.debug(f"{self.exchange_name}: Processing orderbook data for pair_id {pair_id}")
            
            # Parse pub_data
            if isinstance(pub_data, str):
                try:
                    pub_data = json.loads(pub_data)
                    logger.debug(f"{self.exchange_name}: Parsed pub_data for {pair_id}")
                except json.JSONDecodeError as e:
                    logger.error(f"{self.exchange_name}: Failed to parse pub_data: {e}")
                    return
                    
            buys = pub_data.get('buys', [])
            sells = pub_data.get('sells', [])
            
            logger.debug(f"{self.exchange_name}: Orderbook for {pair_id} - buys: {len(buys)}, sells: {len(sells)}")
            
            if buys and sells:
                # Check if we have mapping for this pair_id
                pair_info = get_ramzinex_pair_info(pair_id)
                if pair_info is None:
                    logger.debug(f"{self.exchange_name}: Ignoring unknown pair ID: {pair_id}")
                    return
                
                # Best bid: first in buys (highest price)
                bid_price = Decimal(str(buys[0][0]))
                bid_volume = Decimal(str(buys[0][1]))
                
                # Best ask: last in sells (lowest price)  
                ask_price = Decimal(str(sells[-1][0]))
                ask_volume = Decimal(str(sells[-1][1]))
                
                logger.debug(f"{self.exchange_name}: Best prices for {pair_id} ({pair_info['symbol']}) - "
                           f"bid: {bid_price}@{bid_volume}, ask: {ask_price}@{ask_volume}")
                
                # Save with pair_id directly (will be converted in frontend)
                await self.save_price_data(pair_id, bid_price, ask_price, bid_volume, ask_volume)
                logger.debug(f"{self.exchange_name}: 💾 Saved price data for {pair_id} ({pair_info['symbol']})")
                
            else:
                logger.warning(f"{self.exchange_name}: Empty buys or sells for {pair_id}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Push data processing error: {e}")

    async def _status_monitor(self):
        """📊 Status monitor with detailed reporting"""
        logger.info(f"{self.exchange_name}: 📊 Status monitor started")
        
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                
                current_time = time.time()
                time_since_data = current_time - self.last_data_time if self.last_data_time > 0 else float('inf')
                
                logger.info(f"{self.exchange_name}: 📊 RAMZINEX Status Report:")
                logger.info(f"  🔗 Endpoint: {self.config['url']}")
                logger.info(f"  ⏱️  Time since last data: {time_since_data:.1f}s")
                logger.info(f"  📝 Messages processed: {self.message_count}")
                logger.info(f"  🏓 Server pings received: {self.ping_count}")
                logger.info(f"  🏓 Client pongs sent: {self.pong_count}")
                logger.info(f"  📡 Subscribed pairs: {len(self.subscribed_pairs)}")
                
                # Data flow status
                if time_since_data < 30:
                    logger.info(f"{self.exchange_name}: ✅ Data flow healthy")
                elif time_since_data < 60:
                    logger.warning(f"{self.exchange_name}: ⚠️ Data flow slow")
                else:
                    logger.error(f"{self.exchange_name}: ❌ No data for {time_since_data:.1f}s")
                
        except asyncio.CancelledError:
            logger.info(f"{self.exchange_name}: Status monitor canceled")
        except Exception as e:
            logger.error(f"{self.exchange_name}: Status monitor error: {e}")

    def is_healthy(self) -> bool:
        """🔍 Ramzinex health check with ping/pong stats"""
        if not super().is_healthy():
            return False
            
        # Log ping/pong stats
        logger.debug(f"{self.exchange_name}: Health check - pings received: {self.ping_count}, pongs sent: {self.pong_count}")
        
        return True

    async def reset_state(self):
        """🔄 Reset Ramzinex-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting Ramzinex-specific state")
        
        # Clear subscriptions
        logger.debug(f"{self.exchange_name}: Clearing {len(self.subscribed_pairs)} subscribed pairs")
        self.subscribed_pairs.clear()
        
        # Reset ping/pong counters
        logger.debug(f"{self.exchange_name}: Resetting counters - pings: {self.ping_count}, pongs: {self.pong_count}")
        self.pong_count = 0
        self.ping_count = 0
        
        logger.debug(f"{self.exchange_name}: Ramzinex state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting Ramzinex disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # Ramzinex-specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: Ramzinex disconnect completed")