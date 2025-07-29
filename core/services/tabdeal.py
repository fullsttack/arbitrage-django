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

class TabdealService(BaseExchangeService):
    """🚀 Fast and Simple Tabdeal Service"""
    
    def __init__(self):
        config = get_config('tabdeal')
        super().__init__('tabdeal', config)
        self.subscribed_pairs = set()
        self.subscription_id = 1
        
    async def connect(self) -> bool:
        """🔌 Simple connection"""
        logger.info(f"{self.exchange_name}: Attempting connection to {self.config['url']}")
        
        try:
            # Reset state before connecting
            await self.reset_state()
            
            self.websocket = await websockets.connect(
                self.config['url'],
                ping_interval=None,  # No ping/pong - server sends data every 2s
                ping_timeout=None,
                close_timeout=10,
                max_size=1024*1024
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            logger.info(f"{self.exchange_name}: Connected successfully")
            
            # Start background tasks
            listen_task = asyncio.create_task(self.listen_loop())
            health_task = asyncio.create_task(self.health_monitor())
            status_task = asyncio.create_task(self._status_monitor())
            
            self.background_tasks = [listen_task, health_task, status_task]
            
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
        
        # Prepare subscription list
        new_subscriptions = []
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                # Tabdeal format: "symbol@depth@2000ms"
                subscription = f"{symbol}@depth@2000ms"
                new_subscriptions.append(subscription)
                self.subscribed_pairs.add(symbol)
        
        if not new_subscriptions:
            logger.info(f"{self.exchange_name}: All pairs already subscribed")
            return True
        
        try:
            # Send subscription message
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": new_subscriptions,
                "id": self.subscription_id
            }
            
            msg_json = json.dumps(subscribe_msg)
            await self.websocket.send(msg_json)
            
            self.subscription_id += 1
            
            logger.info(f"{self.exchange_name}: Subscription sent for {len(new_subscriptions)} new pairs")
            logger.debug(f"{self.exchange_name}: Subscription message: {msg_json}")
            
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Subscribe error: {e}")
            return False

    async def handle_message(self, message: str):
        """📨 Handle incoming messages"""
        try:
            # Parse JSON
            try:
                data = json.loads(message)
                logger.debug(f"{self.exchange_name}: Received message type: {type(data)}")
            except json.JSONDecodeError:
                logger.warning(f"{self.exchange_name}: Non-JSON message: {message[:100]}")
                return
            
            # Handle subscription response
            if isinstance(data, dict) and 'result' in data and 'id' in data:
                await self._handle_subscription_response(data)
                
            # Handle market data stream
            elif isinstance(data, dict) and 'stream' in data and 'data' in data:
                await self._handle_market_data(data)
                
            # Handle other messages
            else:
                logger.debug(f"{self.exchange_name}: Unknown message format: {data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_subscription_response(self, data: dict):
        """📨 Handle subscription response"""
        subscription_id = data.get('id')
        result = data.get('result')
        
        if result is None:
            logger.info(f"{self.exchange_name}: ✅ Subscription #{subscription_id} successful")
        else:
            logger.error(f"{self.exchange_name}: ❌ Subscription #{subscription_id} failed: {result}")

    async def _handle_market_data(self, data: dict):
        """📊 Process market data"""
        try:
            stream = data.get('stream', '')
            market_data = data.get('data', {})
            
            if not stream or not market_data:
                logger.debug(f"{self.exchange_name}: Empty market data")
                return
            
            # Extract symbol from stream (e.g., "usdtirt@depth@2000ms" -> "usdtirt")
            symbol = stream.split('@')[0] if '@' in stream else stream
            
            event_type = market_data.get('e')
            
            if event_type == 'depthUpdate':
                await self._process_depth_update(symbol, market_data)
            else:
                logger.debug(f"{self.exchange_name}: Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Market data processing error: {e}")

    async def _process_depth_update(self, symbol: str, market_data: dict):
        """📊 Process depth update (orderbook)"""
        try:
            bids = market_data.get('b', [])
            asks = market_data.get('a', [])
            
            logger.debug(f"{self.exchange_name}: Depth update for {symbol} - bids: {len(bids)}, asks: {len(asks)}")
            
            if not bids or not asks:
                logger.debug(f"{self.exchange_name}: Empty bids or asks for {symbol}")
                return
            
            # Get best prices (first in list)
            try:
                # Best bid (highest buy price)
                best_bid = bids[0]
                bid_price = Decimal(str(best_bid[0]))
                bid_volume = Decimal(str(best_bid[1]))
                
                # Best ask (lowest sell price)  
                best_ask = asks[0]
                ask_price = Decimal(str(best_ask[0]))
                ask_volume = Decimal(str(best_ask[1]))
                
                logger.debug(f"{self.exchange_name}: Best prices for {symbol} - "
                           f"bid: {bid_price}@{bid_volume}, ask: {ask_price}@{ask_volume}")
                
                # Save price data
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                logger.debug(f"{self.exchange_name}: 💾 Saved price data for {symbol}")
                
            except (IndexError, ValueError, TypeError) as e:
                logger.error(f"{self.exchange_name}: Error parsing prices for {symbol}: {e}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Depth update processing error: {e}")

    async def _status_monitor(self):
        """📊 Status monitor with detailed reporting"""
        logger.info(f"{self.exchange_name}: 📊 Status monitor started")
        
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                
                current_time = time.time()
                time_since_data = current_time - self.last_data_time if self.last_data_time > 0 else float('inf')
                
                logger.info(f"{self.exchange_name}: 📊 TABDEAL Status Report:")
                logger.info(f"  🔗 Endpoint: {self.config['url']}")
                logger.info(f"  ⏱️  Time since last data: {time_since_data:.1f}s")
                logger.info(f"  📝 Messages processed: {self.message_count}")
                logger.info(f"  📡 Subscribed pairs: {len(self.subscribed_pairs)}")
                logger.info(f"  🆔 Next subscription ID: {self.subscription_id}")
                
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
        """🔍 Tabdeal health check"""
        if not super().is_healthy():
            return False
            
        # Log subscription status
        logger.debug(f"{self.exchange_name}: Health check - subscribed pairs: {len(self.subscribed_pairs)}")
        
        return True

    async def reset_state(self):
        """🔄 Reset Tabdeal-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting Tabdeal-specific state")
        
        # Clear subscriptions
        logger.debug(f"{self.exchange_name}: Clearing {len(self.subscribed_pairs)} subscribed pairs")
        self.subscribed_pairs.clear()
        
        # Reset subscription ID
        self.subscription_id = 1
        
        logger.debug(f"{self.exchange_name}: Tabdeal state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting Tabdeal disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # Tabdeal-specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: Tabdeal disconnect completed")