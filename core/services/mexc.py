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

class MexcService(BaseExchangeService):
    """🚀 MEXC Service - WebSocket with Protocol Buffers Support"""
    
    def __init__(self):
        config = get_config('mexc')
        super().__init__('mexc', config)
        self.subscribed_pairs = set()
        self.client_ping_task = None
        
        # Ping/Pong stats
        self.client_ping_count = 0
        self.server_pong_count = 0
        
        # Subscription tracking
        self.subscription_responses = {}
        
        # Protobuf stats
        self.protobuf_messages = 0
        self.protobuf_errors = 0
        
        # Try to import protobuf
        self.protobuf_available = self._check_protobuf_support()
        
    def _check_protobuf_support(self) -> bool:
        """🔧 Check if protobuf is available"""
        try:
            # Try to import the generated protobuf classes
            # These should be generated from: https://github.com/mexcdevelop/websocket-proto
            # Command: protoc *.proto --python_out=core/services/mexc_proto/
            
            # Uncomment when protobuf files are available:
            from .mexc_proto import PushDataV3ApiWrapper_pb2
            self.PushDataV3ApiWrapper = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper
            return True
            
            logger.warning(f"{self.exchange_name}: Protobuf classes not found. Please run:")
            logger.warning(f"  1. git clone https://github.com/mexcdevelop/websocket-proto")
            logger.warning(f"  2. protoc *.proto --python_out=core/services/mexc_proto/")
            logger.warning(f"  3. Uncomment protobuf imports in mexc.py")
            
            return False
            
        except ImportError as e:
            logger.warning(f"{self.exchange_name}: Protobuf support not available: {e}")
            return False
        
    async def connect(self) -> bool:
        """🔌 Connect to MEXC WebSocket"""
        logger.info(f"{self.exchange_name}: Attempting connection to {self.config['url']}")
        
        if not self.protobuf_available:
            logger.error(f"{self.exchange_name}: Cannot connect - Protobuf support required!")
            logger.error(f"Please install protobuf and generate Python classes from:")
            logger.error(f"https://github.com/mexcdevelop/websocket-proto")
            return False
        
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
            
            self.background_tasks = [listen_task, health_task, ping_task]
            self.client_ping_task = ping_task
            
            logger.debug(f"{self.exchange_name}: Background tasks started: {len(self.background_tasks)}")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Connect failed: {e}")
            await self.reset_state()
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to trading pairs using Book Ticker streams"""
        logger.info(f"{self.exchange_name}: Starting subscription for {len(pairs)} pairs")
        logger.debug(f"{self.exchange_name}: Current subscribed pairs: {self.subscribed_pairs}")
        logger.debug(f"{self.exchange_name}: Pairs to subscribe: {pairs}")
        
        if not self.is_connected:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - not connected")
            return False
            
        if not self.websocket:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - no websocket")
            return False
        
        # Prepare subscription list for new pairs only
        new_subscriptions = []
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                # Use Book Ticker stream for best bid/ask (100ms updates)
                channel = f"spot@public.aggre.bookTicker.v3.api.pb@100ms@{symbol.upper()}"
                new_subscriptions.append(channel)
                self.subscribed_pairs.add(symbol)
        
        if not new_subscriptions:
            logger.info(f"{self.exchange_name}: All pairs already subscribed")
            return True
        
        # Check subscription limit (max 30 per connection)
        if len(self.subscribed_pairs) > 30:
            logger.warning(f"{self.exchange_name}: Subscription limit exceeded (30 max)")
            new_subscriptions = new_subscriptions[:30 - (len(self.subscribed_pairs) - len(new_subscriptions))]
        
        try:
            # Send subscription message (JSON format)
            subscribe_msg = {
                "method": "SUBSCRIPTION", 
                "params": new_subscriptions
            }
            
            msg_json = json.dumps(subscribe_msg)
            await self.websocket.send(msg_json)
            
            logger.info(f"{self.exchange_name}: Subscription sent for {len(new_subscriptions)} new pairs")
            logger.debug(f"{self.exchange_name}: Subscription message: {msg_json}")
            
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Subscribe error: {e}")
            return False

    async def handle_message(self, message):
        """📨 Handle incoming messages (JSON or Binary Protobuf)"""
        try:
            # Check if message is binary (protobuf) or text (JSON)
            if isinstance(message, bytes):
                # Binary message = Protobuf market data
                await self._handle_protobuf_message(message)
            else:
                # Text message = JSON (subscription responses, ping/pong)
                await self._handle_json_message(message)
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_json_message(self, message: str):
        """📨 Handle JSON messages (ping/pong, subscriptions)"""
        try:
            data = json.loads(message)
            logger.debug(f"{self.exchange_name}: JSON message: {type(data)}")
            
            # Handle PONG response
            if isinstance(data, dict) and data.get('msg') == 'PONG':
                await self._handle_server_pong(data)
                
            # Handle subscription response
            elif isinstance(data, dict) and 'id' in data and 'code' in data and 'msg' in data:
                await self._handle_subscription_response(data)
                
            # Handle other JSON messages
            else:
                logger.debug(f"{self.exchange_name}: Unknown JSON message: {data}")
                
        except json.JSONDecodeError:
            logger.warning(f"{self.exchange_name}: Invalid JSON message: {message[:100]}")
        except Exception as e:
            logger.error(f"{self.exchange_name}: JSON message handling error: {e}")

    async def _handle_protobuf_message(self, binary_data: bytes):
        """📊 Handle binary protobuf messages (market data)"""
        try:
            self.protobuf_messages += 1
            
            if not self.protobuf_available:
                # Skip protobuf parsing if not available
                logger.debug(f"{self.exchange_name}: Protobuf message #{self.protobuf_messages} (skipped - no protobuf support)")
                return
            
            # TODO: Uncomment when protobuf classes are available
            """
            # Parse the protobuf message
            wrapper = self.PushDataV3ApiWrapper()
            wrapper.ParseFromString(binary_data)
            
            # Extract channel and symbol
            channel = getattr(wrapper, 'channel', '')
            symbol = getattr(wrapper, 'symbol', '')
            
            logger.debug(f"{self.exchange_name}: Protobuf message - channel: {channel}, symbol: {symbol}")
            
            # Handle book ticker data
            if 'bookTicker' in channel and hasattr(wrapper, 'publicbookticker'):
                await self._process_book_ticker_protobuf(symbol, wrapper.publicbookticker)
            else:
                logger.debug(f"{self.exchange_name}: Unhandled protobuf channel: {channel}")
            """
            
            # For now, just log that we received protobuf data
            logger.debug(f"{self.exchange_name}: Protobuf message #{self.protobuf_messages} received ({len(binary_data)} bytes)")
            
        except Exception as e:
            self.protobuf_errors += 1
            logger.error(f"{self.exchange_name}: Protobuf parsing error #{self.protobuf_errors}: {e}")

    async def _process_book_ticker_protobuf(self, symbol: str, book_ticker):
        """📊 Process book ticker protobuf data"""
        try:
            # Extract bid/ask from protobuf object
            bid_price = Decimal(str(getattr(book_ticker, 'bidprice', '0')))
            bid_quantity = Decimal(str(getattr(book_ticker, 'bidquantity', '0')))
            ask_price = Decimal(str(getattr(book_ticker, 'askprice', '0')))
            ask_quantity = Decimal(str(getattr(book_ticker, 'askquantity', '0')))
            
            logger.debug(f"{self.exchange_name}: Book ticker for {symbol} - "
                       f"bid: {bid_price}@{bid_quantity}, ask: {ask_price}@{ask_quantity}")
            
            # Validate prices
            if bid_price <= 0 or ask_price <= 0 or bid_quantity <= 0 or ask_quantity <= 0:
                logger.debug(f"{self.exchange_name}: Invalid price/quantity for {symbol}")
                return
            
            # Save price data
            await self.save_price_data(symbol, bid_price, ask_price, bid_quantity, ask_quantity)
            logger.debug(f"{self.exchange_name}: 💾 Saved protobuf price data for {symbol}")
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Book ticker protobuf processing error: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 Handle server pong response"""
        self.server_pong_count += 1
        logger.info(f"{self.exchange_name}: 🏓 RECEIVED SERVER PONG #{self.server_pong_count}")
        logger.debug(f"{self.exchange_name}: Pong message: {data}")

    async def _handle_subscription_response(self, data: dict):
        """📨 Handle subscription response"""
        msg_id = data.get('id', 'unknown')
        code = data.get('code', -1)
        msg = data.get('msg', '')
        
        if code == 0:
            logger.info(f"{self.exchange_name}: ✅ Subscription successful - ID: {msg_id}, Channel: {msg}")
            self.subscription_responses[msg] = True
        else:
            logger.error(f"{self.exchange_name}: ❌ Subscription failed - ID: {msg_id}, Code: {code}, Msg: {msg}")
            self.subscription_responses[msg] = False

    async def _client_ping_task(self):
        """🏓 Send periodic client pings to keep connection alive"""
        logger.info(f"{self.exchange_name}: Starting client ping task (every {self.config['ping_interval']}s)")
        
        try:
            while self.is_connected and self._listen_task_running:
                try:
                    await asyncio.sleep(self.config['ping_interval'])
                    
                    if not self.is_connected or not self.websocket:
                        break
                        
                    # Send client ping (JSON format)
                    ping_msg = {"method": "PING"}
                    ping_json = json.dumps(ping_msg)
                    await self.websocket.send(ping_json)
                    
                    self.client_ping_count += 1
                    logger.info(f"{self.exchange_name}: 🏓 SENT CLIENT PING #{self.client_ping_count}")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Client ping error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"{self.exchange_name}: Client ping task error: {e}")
        finally:
            logger.info(f"{self.exchange_name}: Client ping task terminated")

    def is_healthy(self) -> bool:
        """🔍 MEXC health check with protobuf stats"""
        if not super().is_healthy():
            return False
            
        # Log stats
        logger.debug(f"{self.exchange_name}: Health check - "
                   f"pings: {self.client_ping_count}, pongs: {self.server_pong_count}, "
                   f"protobuf messages: {self.protobuf_messages}, errors: {self.protobuf_errors}")
        
        return True

    async def reset_state(self):
        """🔄 Reset MEXC-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting MEXC-specific state")
        
        # Clear subscriptions
        self.subscribed_pairs.clear()
        
        # Reset counters
        self.client_ping_count = 0
        self.server_pong_count = 0
        self.protobuf_messages = 0
        self.protobuf_errors = 0
        
        # Clear responses
        self.subscription_responses.clear()
        self.client_ping_task = None
        
        logger.debug(f"{self.exchange_name}: MEXC state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting MEXC disconnect")
        
        await super().disconnect()
        
        logger.info(f"{self.exchange_name}: MEXC disconnect completed")
        logger.info(f"{self.exchange_name}: Session stats - "
                   f"Pings: {self.client_ping_count}, Pongs: {self.server_pong_count}, "
                   f"Protobuf messages: {self.protobuf_messages}, Errors: {self.protobuf_errors}")