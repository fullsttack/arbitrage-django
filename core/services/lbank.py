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

class LBankService(BaseExchangeService):
    """🚀 Fast and Simple LBank Service"""
    
    def __init__(self):
        config = get_config('lbank')
        super().__init__('lbank', config)
        self.subscribed_pairs = set()
        self.ping_counter = 1
        self.client_ping_task = None
        
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
                close_timeout=10,
                max_size=1024*1024
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            logger.info(f"{self.exchange_name}: Connected successfully")
            
            # Start background tasks and track them
            listen_task = asyncio.create_task(self.listen_loop())
            health_task = asyncio.create_task(self.health_monitor())
            ping_task = asyncio.create_task(self._client_ping_task())
            
            self.background_tasks = [listen_task, health_task, ping_task]
            self.client_ping_task = ping_task  # Keep reference for specific handling
            
            logger.debug(f"{self.exchange_name}: Background tasks started")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Connect failed: {e}")
            await self.reset_state()
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to pairs"""
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
                    
                    # Create subscription message from config
                    msg = self.config['subscribe_format'].copy()
                    msg['pair'] = symbol
                    
                    await self.websocket.send(json.dumps(msg))
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    logger.debug(f"{self.exchange_name}: Subscribed to {symbol}")
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
            if isinstance(data, dict) and data.get('action') == 'ping':
                await self._handle_server_ping(data)
                
            # Handle server pong (response to our ping)
            elif isinstance(data, dict) and data.get('action') == 'pong':
                await self._handle_server_pong(data)
                
            # Handle depth data
            elif data.get('type') == 'depth' and 'depth' in data:
                await self._handle_depth_data(data)
                
        except json.JSONDecodeError:
            pass  # Ignore non-JSON
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_server_ping(self, data: dict):
        """🏓 Handle server ping"""
        try:
            ping_id = data.get('ping')
            logger.debug(f"{self.exchange_name}: Received server PING {ping_id}")
            
            if ping_id:
                # Send pong response
                pong_msg = {"action": "pong", "pong": ping_id}
                
                if self.websocket and self.is_connected:
                    await self.websocket.send(json.dumps(pong_msg))
                    logger.debug(f"{self.exchange_name}: Sent server PONG {ping_id}")
                else:
                    logger.warning(f"{self.exchange_name}: Cannot send PONG - no websocket or disconnected")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Server ping handling error: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 Handle server pong (response to our ping)"""
        try:
            pong_id = data.get('pong')
            logger.debug(f"{self.exchange_name}: Received server PONG {pong_id}")
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Server pong handling error: {e}")

    async def _handle_depth_data(self, data: dict):
        """📊 Process depth data"""
        try:
            depth = data.get('depth', {})
            symbol = data.get('pair', '')
            
            if not symbol:
                return
                
            asks = depth.get('asks', [])
            bids = depth.get('bids', [])
            
            if asks and bids:
                # Best prices
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                logger.debug(f"{self.exchange_name}: Processed depth data for {symbol}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Depth data processing error: {e}")

    async def _client_ping_task(self):
        """🏓 Send periodic client pings"""
        logger.debug(f"{self.exchange_name}: Starting client ping task")
        
        while self.is_connected:
            try:
                await asyncio.sleep(self.config['ping_interval'])
                
                if not self.is_connected:
                    logger.debug(f"{self.exchange_name}: Ping task stopping - disconnected")
                    break
                
                if not self.websocket:
                    logger.warning(f"{self.exchange_name}: Ping task stopping - no websocket")
                    break
                    
                # Send client ping
                ping_id = f"client-{self.ping_counter}-{int(time.time())}"
                ping_msg = {"action": "ping", "ping": ping_id}
                
                await self.websocket.send(json.dumps(ping_msg))
                self.ping_counter += 1
                
                logger.debug(f"{self.exchange_name}: Client ping sent #{self.ping_counter}: {ping_id}")
                
            except Exception as e:
                logger.error(f"{self.exchange_name}: Client ping error: {e}")
                break
        
        logger.debug(f"{self.exchange_name}: Client ping task terminated")

    async def reset_state(self):
        """🔄 Reset LBank-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting LBank-specific state")
        
        # Clear subscriptions
        self.subscribed_pairs.clear()
        
        # Reset ping counter
        self.ping_counter = 1
        
        # Clear ping task reference
        self.client_ping_task = None
        
        logger.debug(f"{self.exchange_name}: LBank state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting LBank disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # LBank-specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: LBank disconnect completed")