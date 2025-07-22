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
        self.websocket_url = 'wss://api.wallex.ir/ws'
        self.websocket = None
        self.subscribed_pairs = set()
        self.partial_data = {}  # Store partial orderbook data
        
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
                    # Subscribe to orderbook updates (buyDepth and sellDepth)
                    subscribe_buy = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    subscribe_sell = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    
                    await self.websocket.send(json.dumps(subscribe_buy))
                    await self.websocket.send(json.dumps(subscribe_sell))
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
                
                logger.debug(f"Wallex received: {data}")
                
                # Process depth data - Wallex format: [channel_name, data_array]
                if isinstance(data, list) and len(data) == 2:
                    await self._process_depth_data(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Wallex WebSocket connection closed")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"Wallex message processing error: {e}")
                continue

    async def _process_depth_data(self, data: list):
        """Process depth data from Wallex WebSocket"""
        try:
            channel_name = data[0]  # e.g., "USDTTMN@buyDepth" 
            orders_data = data[1]   # Array of order objects
            
            # Extract symbol and type from channel name
            if '@buyDepth' in channel_name:
                symbol = channel_name.replace('@buyDepth', '')
                order_type = 'buy'
            elif '@sellDepth' in channel_name:
                symbol = channel_name.replace('@sellDepth', '')
                order_type = 'sell'
            else:
                return
            
            if not orders_data:
                return
                
            # Store the latest price from this channel
            # buyDepth contains buy orders (bids), sellDepth contains sell orders (asks)
            if order_type == 'buy' and orders_data:
                # Best bid (highest buy price) is first in buy orders
                best_order = orders_data[0]
                bid_price = Decimal(str(best_order['price']))
                bid_volume = Decimal(str(best_order['quantity']))
                
                # Store bid data temporarily until we get ask data
                await self._store_partial_data(symbol, bid_price=bid_price, bid_volume=bid_volume)
                
            elif order_type == 'sell' and orders_data:
                # Best ask (lowest sell price) is first in sell orders
                best_order = orders_data[0]
                ask_price = Decimal(str(best_order['price']))
                ask_volume = Decimal(str(best_order['quantity']))
                
                # Store ask data temporarily until we get bid data
                await self._store_partial_data(symbol, ask_price=ask_price, ask_volume=ask_volume)
            
        except Exception as e:
            logger.error(f"Wallex depth data processing error: {e}")
    
    async def _store_partial_data(self, symbol: str, bid_price=None, ask_price=None, bid_volume=None, ask_volume=None):
        """Store partial order book data and save when both bid and ask are available"""
        if symbol not in self.partial_data:
            self.partial_data[symbol] = {}
        
        # Update partial data
        if bid_price is not None:
            self.partial_data[symbol]['bid_price'] = bid_price
            self.partial_data[symbol]['bid_volume'] = bid_volume
        
        if ask_price is not None:
            self.partial_data[symbol]['ask_price'] = ask_price
            self.partial_data[symbol]['ask_volume'] = ask_volume
        
        # Check if we have both bid and ask data
        data = self.partial_data[symbol]
        if all(key in data for key in ['bid_price', 'ask_price', 'bid_volume', 'ask_volume']):
            await self.save_price_data(
                symbol,
                data['bid_price'],
                data['ask_price'],
                data['bid_volume'],
                data['ask_volume']
            )
            logger.debug(f"Wallex {symbol}: bid={data['bid_price']}({data['bid_volume']}), ask={data['ask_price']}({data['ask_volume']})")

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse price data (handled in _process_depth_data)"""
        return None

    async def disconnect(self):
        """Disconnect from Wallex"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
        logger.info("Wallex WebSocket disconnected")