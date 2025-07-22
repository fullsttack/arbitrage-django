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
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"LBank connection attempt {attempt + 1}/{max_retries}")
                
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=30,  # Increase ping interval
                    ping_timeout=15,
                    close_timeout=10
                )
                
                self.is_connected = True
                
                # Start message listener
                asyncio.create_task(self._listen_messages())
                # Start ping handler for LBank
                asyncio.create_task(self._ping_handler())
                logger.info("LBank WebSocket connected")
                return
                
            except Exception as e:
                logger.error(f"LBank connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.is_connected = False
                    logger.error("LBank connection failed after all retries")

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
                if data.get('type') == 'depth' and 'depth' in data:
                    await self._process_depth_data(data)
                elif data.get('action') == 'pong':
                    logger.debug("LBank pong received")
                elif data.get('action') == 'ping':
                    # Respond to server ping
                    pong_msg = {"action": "pong", "pong": data.get('ping')}
                    await self.websocket.send(json.dumps(pong_msg))
                    logger.debug("LBank pong sent")
                
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
            depth_data = data.get('depth', {})
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

    async def _ping_handler(self):
        """Handle ping/pong mechanism for LBank"""
        ping_id = 1
        while self.is_connected and self.websocket:
            try:
                await asyncio.sleep(25)  # Send ping every 25 seconds
                if self.is_connected and self.websocket:
                    ping_msg = {
                        "action": "ping",
                        "ping": f"lbank-ping-{ping_id}"
                    }
                    await self.websocket.send(json.dumps(ping_msg))
                    logger.debug(f"LBank ping sent: {ping_id}")
                    ping_id += 1
            except Exception as e:
                logger.error(f"LBank ping error: {e}")
                break
    
    async def disconnect(self):
        """Disconnect from LBank"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("LBank WebSocket disconnected")