import asyncio
import json
import logging
import websockets
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
        """Connect to LBank WebSocket"""
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
            logger.error(f"LBank WebSocket connection failed: {e}")
            self.is_connected = False

    async def subscribe_to_pairs(self, pairs: List[str]):
        """Subscribe to trading pairs"""
        if not self.is_connected:
            await self.connect()
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Subscribe to depth updates
                    subscribe_msg = {
                        "action": "subscribe",
                        "subscribe": "depth",
                        "pair": symbol,
                        "depth": 5
                    }
                    
                    await self.websocket.send(json.dumps(subscribe_msg))
                    self.subscribed_pairs.add(symbol)
                    logger.info(f"LBank subscribed to {symbol}")
                    
                except Exception as e:
                    logger.error(f"LBank subscription error for {symbol}: {e}")

    async def _listen_messages(self):
        """Listen for WebSocket messages"""
        while self.is_connected and self.websocket:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # Process depth data
                if data.get('type') == 'depth' and 'data' in data:
                    await self._process_depth_data(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("LBank WebSocket connection closed")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"LBank message processing error: {e}")
                continue

    async def _process_depth_data(self, data: Dict[str, Any]):
        """Process depth data from LBank WebSocket"""
        try:
            depth_data = data.get('data', {})
            symbol = data.get('pair', '')
            
            # Get best bid and ask
            asks = depth_data.get('asks', [])
            bids = depth_data.get('bids', [])
            
            if asks and bids and symbol:
                # Best ask (lowest sell price)  
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                
                # Best bid (highest buy price)
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                # Save price data with separate volumes
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                
                logger.debug(f"LBank {symbol}: bid={bid_price}({bid_volume}), ask={ask_price}({ask_volume})")
            
        except Exception as e:
            logger.error(f"LBank depth data processing error: {e}")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_depth_data)"""
        return None

    async def disconnect(self):
        """Disconnect from LBank"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("LBank WebSocket disconnected")