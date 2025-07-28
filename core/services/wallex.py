import asyncio
import logging
import time
from decimal import Decimal
from typing import List
import socketio
from .base import BaseExchangeService
from .config import get_config

logger = logging.getLogger(__name__)

class WallexService(BaseExchangeService):
    """🚀 Wallex Service - Socket.IO Implementation (Fixed)"""
    
    def __init__(self):
        config = get_config('wallex')
        super().__init__('wallex', config)
        
        # Socket.IO client
        self.sio = None
        self.subscribed_pairs = set()
        
        # Market data storage
        self.partial_data = {}
        
        # Stats
        self.broadcaster_events = 0
        self.market_data_processed = 0
        
    async def connect(self) -> bool:
        """🔌 Socket.IO connection"""
        logger.info(f"{self.exchange_name}: Attempting Socket.IO connection")
        
        try:
            # Reset state before connecting
            await self.reset_state()
            
            # Create Socket.IO client
            self.sio = socketio.AsyncClient(
                logger=False,
                engineio_logger=False
            )
            
            # Setup event handlers
            self._setup_socketio_handlers()
            
            # Connect to Wallex
            await self.sio.connect(
                "https://api.wallex.ir",
                transports=['websocket'],
                wait_timeout=10
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            
            logger.info(f"{self.exchange_name}: Socket.IO connected successfully")
            
            # Start health monitoring (Socket.IO handles ping/pong automatically)
            health_task = asyncio.create_task(self.health_monitor())
            self.background_tasks = [health_task]
            
            logger.debug(f"{self.exchange_name}: Background tasks started: {len(self.background_tasks)}")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Socket.IO connect failed: {e}")
            await self.reset_state()
            return False
    
    def _setup_socketio_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        async def connect():
            """Socket.IO connected"""
            logger.info(f"{self.exchange_name}: Socket.IO session connected")
        
        @self.sio.event 
        async def disconnect():
            """Socket.IO disconnected"""
            logger.warning(f"{self.exchange_name}: Socket.IO session disconnected")
            self.mark_dead("Socket.IO disconnected")
        
        @self.sio.event
        async def connect_error(data):
            """Socket.IO connection error"""
            logger.error(f"{self.exchange_name}: Socket.IO connection error: {data}")
            self.mark_dead(f"Socket.IO error: {data}")
        
        # Main event handler for market data
        @self.sio.on('Broadcaster')
        async def handle_broadcaster(channel_name, *args):
            """Handle Broadcaster events - actual market data"""
            try:
                self.broadcaster_events += 1
                self.update_message_time()
                
                logger.debug(f"{self.exchange_name}: Broadcaster event #{self.broadcaster_events}: {channel_name}")
                
                # Market data is in args[0]
                if args and len(args) > 0:
                    market_data = args[0]
                    
                    if isinstance(market_data, dict):
                        await self._process_market_data(channel_name, market_data)
                    else:
                        logger.debug(f"{self.exchange_name}: No market data in args: {type(market_data)}")
                else:
                    logger.debug(f"{self.exchange_name}: No args in Broadcaster event")
                    
            except Exception as e:
                logger.error(f"{self.exchange_name}: Error in Broadcaster handler: {e}")
        
        # Handle subscription responses
        @self.sio.event
        async def subscribe(data):
            """Handle subscription responses"""
            logger.debug(f"{self.exchange_name}: Subscription response: {data}")
    
    async def _process_market_data(self, channel_name: str, market_data: dict):
        """Process market data from Broadcaster events"""
        try:
            self.market_data_processed += 1
            
            # Extract symbol from channel
            if '@' not in channel_name:
                return
            
            symbol, channel_type = channel_name.split('@', 1)
            
            # Convert indexed dict to list of orders
            orders = []
            for key in sorted(market_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
                if key != 'socket' and isinstance(market_data[key], dict):
                    order = market_data[key]
                    if 'price' in order and 'quantity' in order:
                        orders.append(order)
            
            if not orders:
                logger.debug(f"{self.exchange_name}: No valid orders in {channel_name}")
                return
            
            logger.debug(f"{self.exchange_name}: Processing {len(orders)} orders for {channel_name}")
            
            # Process based on channel type
            if channel_type == 'buyDepth':
                await self._store_order_data(symbol, 'buy', orders)
            elif channel_type == 'sellDepth':
                await self._store_order_data(symbol, 'sell', orders)
            else:
                logger.debug(f"{self.exchange_name}: Ignoring channel type: {channel_type}")
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Error processing market data: {e}")
    
    async def _store_order_data(self, symbol: str, order_type: str, orders: List[dict]):
        """Store order data and save when complete"""
        try:
            if not orders:
                return
            
            # Get best order (first one)
            best_order = orders[0]
            price = Decimal(str(best_order.get('price', 0)))
            volume = Decimal(str(best_order.get('quantity', 0)))
            
            if price <= 0 or volume <= 0:
                logger.debug(f"{self.exchange_name}: Invalid price/volume for {symbol}: {price}/{volume}")
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
            else:  # sell
                data['ask_price'] = price
                data['ask_volume'] = volume  
                data['ask_time'] = current_time
            
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
                    logger.debug(f"{self.exchange_name}: 💾 Saved price data for {symbol}")
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Store order data error for {symbol}: {e}")

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to trading pairs using Socket.IO"""
        logger.info(f"{self.exchange_name}: Starting Socket.IO subscription for {len(pairs)} pairs")
        logger.debug(f"{self.exchange_name}: Current subscribed pairs: {self.subscribed_pairs}")
        logger.debug(f"{self.exchange_name}: Pairs to subscribe: {pairs}")
        
        if not self.is_connected or not self.sio:
            logger.warning(f"{self.exchange_name}: Cannot subscribe - not connected")
            return False
        
        success_count = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    logger.debug(f"{self.exchange_name}: Subscribing to {symbol}")
                    
                    # Subscribe to buy depth
                    await self.sio.emit('subscribe', {'channel': f'{symbol}@buyDepth'})
                    logger.debug(f"{self.exchange_name}: Sent buyDepth subscription for {symbol}")
                    
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to sell depth
                    await self.sio.emit('subscribe', {'channel': f'{symbol}@sellDepth'})
                    logger.debug(f"{self.exchange_name}: Sent sellDepth subscription for {symbol}")
                    
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {symbol}: {e}")
            else:
                logger.debug(f"{self.exchange_name}: Skipping {symbol} - already subscribed")
        
        logger.info(f"{self.exchange_name}: Socket.IO subscription result: {success_count}/{len(pairs)}")
        return success_count > 0

    def is_healthy(self) -> bool:
        """🔍 Health check - Socket.IO handles ping/pong automatically"""
        if not self.is_connected or not self.sio or not self.sio.connected:
            logger.debug(f"{self.exchange_name}: Health check - not connected")
            return False
        
        current_time = time.time()
        
        # Check message flow (extended timeout since Socket.IO is more reliable)
        if self.last_message_time > 0:
            time_since_last = current_time - self.last_message_time
            logger.debug(f"{self.exchange_name}: Health check - last message {time_since_last:.1f}s ago")
            
            if time_since_last > 120:  # 2 minutes timeout
                logger.warning(f"{self.exchange_name}: Health check failed - no messages for {time_since_last:.1f}s")
                return False
        
        return True

    async def reset_state(self):
        """🔄 Reset Socket.IO specific state"""
        await super().reset_state()
        
        logger.debug(f"{self.exchange_name}: Resetting Socket.IO specific state")
        
        # Clear subscriptions
        logger.debug(f"{self.exchange_name}: Clearing {len(self.subscribed_pairs)} subscribed pairs")
        self.subscribed_pairs.clear()
        
        # Reset stats
        self.broadcaster_events = 0
        self.market_data_processed = 0
        
        # Clear partial data
        self.partial_data.clear()
        
        # Close Socket.IO if connected
        if self.sio and self.sio.connected:
            try:
                await self.sio.disconnect()
                logger.debug(f"{self.exchange_name}: Socket.IO disconnected")
            except Exception as e:
                logger.warning(f"{self.exchange_name}: Error disconnecting Socket.IO: {e}")
        
        self.sio = None
        
        logger.debug(f"{self.exchange_name}: Socket.IO state reset completed")

    async def handle_message(self, message: str):
        """📨 Handle message - Not used in Socket.IO (events handled by decorators)"""
        # This method is required by BaseExchangeService but not used in Socket.IO
        # All message handling is done through Socket.IO event decorators
        logger.debug(f"{self.exchange_name}: handle_message called but not used in Socket.IO: {message[:100]}")
        pass

    async def disconnect(self):
        """🔌 Disconnect Socket.IO"""
        logger.info(f"{self.exchange_name}: Starting Socket.IO disconnect")
        
        # Call parent disconnect first
        await super().disconnect()
        
        # Socket.IO specific cleanup already handled in reset_state
        logger.info(f"{self.exchange_name}: Socket.IO disconnect completed")
        logger.info(f"{self.exchange_name}: Session stats - Broadcaster events: {self.broadcaster_events}, Market data processed: {self.market_data_processed}")