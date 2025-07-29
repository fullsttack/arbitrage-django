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
    """🚀 Fast and Simple LBank Service with Enhanced Debugging"""
    
    def __init__(self):
        config = get_config('lbank')
        super().__init__('lbank', config)
        self.subscribed_pairs = set()
        self.ping_counter = 1
        self.client_ping_task = None
        self.server_ping_count = 0
        self.server_pong_count = 0
        self.client_ping_count = 0
        self.client_pong_received_count = 0
        
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
            status_task = asyncio.create_task(self._status_monitor())
            
            self.background_tasks = [listen_task, health_task, ping_task, status_task]
            self.client_ping_task = ping_task  # Keep reference for specific handling
            
            logger.debug(f"{self.exchange_name}: Background tasks started: {len(self.background_tasks)}")
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
                    
                    msg_json = json.dumps(msg)
                    await self.websocket.send(msg_json)
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    logger.debug(f"{self.exchange_name}: Subscribed to {symbol} with message: {msg_json}")
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {symbol}: {e}")
            else:
                logger.debug(f"{self.exchange_name}: Skipping {symbol} - already subscribed")
        
        logger.info(f"{self.exchange_name}: Subscription result: {success_count}/{len(pairs)}")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 Handle incoming messages with enhanced debugging"""
        try:
            # First, let's see if it's JSON
            try:
                data = json.loads(message)
                logger.debug(f"{self.exchange_name}: JSON MESSAGE TYPE: {type(data)}")
                
                if isinstance(data, dict):
                    action = data.get('action')
                    msg_type = data.get('type')
                    logger.debug(f"{self.exchange_name}: JSON DICT - action: {action}, type: {msg_type}, keys: {list(data.keys())}")
                else:
                    logger.debug(f"{self.exchange_name}: JSON NON-DICT: {type(data)} - {data}")
                    
            except json.JSONDecodeError:
                logger.warning(f"{self.exchange_name}: NON-JSON MESSAGE: {message[:100]}{'...' if len(message) > 100 else ''}")
                return
            
            # Handle server ping
            if isinstance(data, dict) and data.get('action') == 'ping':
                await self._handle_server_ping(data)
                
            # Handle server pong (response to our ping)
            elif isinstance(data, dict) and data.get('action') == 'pong':
                await self._handle_server_pong(data)
                
            # Handle depth data
            elif data.get('type') == 'depth' and 'depth' in data:
                await self._handle_depth_data(data)
                
            # Handle other message types
            elif isinstance(data, dict):
                msg_type = data.get('type', 'unknown')
                action = data.get('action', 'unknown')
                logger.debug(f"{self.exchange_name}: UNHANDLED MESSAGE - type: {msg_type}, action: {action}")
                
            else:
                logger.warning(f"{self.exchange_name}: UNKNOWN MESSAGE FORMAT: {type(data)} - {data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_server_ping(self, data: dict):
        """🏓 Handle server ping with detailed logging"""
        try:
            ping_id = data.get('ping')
            self.server_ping_count += 1
            
            logger.debug(f"{self.exchange_name}: 🏓 RECEIVED SERVER PING #{self.server_ping_count}: {ping_id}")
            logger.debug(f"{self.exchange_name}: Full server ping message: {data}")
            
            if ping_id:
                # Send pong response
                pong_msg = {"action": "pong", "pong": ping_id}
                
                if self.websocket and self.is_connected:
                    pong_json = json.dumps(pong_msg)
                    await self.websocket.send(pong_json)
                    self.server_pong_count += 1
                    
                    logger.debug(f"{self.exchange_name}: 🏓 SENT SERVER PONG #{self.server_pong_count}: {ping_id}")
                    logger.debug(f"{self.exchange_name}: Server pong message sent: {pong_json}")
                else:
                    logger.error(f"{self.exchange_name}: Cannot send server PONG - no websocket or disconnected")
                    
            else:
                logger.warning(f"{self.exchange_name}: Server ping message without ping ID: {data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Server ping handling error: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 Handle server pong (response to our ping) with detailed logging"""
        try:
            pong_id = data.get('pong')
            self.client_pong_received_count += 1
            
            logger.debug(f"{self.exchange_name}: 🏓 RECEIVED SERVER PONG #{self.client_pong_received_count}: {pong_id}")
            logger.debug(f"{self.exchange_name}: Full server pong message: {data}")
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Server pong handling error: {e}")

    async def _handle_depth_data(self, data: dict):
        """📊 Process depth data with debugging"""
        try:
            depth = data.get('depth', {})
            symbol = data.get('pair', '')
            
            logger.debug(f"{self.exchange_name}: DEPTH DATA for {symbol}")
            
            if not symbol:
                logger.warning(f"{self.exchange_name}: Depth data without symbol: {data}")
                return
                
            asks = depth.get('asks', [])
            bids = depth.get('bids', [])
            
            logger.debug(f"{self.exchange_name}: Depth for {symbol} - asks: {len(asks)}, bids: {len(bids)}")
            
            if asks and bids:
                # Best prices
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                logger.debug(f"{self.exchange_name}: Best prices for {symbol} - bid: {bid_price}@{bid_volume}, ask: {ask_price}@{ask_volume}")
                
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                logger.debug(f"{self.exchange_name}: 💾 Saved price data for {symbol}")
                
            else:
                logger.warning(f"{self.exchange_name}: Empty asks or bids for {symbol}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Depth data processing error: {e}")

    async def _client_ping_task(self):
        """🏓 Send periodic client pings with enhanced logging"""
        logger.info(f"{self.exchange_name}: Starting client ping task")
        
        try:
            while self.is_connected and self._listen_task_running:
                try:
                    await asyncio.sleep(self.config['ping_interval'])
                    
                    if not self.is_connected:
                        logger.debug(f"{self.exchange_name}: Client ping task stopping - disconnected")
                        break
                    
                    if not self.websocket:
                        logger.warning(f"{self.exchange_name}: Client ping task stopping - no websocket")
                        break
                        
                    # Send client ping
                    ping_id = f"client-{self.ping_counter}-{int(time.time())}"
                    ping_msg = {"action": "ping", "ping": ping_id}
                    
                    ping_json = json.dumps(ping_msg)
                    await self.websocket.send(ping_json)
                    self.ping_counter += 1
                    self.client_ping_count += 1
                    
                    logger.debug(f"{self.exchange_name}: 🏓 SENT CLIENT PING #{self.client_ping_count}: {ping_id}")
                    logger.debug(f"{self.exchange_name}: Client ping message sent: {ping_json}")
                    
                except asyncio.CancelledError:
                    logger.info(f"{self.exchange_name}: Client ping task canceled")
                    break
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Client ping error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"{self.exchange_name}: Client ping task error: {e}")
        
        finally:
            logger.info(f"{self.exchange_name}: Client ping task terminated")

    async def _status_monitor(self):
        """📊 Status monitor with detailed reporting"""
        logger.info(f"{self.exchange_name}: 📊 Status monitor started")
        
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                
                current_time = time.time()
                time_since_data = current_time - self.last_data_time if self.last_data_time > 0 else float('inf')
                
                logger.info(f"{self.exchange_name}: 📊 LBANK Status Report:")
                logger.info(f"  🔗 Endpoint: {self.config['url']}")
                logger.info(f"  ⏱️  Time since last data: {time_since_data:.1f}s")
                logger.info(f"  📝 Messages processed: {self.message_count}")
                logger.info(f"  🏓 Server pings received: {self.server_ping_count}")
                logger.info(f"  🏓 Server pongs sent: {self.server_pong_count}")
                logger.info(f"  🏓 Client pings sent: {self.client_ping_count}")
                logger.info(f"  🏓 Client pongs received: {self.client_pong_received_count}")
                logger.info(f"  📡 Subscribed pairs: {len(self.subscribed_pairs)}")
                
                # Data flow status
                if time_since_data < 30:
                    logger.info(f"{self.exchange_name}: ✅ Data flow healthy")
                elif time_since_data < 60:
                    logger.warning(f"{self.exchange_name}: ⚠️ Data flow slow")
                else:
                    logger.error(f"{self.exchange_name}: ❌ No data for {time_since_data:.1f}s")
                
        except asyncio.CancelledError:
            logger.info(f"{self.exchange_name}: Status monitor canceled")
        except Exception as e:
            logger.error(f"{self.exchange_name}: Status monitor error: {e}")

    def is_healthy(self) -> bool:
        """🔍 LBank health check with ping/pong stats"""
        if not super().is_healthy():
            return False
            
        # Log ping/pong stats
        logger.debug(f"{self.exchange_name}: Health check - "
                   f"server pings: {self.server_ping_count}, "
                   f"server pongs sent: {self.server_pong_count}, "
                   f"client pings sent: {self.client_ping_count}, "
                   f"client pongs received: {self.client_pong_received_count}")
        
        return True

    async def reset_state(self):
        """🔄 Reset LBank-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting LBank-specific state")
        
        # Clear subscriptions
        logger.debug(f"{self.exchange_name}: Clearing {len(self.subscribed_pairs)} subscribed pairs")
        self.subscribed_pairs.clear()
        
        # Reset ping counters
        logger.debug(f"{self.exchange_name}: Resetting ping counters - "
                   f"server pings: {self.server_ping_count}, "
                   f"server pongs: {self.server_pong_count}, "
                   f"client pings: {self.client_ping_count}, "
                   f"client pongs: {self.client_pong_received_count}")
        
        self.ping_counter = 1
        self.server_ping_count = 0
        self.server_pong_count = 0
        self.client_ping_count = 0
        self.client_pong_received_count = 0
        
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