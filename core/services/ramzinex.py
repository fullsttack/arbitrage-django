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
    """🚀 Fast and Simple Ramzinex Service"""
    
    def __init__(self):
        config = get_config('ramzinex')
        super().__init__('ramzinex', config)
        self.subscribed_pairs = set()
        self.pong_count = 0
        
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
            await self.websocket.send(json.dumps(connect_msg))
            logger.debug(f"{self.exchange_name}: Connect message sent")
            
            logger.info(f"{self.exchange_name}: Connected successfully")
            
            # Start background tasks and track them
            listen_task = asyncio.create_task(self.listen_loop())
            health_task = asyncio.create_task(self.health_monitor())
            
            self.background_tasks = [listen_task, health_task]
            
            logger.debug(f"{self.exchange_name}: Background tasks started")
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
                        logger.debug(f"{self.exchange_name}: Pair {pair_id} -> {pair_info['symbol']}")
                    else:
                        logger.warning(f"{self.exchange_name}: No mapping for pair_id {pair_id}, skipping")
                        continue
                    
                    msg = {
                        'subscribe': {'channel': f'{self.config["subscribe_prefix"]}{pair_id}'},
                        'id': 2 + len(self.subscribed_pairs)
                    }
                    
                    await self.websocket.send(json.dumps(msg))
                    self.subscribed_pairs.add(pair_id)
                    success_count += 1
                    
                    logger.debug(f"{self.exchange_name}: Subscribed to {pair_id}")
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {pair_id}: {e}")
            else:
                logger.debug(f"{self.exchange_name}: Skipping {pair_id} - already subscribed")
        
        logger.info(f"{self.exchange_name}: Subscription result: {success_count}/{len(pairs)}")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 Handle incoming messages"""
        try:
            data = json.loads(message)
            
            # Handle ping (empty JSON {})
            if isinstance(data, dict) and len(data) == 0:
                await self._handle_ping()
                
            # Handle push data
            elif isinstance(data, dict) and 'push' in data:
                await self._handle_push_data(data)
                
        except json.JSONDecodeError:
            pass  # Ignore non-JSON
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_ping(self):
        """🏓 Handle server ping (empty JSON)"""
        try:
            self.pong_count += 1
            logger.debug(f"{self.exchange_name}: Received PING (empty JSON) #{self.pong_count}")
            
            if self.websocket and self.is_connected:
                await self.websocket.send('{}')  # Send pong (empty JSON)
                logger.debug(f"{self.exchange_name}: Sent PONG (empty JSON) #{self.pong_count}")
            else:
                logger.warning(f"{self.exchange_name}: Cannot send PONG - no websocket or disconnected")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Ping handling error: {e}")

    async def _handle_push_data(self, data: dict):
        """📊 Process orderbook data"""
        try:
            push = data.get('push', {})
            channel = push.get('channel', '')
            pub_data = push.get('pub', {}).get('data')
            
            if not channel.startswith('orderbook:') or not pub_data:
                return
                
            pair_id = channel.split(':')[1]
            logger.debug(f"{self.exchange_name}: Processing orderbook data for pair_id {pair_id}")
            
            # Parse pub_data
            if isinstance(pub_data, str):
                pub_data = json.loads(pub_data)
                
            buys = pub_data.get('buys', [])
            sells = pub_data.get('sells', [])
            
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
                
                # Save with pair_id directly (will be converted in frontend)
                await self.save_price_data(pair_id, bid_price, ask_price, bid_volume, ask_volume)
                logger.debug(f"{self.exchange_name}: Saved price data for {pair_id} ({pair_info['symbol']})")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Push data processing error: {e}")

    async def reset_state(self):
        """🔄 Reset Ramzinex-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting Ramzinex-specific state")
        
        # Clear subscriptions
        self.subscribed_pairs.clear()
        
        # Reset pong counter
        self.pong_count = 0
        
        logger.debug(f"{self.exchange_name}: Ramzinex state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting Ramzinex disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # Ramzinex-specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: Ramzinex disconnect completed")