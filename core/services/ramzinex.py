import asyncio
import websockets
import json
import logging
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
        try:
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Send connection message
            connect_msg = {'connect': {'name': 'python'}, 'id': 1}
            await self.websocket.send(json.dumps(connect_msg))
            
            self.is_connected = True
            
            # Start message listener
            asyncio.create_task(self._listen_messages())
            logger.info("Ramzinex WebSocket connected")
            
        except Exception as e:
            logger.error(f"Ramzinex connection failed: {e}")
            self.is_connected = False

    async def subscribe_to_pairs(self, pairs: List[str]):
        if not self.is_connected:
            await self.connect()
            
        # Subscribe to all pairs
        for i, pair_id in enumerate(pairs):
            if pair_id not in self.subscribed_pairs:
                subscribe_msg = {
                    'subscribe': {
                        'channel': f'orderbook:{pair_id}',
                        'recover': True,
                        'delta': 'fossil'
                    },
                    'id': i + 2
                }
                
                await self.websocket.send(json.dumps(subscribe_msg))
                self.subscribed_pairs.add(pair_id)
                logger.info(f"Ramzinex subscribed to: {pair_id}")

    async def _listen_messages(self):
        try:
            async for message in self.websocket:
                if not message or message == '{}':
                    await self.websocket.send('{}')  # Pong
                    continue
                    
                data = json.loads(message)
                
                # Handle orderbook data
                if 'push' in data:
                    await self._process_orderbook_data(data['push'])
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Ramzinex WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Ramzinex WebSocket error: {e}")

    async def _process_orderbook_data(self, push_data: Dict[str, Any]):
        if 'orderbook:' in push_data.get('channel', ''):
            parsed_data = self.parse_price_data(push_data)
            if parsed_data:
                channel = push_data['channel']
                pair_id = channel.split(':')[1]
                
                await self.save_price_data(
                    symbol=pair_id,
                    bid_price=parsed_data['bid_price'],
                    ask_price=parsed_data['ask_price'],
                    volume=parsed_data['volume']
                )

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            pub_data = data.get('pub', {})
            
            # Handle JSON string data
            if isinstance(pub_data.get('data'), str):
                order_data = json.loads(pub_data['data'])
            else:
                order_data = pub_data.get('data', {})
            
            buys = order_data.get('buys', [])
            sells = order_data.get('sells', [])
            
            if not buys or not sells:
                return None
                
            # بیشترین قیمت خرید در اول buys
            # کمترین قیمت فروش در آخر sells
            bid_price = Decimal(str(buys[0][0]))
            ask_price = Decimal(str(sells[-1][0]))
            volume = Decimal(str(buys[0][1]))
            
            return {
                'bid_price': bid_price,
                'ask_price': ask_price,
                'volume': volume
            }
            
        except (KeyError, IndexError, ValueError, json.JSONDecodeError):
            return None

    async def disconnect(self):
        await super().disconnect()
        if self.websocket:
            await self.websocket.close()
            self.websocket = None