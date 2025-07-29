import asyncio
import json
import logging
import time
import gzip
import io
from decimal import Decimal
from typing import List
import websockets
from .base import BaseExchangeService
from .config import get_config

logger = logging.getLogger(__name__)

class BingXService(BaseExchangeService):
    """🚀 BingX Service - GZIP Compressed WebSocket with Server Ping/Pong"""
    
    def __init__(self):
        config = get_config('bingx')
        super().__init__('bingx', config)
        self.subscribed_pairs = set()
        self.subscription_id = 1
        
        # Ping/Pong stats
        self.server_ping_count = 0
        self.client_pong_count = 0
        
    async def connect(self) -> bool:
        """🔌 Connect to BingX WebSocket"""
        logger.info(f"{self.exchange_name}: Attempting connection to {self.config['url']}")
        
        try:
            await self.reset_state()
            
            self.websocket = await websockets.connect(
                self.config['url'],
                ping_interval=None,  # Handle ping manually
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
        """📡 Subscribe to pairs using BingX format"""
        logger.info(f"{self.exchange_name}: Starting subscription for {len(pairs)} pairs")
        
        if not self.is_connected or not self.websocket:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - not connected")
            return False
        
        success_count = 0
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    # Convert symbol format (e.g., BTCUSDT -> BTC-USDT)
                    bingx_symbol = self._convert_symbol_format(symbol)
                    
                    # Subscribe to bookTicker for arbitrage
                    subscription_msg = {
                        "id": f"bingx_{self.subscription_id}",
                        "reqType": "sub",
                        "dataType": f"{bingx_symbol}@bookTicker"
                    }
                    
                    await self.websocket.send(json.dumps(subscription_msg))
                    logger.debug(f"{self.exchange_name}: 📡 Subscribed to {bingx_symbol}@bookTicker")
                    
                    self.subscribed_pairs.add(symbol)
                    self.subscription_id += 1
                    success_count += 1
                    
                    await asyncio.sleep(0.1)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {symbol}: {e}")
        
        logger.info(f"{self.exchange_name}: Subscription result: {success_count}/{len(pairs)}")
        return success_count > 0

    def _convert_symbol_format(self, symbol: str) -> str:
        """Convert BTCUSDT to BTC-USDT format"""
        # Common base currencies to detect pattern
        bases = ['BTC', 'ETH', 'XRP', 'DOGE', 'NOT', 'ADA', 'DOT', 'LINK']
        
        for base in bases:
            if symbol.upper().startswith(base):
                quote = symbol[len(base):]
                return f"{base}-{quote}"
        
        # Fallback: assume last 4 chars are quote (USDT, BUSD, etc)
        if len(symbol) > 4:
            base = symbol[:-4]
            quote = symbol[-4:]
            return f"{base.upper()}-{quote.upper()}"
        
        # If all else fails, return as-is
        return symbol.upper()

    async def handle_message(self, message):
        """📨 Handle GZIP compressed messages"""
        try:
            # Decompress GZIP data
            if isinstance(message, bytes):
                try:
                    compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
                    decompressed_data = compressed_data.read()
                    utf8_data = decompressed_data.decode('utf-8')
                    logger.debug(f"{self.exchange_name}: 📦 Decompressed message: {utf8_data[:100]}...")
                except Exception as e:
                    logger.error(f"{self.exchange_name}: GZIP decompression failed: {e}")
                    return
            else:
                utf8_data = message
            
            # Handle ping/pong
            if utf8_data.strip() == "Ping":
                await self._handle_server_ping()
                return
            
            # Try to parse as JSON
            try:
                data = json.loads(utf8_data)
                await self._handle_json_message(data)
            except json.JSONDecodeError:
                logger.debug(f"{self.exchange_name}: Non-JSON message: {utf8_data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")

    async def _handle_server_ping(self):
        """🏓 Handle server ping"""
        try:
            self.server_ping_count += 1
            logger.debug(f"{self.exchange_name}: 🏓 RECEIVED SERVER PING #{self.server_ping_count}")
            
            if self.websocket and self.is_connected:
                await self.websocket.send("Pong")
                self.client_pong_count += 1
                logger.debug(f"{self.exchange_name}: 🏓 SENT CLIENT PONG #{self.client_pong_count}")
            else:
                logger.error(f"{self.exchange_name}: Cannot send PONG - no websocket or disconnected")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Ping handling error: {e}")

    async def _handle_json_message(self, data: dict):
        """📨 Handle JSON messages"""
        try:
            # Handle subscription confirmation
            if 'code' in data and 'id' in data:
                await self._handle_subscription_response(data)
                return
            
            # Handle market data
            if 'dataType' in data and 'data' in data:
                await self._handle_market_data(data)
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: JSON message handling error: {e}")

    async def _handle_subscription_response(self, data: dict):
        """📨 Handle subscription response"""
        code = data.get('code', -1)
        msg = data.get('msg', '')
        sub_id = data.get('id', '')
        
        if code == 0:
            logger.debug(f"{self.exchange_name}: ✅ Subscription successful: {sub_id}")
        else:
            logger.error(f"{self.exchange_name}: ❌ Subscription failed - ID: {sub_id}, Code: {code}, Msg: {msg}")

    async def _handle_market_data(self, message: dict):
        """📊 Handle market data (bookTicker)"""
        try:
            data_type = message.get('dataType', '')
            market_data = message.get('data', {})
            
            if '@bookTicker' in data_type:
                # Extract symbol (e.g., "BTC-USDT@bookTicker" -> "BTC-USDT")
                symbol_part = data_type.split('@')[0]
                # Convert back to our format (BTC-USDT -> BTCUSDT)
                symbol = symbol_part.replace('-', '')
                
                await self._process_book_ticker(symbol, market_data)
            else:
                logger.debug(f"{self.exchange_name}: Unhandled data type: {data_type}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Market data handling error: {e}")

    async def _process_book_ticker(self, symbol: str, data: dict):
        """💰 Process book ticker data"""
        try:
            logger.debug(f"{self.exchange_name}: Processing book ticker for {symbol}")
            
            # Extract bid/ask data
            bid_price_raw = data.get('b')  # Best bid price
            ask_price_raw = data.get('a')  # Best ask price
            bid_qty_raw = data.get('B')    # Best bid quantity
            ask_qty_raw = data.get('A')    # Best ask quantity
            
            logger.debug(f"{self.exchange_name}: Raw data for {symbol} - "
                       f"bid: {bid_price_raw}@{bid_qty_raw}, ask: {ask_price_raw}@{ask_qty_raw}")
            
            # Check if data is valid
            if not bid_price_raw or not ask_price_raw:
                logger.debug(f"{self.exchange_name}: Empty price data for {symbol}")
                return
            
            try:
                # Convert to Decimal
                bid_price = Decimal(str(bid_price_raw))
                ask_price = Decimal(str(ask_price_raw))
                bid_quantity = Decimal(str(bid_qty_raw)) if bid_qty_raw else Decimal('0')
                ask_quantity = Decimal(str(ask_qty_raw)) if ask_qty_raw else Decimal('0')
                
                # Validate prices
                if bid_price <= 0 or ask_price <= 0:
                    logger.warning(f"{self.exchange_name}: Invalid prices for {symbol}")
                    return
                
                # Log occasionally to avoid spam
                if self.message_count % 100 == 1:
                    logger.debug(f"{self.exchange_name}: ✅ Valid data for {symbol} - "
                               f"bid: {bid_price}@{bid_quantity}, ask: {ask_price}@{ask_quantity}")
                
                # Save price data
                await self.save_price_data(symbol, bid_price, ask_price, bid_quantity, ask_quantity)
                
            except (ValueError, TypeError) as e:
                logger.error(f"{self.exchange_name}: Price conversion error for {symbol}: {e}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Book ticker processing error for {symbol}: {e}")

    async def _status_monitor(self):
        """📊 Status monitor with detailed reporting"""
        logger.info(f"{self.exchange_name}: 📊 Status monitor started")
        
        try:
            while self.is_connected:
                await asyncio.sleep(30)
                
                current_time = time.time()
                time_since_data = current_time - self.last_data_time if self.last_data_time > 0 else float('inf')
                
                logger.info(f"{self.exchange_name}: 📊 BINGX Status Report:")
                logger.info(f"  🔗 Endpoint: {self.config['url']}")
                logger.info(f"  ⏱️  Time since last data: {time_since_data:.1f}s")
                logger.info(f"  📝 Messages processed: {self.message_count}")
                logger.info(f"  🏓 Server pings received: {self.server_ping_count}")
                logger.info(f"  🏓 Client pongs sent: {self.client_pong_count}")
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
        """🔍 BingX health check"""
        if not super().is_healthy():
            return False
        
        # Check ping/pong ratio
        if self.server_ping_count > 0:
            pong_ratio = self.client_pong_count / self.server_ping_count
            if pong_ratio < 0.8:  # Less than 80% response rate
                logger.warning(f"{self.exchange_name}: Low ping/pong response rate: {pong_ratio:.2f}")
        
        return True

    async def reset_state(self):
        """🔄 Reset BingX-specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting BingX-specific state")
        
        # Clear subscriptions
        self.subscribed_pairs.clear()
        
        # Reset counters
        self.subscription_id = 1
        self.server_ping_count = 0
        self.client_pong_count = 0
        
        logger.debug(f"{self.exchange_name}: BingX state reset completed")

    async def disconnect(self):
        """🔌 Disconnect"""
        logger.info(f"{self.exchange_name}: Starting BingX disconnect")
        
        await super().disconnect()
        
        logger.info(f"{self.exchange_name}: BingX disconnect completed")
        logger.info(f"{self.exchange_name}: Session stats - "
                   f"Server pings: {self.server_ping_count}, Client pongs: {self.client_pong_count}")