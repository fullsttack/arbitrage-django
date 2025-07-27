import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import List
import websockets
from .base import BaseExchangeService
from .config import get_config

logger = logging.getLogger(__name__)

class WallexService(BaseExchangeService):
    """🚀 Fast and Simple Wallex Service"""
    
    def __init__(self):
        config = get_config('wallex')
        super().__init__('wallex', config)
        self.subscribed_pairs = set()
        self.pong_count = 0
        self.connection_start_time = 0
        self.partial_data = {}  # Store bid/ask separately
        
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
            self.connection_start_time = time.time()
            
            # Start tasks
            asyncio.create_task(self.listen_loop())
            asyncio.create_task(self.health_monitor())
            
            logger.info("Wallex connected")
            return True
            
        except Exception as e:
            logger.error(f"Wallex connect failed: {e}")
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to pairs (buyDepth and sellDepth)"""
        if not self.is_connected:
            return False
            
        success_count = 0
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Subscribe to buy depth
                    buy_msg = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    await self.websocket.send(json.dumps(buy_msg))
                    
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to sell depth
                    sell_msg = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    await self.websocket.send(json.dumps(sell_msg))
                    
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"Wallex subscribe error {symbol}: {e}")
        
        logger.info(f"Wallex subscribed to {success_count}/{len(pairs)} pairs")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 Handle incoming messages"""
        try:
            data = json.loads(message)
            
            # Handle server ping
            if isinstance(data, dict) and 'ping' in data:
                await self._handle_ping(data)
                
            # Handle depth data [channel_name, data_array]
            elif isinstance(data, list) and len(data) == 2:
                await self._handle_depth_data(data)
                
        except json.JSONDecodeError:
            pass  # Ignore non-JSON
        except Exception as e:
            logger.error(f"Wallex message error: {e}")

    async def _handle_ping(self, data: dict):
        """🏓 Handle server ping"""
        try:
            ping_id = data.get('ping')
            if ping_id:
                # Check pong limit
                if self.pong_count >= self.config['max_pongs']:
                    self.mark_dead("Max pongs reached")
                    return
                    
                # Send pong
                pong_msg = {"pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                
                self.pong_count += 1
                logger.debug(f"Wallex PING->PONG #{self.pong_count}/100")
                
        except Exception as e:
            logger.error(f"Wallex ping error: {e}")

    async def _handle_depth_data(self, data: list):
        """📊 Process depth data"""
        try:
            channel_name = data[0]
            orders_data = data[1]
            
            if '@buyDepth' in channel_name:
                symbol = channel_name.replace('@buyDepth', '')
                await self._store_order_data(symbol, 'buy', orders_data)
                
            elif '@sellDepth' in channel_name:
                symbol = channel_name.replace('@sellDepth', '')
                await self._store_order_data(symbol, 'sell', orders_data)
                
        except Exception as e:
            logger.error(f"Wallex depth error: {e}")

    async def _store_order_data(self, symbol: str, order_type: str, orders_data: list):
        """💾 Store order data and save when complete"""
        try:
            if not orders_data:
                return
                
            # Get best order
            best_order = orders_data[0]
            if not isinstance(best_order, dict):
                return
                
            price = Decimal(str(best_order.get('price', 0)))
            volume = Decimal(str(best_order.get('quantity', 0)))
            
            if price <= 0 or volume <= 0:
                return
            
            # Store partial data
            if symbol not in self.partial_data:
                self.partial_data[symbol] = {}
                
            current_time = time.time()
            data = self.partial_data[symbol]
            
            if order_type == 'buy':
                data['bid_price'] = price
                data['bid_volume'] = volume
                data['bid_time'] = current_time
            else:  # sell
                data['ask_price'] = price
                data['ask_volume'] = volume
                data['ask_time'] = current_time
            
            # Save when we have both bid and ask
            if all(k in data for k in ['bid_price', 'ask_price', 'bid_volume', 'ask_volume']):
                last_save = data.get('last_save_time', 0)
                
                # Throttle saves (every 2 seconds max)
                if current_time - last_save > 2:
                    await self.save_price_data(
                        symbol, 
                        data['bid_price'], 
                        data['ask_price'],
                        data['bid_volume'], 
                        data['ask_volume']
                    )
                    data['last_save_time'] = current_time
                    
        except Exception as e:
            logger.error(f"Wallex store error {symbol}: {e}")

    def is_healthy(self) -> bool:
        """🔍 Wallex-specific health check"""
        if not super().is_healthy():
            return False
            
        current_time = time.time()
        
        # Check connection time limit (30 minutes)
        if self.connection_start_time > 0:
            connection_age = current_time - self.connection_start_time
            if connection_age > self.config['max_connection_time']:
                return False
                
        # Check pong count
        if self.pong_count >= self.config['max_pongs']:
            return False
            
        return True

    async def disconnect(self):
        """🔌 Disconnect"""
        await super().disconnect()
        self.subscribed_pairs.clear()
        self.partial_data.clear()
        self.pong_count = 0
        self.connection_start_time = 0