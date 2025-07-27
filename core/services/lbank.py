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
        
    async def connect(self) -> bool:
        """🔌 Simple connection"""
        try:
            self.websocket = await websockets.connect(
                self.config['url'],
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10,
                max_size=1024*1024
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            # Start tasks
            asyncio.create_task(self.listen_loop())
            asyncio.create_task(self.health_monitor())
            asyncio.create_task(self._client_ping_task())
            
            logger.info("LBank connected")
            return True
            
        except Exception as e:
            logger.error(f"LBank connect failed: {e}")
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to pairs"""
        if not self.is_connected:
            return False
            
        success_count = 0
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Create subscription message from config
                    msg = self.config['subscribe_format'].copy()
                    msg['pair'] = symbol
                    
                    await self.websocket.send(json.dumps(msg))
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"LBank subscribe error {symbol}: {e}")
        
        logger.info(f"LBank subscribed to {success_count}/{len(pairs)} pairs")
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
            logger.error(f"LBank message error: {e}")

    async def _handle_server_ping(self, data: dict):
        """🏓 Handle server ping"""
        try:
            ping_id = data.get('ping')
            if ping_id:
                # Send pong response
                pong_msg = {"action": "pong", "pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                logger.debug(f"LBank server PING->PONG: {ping_id}")
                
        except Exception as e:
            logger.error(f"LBank server ping error: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 Handle server pong (response to our ping)"""
        try:
            pong_id = data.get('pong')
            logger.debug(f"LBank server PONG received: {pong_id}")
            
        except Exception as e:
            logger.error(f"LBank pong error: {e}")

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
                
        except Exception as e:
            logger.error(f"LBank depth error: {e}")

    async def _client_ping_task(self):
        """🏓 Send periodic client pings"""
        while self.is_connected:
            try:
                await asyncio.sleep(self.config['ping_interval'])
                
                if not self.is_connected:
                    break
                    
                # Send client ping
                ping_id = f"client-{self.ping_counter}-{int(time.time())}"
                ping_msg = {"action": "ping", "ping": ping_id}
                
                await self.websocket.send(json.dumps(ping_msg))
                self.ping_counter += 1
                
                logger.debug(f"LBank client PING sent: {ping_id}")
                
            except Exception as e:
                logger.error(f"LBank client ping error: {e}")
                break

    async def disconnect(self):
        """🔌 Disconnect"""
        await super().disconnect()
        self.subscribed_pairs.clear()
        self.ping_counter = 1