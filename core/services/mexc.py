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
    """🚀 MEXC Service - Fixed Implementation Based on Official Documentation"""
    
    def __init__(self):
        config = get_config('mexc')
        super().__init__('mexc', config)
        self.subscribed_pairs = set()
        self.client_ping_task = None
        
        # ✅ استفاده از URL صحیح از config (ws:// نه wss://)
        logger.info(f"{self.exchange_name}: Using CORRECT endpoint from config: {self.config['url']}")
        
        # Ping/Pong stats
        self.client_ping_count = 0
        self.server_pong_count = 0
        
        # Subscription tracking
        self.subscription_responses = {}
        
        # Protobuf stats
        self.protobuf_messages = 0
        self.protobuf_errors = 0
        self.successful_parses = 0
        self.empty_messages = 0
        self.json_messages = 0
        self.last_data_time = 0
        
        # Try to import protobuf
        self.protobuf_available = self._check_protobuf_support()
        
        logger.info(f"{self.exchange_name}: ✅ Initialized with CORRECT endpoint: {self.config['url']}")
        
    def _check_protobuf_support(self) -> bool:
        """🔧 Check if protobuf is available"""
        try:
            import sys
            import os
            
            proto_path = os.path.join(os.path.dirname(__file__), 'mexc_proto')
            if proto_path not in sys.path:
                sys.path.insert(0, proto_path)
            
            import PushDataV3ApiWrapper_pb2
            self.PushDataV3ApiWrapper = PushDataV3ApiWrapper_pb2.PushDataV3ApiWrapper
            
            logger.info(f"{self.exchange_name}: ✅ Protobuf support loaded successfully")
            return True
            
        except ImportError as e:
            logger.warning(f"{self.exchange_name}: Protobuf not available: {e}")
            logger.warning(f"{self.exchange_name}: Please download protobuf files from: https://github.com/mexcdevelop/websocket-proto")
            return False
        
    async def connect(self) -> bool:
        """🔌 Connect to MEXC using CORRECT endpoint from config"""
        logger.info(f"{self.exchange_name}: Connecting to OFFICIAL endpoint: {self.config['url']}")
        
        try:
            await self.reset_state()
            
            # ✅ استفاده از URL از config بدون تغییر
            self.websocket = await websockets.connect(
                self.config['url'],  # ✅ استفاده مستقیم از config
                ping_interval=None,  # Handle ping manually
                ping_timeout=None,
                close_timeout=10,
                max_size=1024*1024
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            logger.info(f"{self.exchange_name}: ✅ Connected to OFFICIAL MEXC endpoint: {self.config['url']}")
            
            # Start background tasks
            listen_task = asyncio.create_task(self.listen_loop())
            health_task = asyncio.create_task(self.health_monitor())
            ping_task = asyncio.create_task(self._client_ping_task())
            debug_task = asyncio.create_task(self._debug_monitor())
            
            self.background_tasks = [listen_task, health_task, ping_task, debug_task]
            self.client_ping_task = ping_task
            
            logger.info(f"{self.exchange_name}: Background tasks started: {len(self.background_tasks)}")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Connect failed: {e}")
            await self.reset_state()
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe using EXACT format from documentation"""
        logger.info(f"{self.exchange_name}: Starting subscription for {len(pairs)} pairs using OFFICIAL format")
        
        if not self.is_connected or not self.websocket:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - not connected")
            return False
        
        try:
            for symbol in pairs:
                if symbol not in self.subscribed_pairs:
                    # Use EXACT format from documentation
                    # Format: spot@public.aggre.bookTicker.v3.api.pb@100ms@<SYMBOL>
                    channel = f"spot@public.aggre.bookTicker.v3.api.pb@100ms@{symbol.upper()}"
                    
                    subscription_msg = {
                        "method": "SUBSCRIPTION",
                        "params": [channel]
                    }
                    
                    await self.websocket.send(json.dumps(subscription_msg))
                    logger.debug(f"{self.exchange_name}: 📡 Subscribed using OFFICIAL format: {channel}")
                    
                    self.subscribed_pairs.add(symbol)
                    await asyncio.sleep(0.3)  # Rate limit
            
            logger.info(f"{self.exchange_name}: ✅ OFFICIAL subscription completed for {len(self.subscribed_pairs)} pairs")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Subscription error: {e}")
            return False

    async def handle_message(self, message):
        """📨 Handle messages according to documentation (Protobuf + JSON)"""
        try:
            if isinstance(message, bytes):
                logger.debug(f"{self.exchange_name}: 📦 PROTOBUF message received ({len(message)} bytes)")
                await self._handle_protobuf_message(message)
            elif isinstance(message, str):
                self.json_messages += 1
                logger.debug(f"{self.exchange_name}: 📝 JSON message #{self.json_messages}: {message}")
                await self._handle_json_message(message)
            else:
                logger.warning(f"{self.exchange_name}: ❌ Unknown message type: {type(message)}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_json_message(self, message: str):
        """📨 Handle JSON messages (subscription responses, ping/pong)"""
        try:
            data = json.loads(message)
            
            # Handle PONG response as per documentation
            if isinstance(data, dict) and data.get('msg') == 'PONG':
                await self._handle_server_pong(data)
                
            # Handle subscription response
            elif isinstance(data, dict) and 'code' in data and 'msg' in data:
                await self._handle_subscription_response(data)
                
            else:
                logger.debug(f"{self.exchange_name}: Other JSON message: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"{self.exchange_name}: ❌ Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"{self.exchange_name}: ❌ JSON processing error: {e}")

    async def _handle_protobuf_message(self, binary_data: bytes):
        """📊 Handle protobuf messages with improved debugging"""
        try:
            self.protobuf_messages += 1
            logger.debug(f"{self.exchange_name}: 🔍 Processing protobuf message #{self.protobuf_messages}")
            
            if not self.protobuf_available:
                logger.warning(f"{self.exchange_name}: Protobuf not available, cannot parse binary data")
                return
            
            # Parse using PushDataV3ApiWrapper as per documentation
            wrapper = self.PushDataV3ApiWrapper()
            wrapper.ParseFromString(binary_data)
            
            # ✅ بهبود debugging برای یافتن field names صحیح
            self._debug_protobuf_structure(wrapper)
            
            # Extract channel and symbol with better error handling
            channel = getattr(wrapper, 'channel', '')
            symbol = getattr(wrapper, 'symbol', '')
            # Try both sendTime and sendtime (protobuf uses sendTime)
            send_time = getattr(wrapper, 'sendTime', getattr(wrapper, 'sendtime', 0))
            
            logger.debug(f"{self.exchange_name}: 📊 PARSED - channel: '{channel}', symbol: '{symbol}', sendtime: {send_time}")
            
            # Handle book ticker with correct field name from protobuf
            book_ticker_obj = None
            
            # Check for the correct protobuf field name
            if hasattr(wrapper, 'publicAggreBookTicker'):
                book_ticker_obj = getattr(wrapper, 'publicAggreBookTicker')
                logger.debug(f"{self.exchange_name}: Found publicAggreBookTicker field")
            # Fallback to other possible field names for different message types
            else:
                possible_fields = ['publicBookTicker', 'publicbookticker', 'public_book_ticker', 'bookTicker']
                for field_name in possible_fields:
                    if hasattr(wrapper, field_name):
                        book_ticker_obj = getattr(wrapper, field_name)
                        logger.debug(f"{self.exchange_name}: Found book ticker field: {field_name}")
                        break
            
            if book_ticker_obj:
                await self._handle_book_ticker_protobuf(symbol, book_ticker_obj)
            else:
                # ✅ بهبود debugging
                available_attrs = [attr for attr in dir(wrapper) if not attr.startswith('_') and hasattr(wrapper, attr)]
                logger.warning(f"{self.exchange_name}: ❌ No book ticker found, available attributes: {available_attrs}")
            
        except Exception as e:
            self.protobuf_errors += 1
            logger.error(f"{self.exchange_name}: 💥 Protobuf error #{self.protobuf_errors}: {e}")
            # Log hex data for debugging
            hex_data = binary_data[:50].hex()
            logger.error(f"{self.exchange_name}: Binary data (first 50 bytes): {hex_data}")

    def _debug_protobuf_structure(self, wrapper):
        """🔍 Debug protobuf structure to find correct field names"""
        try:
            all_attrs = [attr for attr in dir(wrapper) if not attr.startswith('_')]
            
            # Log only every 10th message to avoid spam
            if self.protobuf_messages % 10 == 1:
                logger.debug(f"{self.exchange_name}: 🔍 All protobuf attributes: {all_attrs}")
                
                # Check which attributes have data
                attrs_with_data = []
                for attr in all_attrs:
                    try:
                        value = getattr(wrapper, attr)
                        if value and str(value).strip():
                            attrs_with_data.append(f"{attr}={value}")
                    except:
                        pass
                
                if attrs_with_data:
                    logger.debug(f"{self.exchange_name}: 🔍 Attributes with data: {attrs_with_data}")
                    
        except Exception as e:
            logger.debug(f"{self.exchange_name}: Debug structure error: {e}")

    async def _handle_book_ticker_protobuf(self, symbol: str, book_ticker):
        """💰 Handle book ticker protobuf with improved field detection"""
        try:
            logger.debug(f"{self.exchange_name}: 💰 Processing book ticker for {symbol}")
            
            # ✅ Try multiple possible field name formats
            bid_price_raw = None
            ask_price_raw = None
            bid_qty_raw = None
            ask_qty_raw = None
            
            # Correct field names from protobuf (bidPrice, bidQuantity, askPrice, askQuantity)
            bid_price_fields = ['bidPrice', 'bidprice', 'bid_price', 'bestBidPrice']
            ask_price_fields = ['askPrice', 'askprice', 'ask_price', 'bestAskPrice']
            bid_qty_fields = ['bidQuantity', 'bidquantity', 'bid_quantity', 'bestBidQty']
            ask_qty_fields = ['askQuantity', 'askquantity', 'ask_quantity', 'bestAskQty']
            
            # Find bid price
            for field in bid_price_fields:
                if hasattr(book_ticker, field):
                    bid_price_raw = getattr(book_ticker, field)
                    if bid_price_raw:
                        logger.debug(f"{self.exchange_name}: Found bid price field: {field}")
                        break
            
            # Find ask price
            for field in ask_price_fields:
                if hasattr(book_ticker, field):
                    ask_price_raw = getattr(book_ticker, field)
                    if ask_price_raw:
                        logger.debug(f"{self.exchange_name}: Found ask price field: {field}")
                        break
            
            # Find bid quantity
            for field in bid_qty_fields:
                if hasattr(book_ticker, field):
                    bid_qty_raw = getattr(book_ticker, field)
                    if bid_qty_raw:
                        logger.debug(f"{self.exchange_name}: Found bid qty field: {field}")
                        break
            
            # Find ask quantity
            for field in ask_qty_fields:
                if hasattr(book_ticker, field):
                    ask_qty_raw = getattr(book_ticker, field)
                    if ask_qty_raw:
                        logger.debug(f"{self.exchange_name}: Found ask qty field: {field}")
                        break
            
            logger.debug(f"{self.exchange_name}: 💰 Raw data for {symbol} - "
                       f"bid_price: '{bid_price_raw}', ask_price: '{ask_price_raw}', "
                       f"bid_qty: '{bid_qty_raw}', ask_qty: '{ask_qty_raw}'")
            
            # Check if data is empty (initial messages may be empty)
            if not bid_price_raw or not ask_price_raw:
                self.empty_messages += 1
                if self.empty_messages % 5 == 1:  # Log every 5th empty message
                    logger.debug(f"{self.exchange_name}: ⏭️ Empty data #{self.empty_messages} for {symbol} (normal for initial messages)")
                    
                    # ✅ Debug: show all available fields when data is empty
                    available_fields = [attr for attr in dir(book_ticker) if not attr.startswith('_')]
                    logger.debug(f"{self.exchange_name}: Available book ticker fields: {available_fields}")
                return
            
            try:
                # Convert to Decimal
                bid_price = Decimal(str(bid_price_raw))
                ask_price = Decimal(str(ask_price_raw))
                bid_quantity = Decimal(str(bid_qty_raw)) if bid_qty_raw else Decimal('0')
                ask_quantity = Decimal(str(ask_qty_raw)) if ask_qty_raw else Decimal('0')
                
                # Validate prices
                if bid_price <= 0 or ask_price <= 0:
                    logger.warning(f"{self.exchange_name}: ❌ Invalid prices for {symbol}: bid={bid_price}, ask={ask_price}")
                    return
                
                # Log only very occasionally to avoid spam
                if self.successful_parses % 100 == 1:
                    logger.debug(f"{self.exchange_name}: ✅ VALID data for {symbol} - "
                               f"bid: {bid_price}@{bid_quantity}, ask: {ask_price}@{ask_quantity}")
                
                # Save price data
                await self.save_price_data(symbol, bid_price, ask_price, bid_quantity, ask_quantity)
                self.successful_parses += 1
                self.last_data_time = time.time()
                
            except (ValueError, TypeError) as e:
                logger.error(f"{self.exchange_name}: ❌ Price conversion error for {symbol}: {e}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: 💥 Book ticker processing error for {symbol}: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 Handle server pong response"""
        self.server_pong_count += 1
        logger.debug(f"{self.exchange_name}: 🏓 RECEIVED PONG #{self.server_pong_count}: {data}")

    async def _handle_subscription_response(self, data: dict):
        """📨 Handle subscription response"""
        code = data.get('code', -1)
        msg = data.get('msg', '')
        
        if code == 0:
            logger.debug(f"{self.exchange_name}: ✅ Subscription successful: {msg}")
        else:
            logger.error(f"{self.exchange_name}: ❌ Subscription failed - Code: {code}, Msg: {msg}")

    async def _client_ping_task(self):
        """🏓 Send periodic pings according to documentation"""
        logger.info(f"{self.exchange_name}: 🏓 Starting ping task (every {self.config['ping_interval']}s)")
        
        try:
            while self.is_connected and self._listen_task_running:
                try:
                    await asyncio.sleep(self.config['ping_interval'])
                    
                    if not self.is_connected or not self.websocket:
                        break
                        
                    # Send ping according to documentation format
                    ping_msg = {"method": "PING"}
                    await self.websocket.send(json.dumps(ping_msg))
                    
                    self.client_ping_count += 1
                    logger.debug(f"{self.exchange_name}: 🏓 SENT PING #{self.client_ping_count}")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Ping error: {e}")
                    break
                    
        finally:
            logger.info(f"{self.exchange_name}: 🏓 Ping task terminated")

    async def _debug_monitor(self):
        """🐛 Debug monitor with detailed status"""
        logger.info(f"{self.exchange_name}: 🐛 Debug monitor started")
        
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                
                current_time = time.time()
                time_since_data = current_time - self.last_data_time if self.last_data_time > 0 else float('inf')
                
                logger.info(f"{self.exchange_name}: 📊 MEXC Status Report:")
                logger.info(f"  🔗 Endpoint: {self.config['url']}")
                logger.info(f"  ⏱️  Time since last data: {time_since_data:.1f}s")
                logger.info(f"  📝 JSON messages: {self.json_messages}")
                logger.info(f"  📦 Protobuf messages: {self.protobuf_messages}")
                logger.info(f"  ✅ Successful parses: {self.successful_parses}")
                logger.info(f"  ⏭️  Empty messages: {self.empty_messages}")
                logger.info(f"  ❌ Protobuf errors: {self.protobuf_errors}")
                logger.info(f"  🏓 Pings sent: {self.client_ping_count}, Pongs received: {self.server_pong_count}")
                logger.info(f"  📡 Subscribed pairs: {len(self.subscribed_pairs)}")
                
                # Data flow status
                if time_since_data < 30:
                    logger.info(f"{self.exchange_name}: ✅ Data flow healthy")
                elif time_since_data < 60:
                    logger.warning(f"{self.exchange_name}: ⚠️ Data flow slow")
                else:
                    logger.error(f"{self.exchange_name}: ❌ No data for {time_since_data:.1f}s")
                
        except asyncio.CancelledError:
            logger.info(f"{self.exchange_name}: Debug monitor canceled")
        except Exception as e:
            logger.error(f"{self.exchange_name}: Debug monitor error: {e}")

    def is_healthy(self) -> bool:
        """🔍 Health check"""
        if not super().is_healthy():
            return False
            
        current_time = time.time()
        
        # Check data flow
        if self.last_data_time > 0:
            time_since_data = current_time - self.last_data_time
            if time_since_data > 60:  # No data for 1 minute
                logger.warning(f"{self.exchange_name}: ⚠️ No data for {time_since_data:.1f}s")
                return False
        
        return True

    async def reset_state(self):
        """🔄 Reset state"""
        await super().reset_state()
        
        self.subscribed_pairs.clear()
        self.client_ping_count = 0
        self.server_pong_count = 0
        self.protobuf_messages = 0
        self.protobuf_errors = 0
        self.successful_parses = 0
        self.empty_messages = 0
        self.json_messages = 0
        self.last_data_time = 0
        self.subscription_responses.clear()
        self.client_ping_task = None

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Disconnecting MEXC...")
        
        await super().disconnect()
        
        success_rate = (self.successful_parses / self.protobuf_messages * 100) if self.protobuf_messages > 0 else 0
        
        logger.info(f"{self.exchange_name}: 📊 Final MEXC Stats:")
        logger.info(f"  🔗 Endpoint used: {self.config['url']}")
        logger.info(f"  📝 JSON messages: {self.json_messages}")
        logger.info(f"  📦 Protobuf messages: {self.protobuf_messages}")
        logger.info(f"  ✅ Successful parses: {self.successful_parses} ({success_rate:.1f}%)")
        logger.info(f"  ⏭️  Empty messages: {self.empty_messages}")
        logger.info(f"  ❌ Protobuf errors: {self.protobuf_errors}")
        logger.info(f"  🏓 Pings: {self.client_ping_count}, Pongs: {self.server_pong_count}")