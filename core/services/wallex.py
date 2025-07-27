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
            self.connection_start_time = time.time()
            
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
        """📡 Subscribe to pairs (buyDepth and sellDepth)"""
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
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    logger.debug(f"{self.exchange_name}: Subscribing to {symbol}")
                    
                    # Subscribe to buy depth
                    buy_msg = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    await self.websocket.send(json.dumps(buy_msg))
                    logger.debug(f"{self.exchange_name}: Sent buyDepth subscription for {symbol}")
                    
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to sell depth
                    sell_msg = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    await self.websocket.send(json.dumps(sell_msg))
                    logger.debug(f"{self.exchange_name}: Sent sellDepth subscription for {symbol}")
                    
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {symbol}: {e}")
            else:
                logger.debug(f"{self.exchange_name}: Skipping {symbol} - already subscribed")
        
        logger.info(f"{self.exchange_name}: Subscription result: {success_count}/{len(pairs)}")
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
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_ping(self, data: dict):
        """🏓 Handle server ping"""
        try:
            ping_id = data.get('ping')
            logger.debug(f"{self.exchange_name}: Received PING {ping_id}")
            
            if ping_id:
                # Check pong limit
                if self.pong_count >= self.config['max_pongs']:
                    logger.warning(f"{self.exchange_name}: Max pongs reached ({self.pong_count})")
                    self.mark_dead("Max pongs reached")
                    return
                    
                # Send pong
                pong_msg = {"pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                
                self.pong_count += 1
                logger.debug(f"{self.exchange_name}: Sent PONG {ping_id} (count: {self.pong_count}/{self.config['max_pongs']})")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Ping handling error: {e}")

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
            logger.error(f"{self.exchange_name}: Depth data processing error: {e}")

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
                logger.debug(f"{self.exchange_name}: Updated bid for {symbol}: {price}")
            else:  # sell
                data['ask_price'] = price
                data['ask_volume'] = volume
                data['ask_time'] = current_time
                logger.debug(f"{self.exchange_name}: Updated ask for {symbol}: {price}")
            
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
                    logger.debug(f"{self.exchange_name}: Saved price data for {symbol}")
                    
        except Exception as e:
            logger.error(f"{self.exchange_name}: Store order data error for {symbol}: {e}")

    def is_healthy(self) -> bool:
        """🔍 Wallex-specific health check"""
        if not super().is_healthy():
            return False
            
        current_time = time.time()
        
        # Check connection time limit (30 minutes)
        if self.connection_start_time > 0:
            connection_age = current_time - self.connection_start_time
            logger.debug(f"{self.exchange_name}: Connection age: {connection_age:.1f}s")
            
            if connection_age > self.config['max_connection_time']:
                logger.warning(f"{self.exchange_name}: Connection age limit reached ({connection_age:.1f}s)")
                return False
                
        # Check pong count
        if self.pong_count >= self.config['max_pongs']:
            logger.warning(f"{self.exchange_name}: Pong count limit reached ({self.pong_count})")
            return False
            
        return True

    async def reset_state(self):
        """🔄 Reset Wallex-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting Wallex-specific state")
        
        # Clear subscriptions
        self.subscribed_pairs.clear()
        
        # Reset counters
        self.pong_count = 0
        self.connection_start_time = 0
        
        # Clear partial data
        self.partial_data.clear()
        
        logger.debug(f"{self.exchange_name}: Wallex state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting Wallex disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # Wallex-specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: Wallex disconnect completed")