import asyncio
import websockets
import json
import logging
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

    async def connect(self):
        try:
            self.websocket = await websockets.connect(
                self.websocket_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            self.is_connected = True
            
            # Start message listener
            asyncio.create_task(self._listen_messages())
            logger.info("LBank WebSocket connected")
            
        except Exception as e:
            logger.error(f"LBank connection failed: {e}")
            self.is_connected = False

    async def subscribe_to_pairs(self, pairs: List[str]):
        if not self.is_connected:
            await self.connect()
            
        # Subscribe to all pairs concurrently
        subscribe_tasks = []
        for pair in pairs:
            if pair not in self.subscribed_pairs:
                subscribe_tasks.append(self._subscribe_pair(pair))
        
        if subscribe_tasks:
            await asyncio.gather(*subscribe_tasks)

    async def _subscribe_pair(self, pair: str):
        subscribe_msg = {
            "action": "subscribe",
            "subscribe": "depth",
            "depth": "1",
            "pair": pair
        }
        
        await self.websocket.send(json.dumps(subscribe_msg))
        self.subscribed_pairs.add(pair)
        logger.info(f"LBank subscribed to: {pair}")

    async def _listen_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # Handle ping/pong
                if data.get('action') == 'ping':
                    pong_msg = {"action": "pong", "pong": data.get('ping')}
                    await self.websocket.send(json.dumps(pong_msg))
                    continue
                
                # Handle depth data
                if data.get('type') == 'depth':
                    await self._process_depth_data(data)
                        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("LBank WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"LBank WebSocket error: {e}")

    async def _process_depth_data(self, data: Dict[str, Any]):
        parsed_data = self.parse_price_data(data)
        if parsed_data:
            pair = data.get('pair', '')
            await self.save_price_data(
                symbol=pair,
                bid_price=parsed_data['bid_price'],
                ask_price=parsed_data['ask_price'],
                volume=parsed_data['volume']
            )

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            depth_data = data.get('depth', {})
            asks = depth_data.get('asks', [])
            bids = depth_data.get('bids', [])
            
            if not asks or not bids:
                return None
                
            ask_price = Decimal(str(asks[0][0]))
            bid_price = Decimal(str(bids[0][0]))
            volume = Decimal(str(asks[0][1]))
            
            return {
                'bid_price': bid_price,
                'ask_price': ask_price,
                'volume': volume
            }
            
        except (KeyError, IndexError, ValueError):
            return None

    async def disconnect(self):
        await super().disconnect()
        if self.websocket:
            await self.websocket.close()
            self.websocket = None