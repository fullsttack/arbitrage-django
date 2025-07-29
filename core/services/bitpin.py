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

class BitpinService(BaseExchangeService):
    """🚀 Bitpin Service - Client Ping/Pong Implementation"""
    
    def __init__(self):
        config = get_config('bitpin')
        super().__init__('bitpin', config)
        self.subscribed_pairs = set()
        self.client_ping_task = None
        
        # Ping/Pong stats
        self.client_ping_count = 0
        self.server_pong_count = 0
        
    async def connect(self) -> bool:
        """🔌 Simple connection"""
        logger.info(f"{self.exchange_name}: Attempting connection to {self.config['url']}")
        
        try:
            # Reset state before connecting
            await self.reset_state()
            
            self.websocket = await websockets.connect(
                self.config['url'],
                ping_interval=None,  # Disable automatic ping
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
            ping_task = asyncio.create_task(self._client_ping_task())
            status_task = asyncio.create_task(self._status_monitor())
            
            self.background_tasks = [listen_task, health_task, ping_task, status_task]
            self.client_ping_task = ping_task
            
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
        
        # Prepare new subscriptions
        new_subscriptions = []
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                new_subscriptions.append(symbol)
                self.subscribed_pairs.add(symbol)
        
        if not new_subscriptions:
            logger.info(f"{self.exchange_name}: All pairs already subscribed")
            return True
        
        try:
            # Send subscription message for new pairs
            subscribe_msg = {
                "method": "sub_to_market_data",
                "symbols": new_subscriptions
            }
            
            msg_json = json.dumps(subscribe_msg)
            await self.websocket.send(msg_json)
            
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
            
            # Handle PONG response
            if isinstance(data, dict) and data.get('message') == 'PONG':
                await self._handle_server_pong(data)
                
            # Handle subscription response
            elif isinstance(data, dict) and 'message' in data and 'sub to markets' in data.get('message', ''):
                await self._handle_subscription_response(data)
                
            # Handle market data
            elif isinstance(data, dict) and data.get('event') == 'market_data':
                await self._handle_market_data(data)
                
            # Handle matches (trades) - optional
            elif isinstance(data, dict) and data.get('event') == 'matches_update':
                logger.debug(f"{self.exchange_name}: Matches update for {data.get('symbol', 'unknown')}")
                
            # Handle other messages
            else:
                logger.debug(f"{self.exchange_name}: Unknown message format: {data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 Handle server pong response"""
        self.server_pong_count += 1
        logger.debug(f"{self.exchange_name}: 🏓 RECEIVED SERVER PONG #{self.server_pong_count}")
        logger.debug(f"{self.exchange_name}: Pong message: {data}")

    async def _handle_subscription_response(self, data: dict):
        """📨 Handle subscription response"""
        message = data.get('message', '')
        logger.info(f"{self.exchange_name}: ✅ Subscription response: {message}")

    async def _handle_market_data(self, data: dict):
        """📊 Process market data"""
        try:
            symbol = data.get('symbol', '')
            asks = data.get('ask', [])
            bids = data.get('bid', [])
            
            logger.debug(f"{self.exchange_name}: Market data for {symbol} - bids: {len(bids)}, asks: {len(asks)}")
            
            if not symbol or not asks or not bids:
                logger.debug(f"{self.exchange_name}: Incomplete market data for {symbol}")
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
            logger.error(f"{self.exchange_name}: Market data processing error: {e}")

    async def _client_ping_task(self):
        """🏓 Send periodic client pings"""
        logger.info(f"{self.exchange_name}: Starting client ping task (every {self.config['ping_interval']}s)")
        
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
                    ping_msg = {"message": "PING"}
                    ping_json = json.dumps(ping_msg)
                    await self.websocket.send(ping_json)
                    
                    self.client_ping_count += 1
                    logger.debug(f"{self.exchange_name}: 🏓 SENT CLIENT PING #{self.client_ping_count}")
                    logger.debug(f"{self.exchange_name}: Ping message sent: {ping_json}")
                    
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
                
                logger.info(f"{self.exchange_name}: 📊 BITPIN Status Report:")
                logger.info(f"  🔗 Endpoint: {self.config['url']}")
                logger.info(f"  ⏱️  Time since last data: {time_since_data:.1f}s")
                logger.info(f"  📝 Messages processed: {self.message_count}")
                logger.info(f"  🏓 Client pings sent: {self.client_ping_count}")
                logger.info(f"  🏓 Server pongs received: {self.server_pong_count}")
                logger.info(f"  📡 Subscribed pairs: {len(self.subscribed_pairs)}")
                
                # Ping/Pong ratio
                if self.client_ping_count > 0:
                    pong_ratio = self.server_pong_count / self.client_ping_count
                    logger.info(f"  🔄 Ping/Pong ratio: {pong_ratio:.2f}")
                else:
                    logger.info(f"  🔄 Ping/Pong ratio: N/A")
                
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
        """🔍 Bitpin health check with ping/pong stats"""
        if not super().is_healthy():
            return False
            
        # Log ping/pong stats
        logger.debug(f"{self.exchange_name}: Health check - "
                   f"client pings sent: {self.client_ping_count}, "
                   f"server pongs received: {self.server_pong_count}")
        
        # Check ping/pong ratio
        if self.client_ping_count > 0:
            pong_ratio = self.server_pong_count / self.client_ping_count
            if pong_ratio < 0.8:  # Less than 80% response rate
                logger.warning(f"{self.exchange_name}: Low ping/pong response rate: {pong_ratio:.2f}")
        
        return True

    async def reset_state(self):
        """🔄 Reset Bitpin-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting Bitpin-specific state")
        
        # Clear subscriptions
        logger.debug(f"{self.exchange_name}: Clearing {len(self.subscribed_pairs)} subscribed pairs")
        self.subscribed_pairs.clear()
        
        # Reset ping/pong counters
        logger.debug(f"{self.exchange_name}: Resetting ping/pong counters - "
                   f"client pings: {self.client_ping_count}, "
                   f"server pongs: {self.server_pong_count}")
        
        self.client_ping_count = 0
        self.server_pong_count = 0
        
        # Clear ping task reference
        self.client_ping_task = None
        
        logger.debug(f"{self.exchange_name}: Bitpin state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting Bitpin disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # Bitpin-specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: Bitpin disconnect completed")
        logger.info(f"{self.exchange_name}: Session stats - Client pings: {self.client_ping_count}, Server pongs: {self.server_pong_count}")