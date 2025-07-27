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
        try:
            self.websocket = await websockets.connect(
                self.config['url'],
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            # Send connect message
            await self.websocket.send(json.dumps(self.config['connect_msg']))
            
            # Start tasks
            asyncio.create_task(self.listen_loop())
            asyncio.create_task(self.health_monitor())
            
            logger.info("Ramzinex connected")
            return True
            
        except Exception as e:
            logger.error(f"Ramzinex connect failed: {e}")
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to pairs"""
        if not self.is_connected:
            return False
            
        success_count = 0
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    msg = {
                        'subscribe': {'channel': f'{self.config["subscribe_prefix"]}{pair_id}'},
                        'id': 2 + len(self.subscribed_pairs)
                    }
                    
                    await self.websocket.send(json.dumps(msg))
                    self.subscribed_pairs.add(pair_id)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"Ramzinex subscribe error {pair_id}: {e}")
        
        logger.info(f"Ramzinex subscribed to {success_count}/{len(pairs)} pairs")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 Handle incoming messages"""
        try:
            data = json.loads(message)
            
            # Handle ping (empty JSON {})
            if isinstance(data, dict) and len(data) == 0:
                self.pong_count += 1
                await self.websocket.send('{}')  # Send pong
                logger.debug(f"Ramzinex PING->PONG #{self.pong_count}")
                
            # Handle push data
            elif isinstance(data, dict) and 'push' in data:
                await self._handle_push_data(data)
                
        except json.JSONDecodeError:
            pass  # Ignore non-JSON
        except Exception as e:
            logger.error(f"Ramzinex message error: {e}")

    async def _handle_push_data(self, data: dict):
        """📊 Process orderbook data"""
        try:
            push = data.get('push', {})
            channel = push.get('channel', '')
            pub_data = push.get('pub', {}).get('data')
            
            if not channel.startswith('orderbook:') or not pub_data:
                return
                
            pair_id = channel.split(':')[1]
            
            # Parse pub_data
            if isinstance(pub_data, str):
                pub_data = json.loads(pub_data)
                
            buys = pub_data.get('buys', [])
            sells = pub_data.get('sells', [])
            
            if buys and sells:
                # Check if we have mapping for this pair_id
                pair_info = get_ramzinex_pair_info(pair_id)
                if pair_info is None:
                    logger.debug(f"Ignoring unknown Ramzinex pair ID: {pair_id}")
                    return
                
                # Best bid: first in buys (highest price)
                bid_price = Decimal(str(buys[0][0]))
                bid_volume = Decimal(str(buys[0][1]))
                
                # Best ask: last in sells (lowest price)  
                ask_price = Decimal(str(sells[-1][0]))
                ask_volume = Decimal(str(sells[-1][1]))
                
                # Save with pair_id directly (will be converted in frontend)
                await self.save_price_data(pair_id, bid_price, ask_price, bid_volume, ask_volume)
                
        except Exception as e:
            logger.error(f"Ramzinex data error: {e}")

    async def disconnect(self):
        """🔌 Disconnect"""
        await super().disconnect()
        self.subscribed_pairs.clear()
        self.pong_count = 0