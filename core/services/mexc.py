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
    """🚀 MEXC Service - WebSocket with Protocol Buffers Support (Enhanced Debug)"""
    
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
            import sys
            import os
            
            # Add mexc_proto to path for direct import
            proto_path = os.path.join(os.path.dirname(__file__), 'mexc_proto')
            if proto_path not in sys.path:
                sys.path.insert(0, proto_path)
            
            # Import protobuf classes directly
            import PushDataV3ApiWrapper_pb2
            self.PushDataV3ApiWrapper = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper
            
            logger.info(f"{self.exchange_name}: ✅ Protobuf support loaded successfully")
            return True
            
        except ImportError as e:
            logger.error(f"{self.exchange_name}: Protobuf support not available: {e}")
            logger.error(f"Please run: protoc *.proto --python_out=. in mexc_proto directory")
            
            # Debug: list available files
            try:
                import os
                proto_dir = os.path.join(os.path.dirname(__file__), 'mexc_proto')
                files = [f for f in os.listdir(proto_dir) if f.endswith('.py')]
                logger.error(f"Available files: {files}")
            except Exception as debug_e:
                logger.error(f"Debug error: {debug_e}")
            
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
        """📨 Handle incoming messages (JSON or Binary Protobuf) with enhanced debugging"""
        try:
            # Log ALL incoming messages for debugging
            if isinstance(message, bytes):
                logger.info(f"{self.exchange_name}: 📦 BINARY message received ({len(message)} bytes)")
                logger.debug(f"{self.exchange_name}: Binary hex (first 50 bytes): {message[:50].hex()}")
                # Binary message = Protobuf market data
                await self._handle_protobuf_message(message)
            else:
                logger.info(f"{self.exchange_name}: 📝 TEXT message received: {message}")
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
        """📊 Handle binary protobuf messages (market data) with enhanced debugging"""
        try:
            self.protobuf_messages += 1
            logger.info(f"{self.exchange_name}: 🔍 Processing protobuf message #{self.protobuf_messages} ({len(binary_data)} bytes)")
            
            if not self.protobuf_available:
                logger.warning(f"{self.exchange_name}: Protobuf message #{self.protobuf_messages} (skipped - no protobuf support)")
                return
            
            # Parse the protobuf message
            logger.debug(f"{self.exchange_name}: Parsing protobuf with PushDataV3ApiWrapper...")
            wrapper = self.PushDataV3ApiWrapper()
            wrapper.ParseFromString(binary_data)
            
            # Extract channel and symbol
            channel = getattr(wrapper, 'channel', '')
            symbol = getattr(wrapper, 'symbol', '')
            
            logger.info(f"{self.exchange_name}: 📊 Protobuf parsed - channel: '{channel}', symbol: '{symbol}'")
            
            # Debug: Check all wrapper attributes
            wrapper_attrs = [attr for attr in dir(wrapper) if not attr.startswith('_')]
            logger.debug(f"{self.exchange_name}: Wrapper attributes: {wrapper_attrs}")
            
            # Handle book ticker data
            if 'bookTicker' in channel and hasattr(wrapper, 'publicbookticker'):
                logger.info(f"{self.exchange_name}: 📈 Found book ticker data for {symbol}")
                await self._process_book_ticker_protobuf(symbol, wrapper.publicbookticker)
            elif hasattr(wrapper, 'publicBookTicker'):
                logger.info(f"{self.exchange_name}: 📈 Found publicBookTicker (alternate) for {symbol}")
                await self._process_book_ticker_protobuf(symbol, wrapper.publicBookTicker)
            else:
                logger.warning(f"{self.exchange_name}: ❌ No book ticker data found in protobuf")
                logger.debug(f"{self.exchange_name}: Available wrapper attributes: {[attr for attr in dir(wrapper) if not attr.startswith('_') and hasattr(wrapper, attr)]}")
            
        except Exception as e:
            self.protobuf_errors += 1
            logger.error(f"{self.exchange_name}: 💥 Protobuf parsing error #{self.protobuf_errors}: {e}")
            # Log first few bytes for debugging
            hex_data = binary_data[:50].hex() if len(binary_data) >= 50 else binary_data.hex()
            logger.error(f"{self.exchange_name}: Binary data (first 50 bytes): {hex_data}")
            
            # Try to understand the structure
            try:
                logger.debug(f"{self.exchange_name}: Attempting alternate parsing...")
                # Maybe try direct field access or different wrapper
            except Exception as e2:
                logger.debug(f"{self.exchange_name}: Alternate parsing failed: {e2}")

    async def _process_book_ticker_protobuf(self, symbol: str, book_ticker):
        """📊 Process book ticker protobuf data with enhanced debugging"""
        try:
            logger.info(f"{self.exchange_name}: 💰 Processing book ticker for {symbol}")
            
            # Debug book ticker structure
            ticker_attrs = [attr for attr in dir(book_ticker) if not attr.startswith('_')]
            logger.debug(f"{self.exchange_name}: Book ticker attributes: {ticker_attrs}")
            
            # Try different possible field names
            possible_bid_fields = ['bidprice', 'bidPrice', 'bid_price', 'bid']
            possible_ask_fields = ['askprice', 'askPrice', 'ask_price', 'ask']
            possible_bid_qty_fields = ['bidquantity', 'bidQuantity', 'bid_quantity', 'bidQty']
            possible_ask_qty_fields = ['askquantity', 'askQuantity', 'ask_quantity', 'askQty']
            
            bid_price = None
            ask_price = None
            bid_quantity = None
            ask_quantity = None
            
            # Find bid price
            for field in possible_bid_fields:
                if hasattr(book_ticker, field):
                    bid_price = Decimal(str(getattr(book_ticker, field)))
                    logger.debug(f"{self.exchange_name}: Found bid price in field '{field}': {bid_price}")
                    break
            
            # Find ask price  
            for field in possible_ask_fields:
                if hasattr(book_ticker, field):
                    ask_price = Decimal(str(getattr(book_ticker, field)))
                    logger.debug(f"{self.exchange_name}: Found ask price in field '{field}': {ask_price}")
                    break
            
            # Find bid quantity
            for field in possible_bid_qty_fields:
                if hasattr(book_ticker, field):
                    bid_quantity = Decimal(str(getattr(book_ticker, field)))
                    logger.debug(f"{self.exchange_name}: Found bid quantity in field '{field}': {bid_quantity}")
                    break
            
            # Find ask quantity
            for field in possible_ask_qty_fields:
                if hasattr(book_ticker, field):
                    ask_quantity = Decimal(str(getattr(book_ticker, field)))
                    logger.debug(f"{self.exchange_name}: Found ask quantity in field '{field}': {ask_quantity}")
                    break
            
            if bid_price is None or ask_price is None:
                logger.error(f"{self.exchange_name}: ❌ Could not find bid/ask prices")
                logger.error(f"{self.exchange_name}: Available fields: {[attr for attr in dir(book_ticker) if not attr.startswith('_')]}")
                return
            
            logger.info(f"{self.exchange_name}: 📊 Book ticker for {symbol} - "
                       f"bid: {bid_price}@{bid_quantity or 0}, ask: {ask_price}@{ask_quantity or 0}")
            
            # Validate prices
            if bid_price <= 0 or ask_price <= 0:
                logger.warning(f"{self.exchange_name}: ❌ Invalid prices for {symbol}: bid={bid_price}, ask={ask_price}")
                return
            
            # Save price data
            await self.save_price_data(symbol, bid_price, ask_price, bid_quantity or 0, ask_quantity or 0)
            logger.info(f"{self.exchange_name}: ✅ Successfully saved price data for {symbol}")
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: 💥 Book ticker processing error: {e}")

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