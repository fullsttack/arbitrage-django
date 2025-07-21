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
        try:
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            # Send connection message
            connect_msg = {'connect': {'name': 'python'}, 'id': 1}
            await self.websocket.send(json.dumps(connect_msg))
            
            self.is_connected = True
            
            # Start message listener
            asyncio.create_task(self._listen_messages())
            logger.info("Ramzinex WebSocket connected")
            
        except Exception as e:
            logger.error(f"Ramzinex WebSocket connection failed: {e}")
            self.is_connected = False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs (using pair IDs)"""
        if not self.is_connected:
            await self.connect()
        
        for pair_id in pairs:
            if pair_id not in self.subscribed_pairs:
                try:
                    # Subscribe to orderbook channel
                    subscribe_msg = {
                        'subscribe': {
                            'channel': f'orderbook-{pair_id}'
                        },
                        'id': len(self.subscribed_pairs) + 2
                    }
                    
                    await self.websocket.send(json.dumps(subscribe_msg))
                    self.subscribed_pairs.add(pair_id)
                    logger.info(f"Ramzinex subscribed to pair ID {pair_id}")
                    
                except Exception as e:
                    logger.error(f"Ramzinex subscription error for pair {pair_id}: {e}")

    async def _listen_messages(self):
        """Listen for WebSocket messages"""
        while self.is_connected and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Process orderbook data
                if 'channel' in data and 'data' in data:
                    await self._process_orderbook_data(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Ramzinex WebSocket connection closed")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Ramzinex message processing error: {e}")
                continue

    async def _process_orderbook_data(self, data: Dict[str, Any]):
        """Process orderbook data from Ramzinex WebSocket"""
        try:
            channel = data.get('channel', '')
            orderbook_data = data.get('data', {})
            
            # Extract pair ID from channel name (e.g., "orderbook-2")
            if not channel.startswith('orderbook-'):
                return
                
            pair_id = channel.replace('orderbook-', '')
            
            # Get buys and sells
            buys = orderbook_data.get('buys', [])
            sells = orderbook_data.get('sells', [])
            
            if buys and sells:
                # طبق مشخصات Ramzinex:
                # Sells (sells): lowest price in the last list element
                # Buys (buys): highest price in the first list element
                
                # Best bid (highest buy price)
                bid_price = Decimal(str(buys[0]['price']))
                bid_volume = Decimal(str(buys[0]['amount']))
                
                # Best ask (کمترین قیمت فروش)
                ask_price = Decimal(str(sells[-1]['price']))
                ask_volume = Decimal(str(sells[-1]['amount']))
                
                # Save price data with separate volumes
                await self.save_price_data(pair_id, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"Ramzinex pair {pair_id}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            
        except Exception as e:
            logger.error(f"Ramzinex orderbook data processing error: {e}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_orderbook_data)"""
        return None

    async def disconnect(self):
        """Disconnect from Ramzinex"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("Ramzinex WebSocket disconnected")