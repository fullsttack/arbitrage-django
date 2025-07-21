import asyncio
import json
import logging
import websockets
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

logger = logging.getLogger(__name__)

class WallexService(BaseExchangeService):
    def __init__(self):
        super().__init__('wallex')
        self.websocket_url = 'wss://api.wallex.ir/v1/ws'
        self.websocket = None
        self.subscribed_pairs = set()
        
    async def connect(self):
        """Connect to Wallex WebSocket"""
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
            logger.info("Wallex WebSocket connected")
            
        except Exception as e:
            logger.error(f"Wallex WebSocket connection failed: {e}")
            self.is_connected = False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs"""
        if not self.is_connected:
            await self.connect()
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Subscribe to orderbook updates
                    subscribe_msg = {
                        "method": "SUBSCRIBE",
                        "params": [f"{symbol.lower()}@depth"],
                        "id": len(self.subscribed_pairs) + 1
                    }
                    
                    await self.websocket.send(json.dumps(subscribe_msg))
                    self.subscribed_pairs.add(symbol)
                    logger.info(f"Wallex subscribed to {symbol}")
                    
                except Exception as e:
                    logger.error(f"Wallex subscription error for {symbol}: {e}")

    async def _listen_messages(self):
        """Listen for WebSocket messages"""
        while self.is_connected and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Process depth data
                if 'stream' in data and 'data' in data:
                    await self._process_depth_data(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Wallex WebSocket connection closed")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Wallex message processing error: {e}")
                continue

    async def _process_depth_data(self, data: Dict[str, Any]):
        """Process depth data from Wallex WebSocket"""
        try:
            stream = data.get('stream', '')
            depth_data = data.get('data', {})
            
            # Extract symbol from stream name (e.g., "btcusdt@depth")
            symbol = stream.replace('@depth', '').upper()
            
            # Get best bid and ask
            asks = depth_data.get('asks', [])
            bids = depth_data.get('bids', [])
            
            if asks and bids:
                # Best ask (کمترین قیمت فروش)
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                
                # Best bid (بیشترین قیمت خرید)
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                # Save price data with separate volumes
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"Wallex {symbol}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            
        except Exception as e:
            logger.error(f"Wallex depth data processing error: {e}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_depth_data)"""
        return None

    async def disconnect(self):
        """Disconnect from Wallex"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("Wallex WebSocket disconnected")