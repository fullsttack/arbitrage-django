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

class WallexService(BaseExchangeService):
    """🚀 Wallex Service - Complete Message Debug to Find Missing Pings"""
    
    def __init__(self):
        config = get_config('wallex')
        super().__init__('wallex', config)
        self.subscribed_pairs = set()
        self.pong_count = 0
        self.connection_start_time = 0
        self.partial_data = {}  # Store bid/ask separately
        self.ping_count = 0  # Track received pings
        self.total_messages = 0
        self.depth_messages = 0
        self.non_depth_messages = 0
        self.message_log = []  # Log first 50 non-depth messages
        
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
                close_timeout=10
            )
            
            self.is_connected = True
            self.last_message_time = time.time()
            self.connection_start_time = time.time()
            
            logger.info(f"{self.exchange_name}: Connected successfully")
            logger.warning(f"{self.exchange_name}: 🔍 DEBUGGING MODE: Will log ALL non-depth messages to find server pings")
            
            # Start background tasks and track them
            listen_task = asyncio.create_task(self.listen_loop())
            health_task = asyncio.create_task(self.health_monitor())
            
            self.background_tasks = [listen_task, health_task]
            
            logger.debug(f"{self.exchange_name}: Background tasks started: {len(self.background_tasks)}")
            return True
            
        except Exception as e:
            logger.error(f"{self.exchange_name}: Connect failed: {e}")
            await self.reset_state()
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 Subscribe to pairs (buyDepth and sellDepth)"""
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
                    
                    # Subscribe to buy depth
                    buy_msg = ["subscribe", {"channel": f"{symbol}@buyDepth"}]
                    await self.websocket.send(json.dumps(buy_msg))
                    logger.debug(f"{self.exchange_name}: Sent buyDepth subscription for {symbol}")
                    
                    await asyncio.sleep(0.5)
                    
                    # Subscribe to sell depth
                    sell_msg = ["subscribe", {"channel": f"{symbol}@sellDepth"}]
                    await self.websocket.send(json.dumps(sell_msg))
                    logger.debug(f"{self.exchange_name}: Sent sellDepth subscription for {symbol}")
                    
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)  # Rate limit
                    
                except Exception as e:
                    logger.error(f"{self.exchange_name}: Subscribe error for {symbol}: {e}")
            else:
                logger.debug(f"{self.exchange_name}: Skipping {symbol} - already subscribed")
        
        logger.info(f"{self.exchange_name}: Subscription result: {success_count}/{len(pairs)}")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 Handle incoming messages with COMPLETE DEBUG"""
        self.total_messages += 1
        
        try:
            # Check if it's a simple string first
            message_clean = message.strip()
            
            # Log EVERY non-depth message
            is_depth = False
            try:
                data = json.loads(message)
                if isinstance(data, list) and len(data) == 2:
                    channel = data[0]
                    if isinstance(channel, str) and ('@buyDepth' in channel or '@sellDepth' in channel):
                        is_depth = True
            except:
                pass
            
            if not is_depth:
                self.non_depth_messages += 1
                
                # Log first 50 non-depth messages completely
                if len(self.message_log) < 50:
                    self.message_log.append({
                        'timestamp': time.time(),
                        'message_number': self.total_messages,
                        'raw_message': message,
                        'length': len(message)
                    })
                    
                    logger.warning(f"{self.exchange_name}: 🔍 NON-DEPTH MESSAGE #{self.non_depth_messages}")
                    logger.warning(f"{self.exchange_name}: 🔍 RAW: {message}")
                    logger.warning(f"{self.exchange_name}: 🔍 LENGTH: {len(message)}")
                    logger.warning(f"{self.exchange_name}: 🔍 CLEAN: '{message_clean}'")
            
            # Check for all possible ping formats
            if self._is_possible_ping(message, message_clean):
                await self._handle_possible_ping(message, message_clean)
                return
            
            # Try to parse as JSON
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                if not is_depth:  # Only log non-depth parsing failures
                    logger.warning(f"{self.exchange_name}: 🔍 JSON PARSE FAILED: {message[:100]}")
                return
            
            # Check for JSON ping formats
            if isinstance(data, dict):
                # Standard ping
                if 'ping' in data:
                    await self._handle_json_ping(data)
                    return
                
                # Other possible ping formats
                if any(key in data for key in ['heartbeat', 'keepalive', 'pong', 'ack']):
                    if not is_depth:
                        logger.warning(f"{self.exchange_name}: 🔍 POSSIBLE PING/CONTROL MESSAGE: {data}")
                    return
                
                # Any other dict that's not depth
                if not is_depth:
                    logger.warning(f"{self.exchange_name}: 🔍 OTHER DICT MESSAGE: {data}")
                    return
            
            # Handle depth data [channel_name, data_array]
            if isinstance(data, list) and len(data) == 2:
                await self._handle_depth_data(data)
            else:
                if not is_depth:
                    logger.warning(f"{self.exchange_name}: 🔍 OTHER LIST MESSAGE: {data}")
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Message handling error: {e}")
            logger.error(f"{self.exchange_name}: Problematic message: {message[:200]}")

    def _is_possible_ping(self, message: str, message_clean: str) -> bool:
        """🔍 Check if message could be a ping"""
        # Check simple string pings
        if message_clean.lower() in ['ping', 'pong', '{}', 'heartbeat', 'keepalive']:
            return True
        
        # Check if it's short and might be a ping
        if len(message_clean) < 20 and message_clean.isalnum():
            return True
            
        return False

    async def _handle_possible_ping(self, message: str, message_clean: str):
        """🔍 Handle possible ping messages"""
        logger.warning(f"{self.exchange_name}: 🚨🚨🚨 POSSIBLE PING DETECTED!")
        logger.warning(f"{self.exchange_name}: 🚨 RAW: '{message}'")
        logger.warning(f"{self.exchange_name}: 🚨 CLEAN: '{message_clean}'")
        
        if message_clean.lower() == 'ping':
            self.ping_count += 1
            logger.error(f"{self.exchange_name}: 🏓🏓🏓 STRING PING #{self.ping_count} CONFIRMED!")
            
            # Send pong response
            await self.websocket.send('pong')
            self.pong_count += 1
            logger.error(f"{self.exchange_name}: 🏓🏓🏓 SENT STRING PONG #{self.pong_count}")
            
        elif message_clean in ['{}', 'heartbeat']:
            self.ping_count += 1
            logger.error(f"{self.exchange_name}: 🏓🏓🏓 SPECIAL PING #{self.ping_count}: {message_clean}")
            
            # Try different pong responses
            if message_clean == '{}':
                await self.websocket.send('{}')
                self.pong_count += 1
                logger.error(f"{self.exchange_name}: 🏓🏓🏓 SENT EMPTY JSON PONG #{self.pong_count}")
            else:
                await self.websocket.send('pong')
                self.pong_count += 1
                logger.error(f"{self.exchange_name}: 🏓🏓🏓 SENT STRING PONG #{self.pong_count}")

    async def _handle_json_ping(self, data: dict):
        """🏓 Handle JSON ping"""
        ping_id = data.get('ping')
        self.ping_count += 1
        
        logger.error(f"{self.exchange_name}: 🏓🏓🏓 JSON PING #{self.ping_count} CONFIRMED!")
        logger.error(f"{self.exchange_name}: 🏓 PING DATA: {data}")
        logger.error(f"{self.exchange_name}: 🏓 PING ID: {ping_id}")
        
        if ping_id:
            # Check pong limit
            if self.pong_count >= self.config['max_pongs']:
                logger.error(f"{self.exchange_name}: Max pongs reached ({self.pong_count})")
                self.mark_dead("Max pongs reached")
                return
                
            # Send pong
            pong_msg = {"pong": ping_id}
            await self.websocket.send(json.dumps(pong_msg))
            
            self.pong_count += 1
            logger.error(f"{self.exchange_name}: 🏓🏓🏓 SENT JSON PONG #{self.pong_count}: {ping_id}")

    async def _handle_depth_data(self, data: list):
        """📊 Process depth data (minimal logging)"""
        try:
            channel_name = data[0]
            orders_data = data[1]
            
            if '@buyDepth' in channel_name:
                symbol = channel_name.replace('@buyDepth', '')
                self.depth_messages += 1
                await self._store_order_data(symbol, 'buy', orders_data)
                
            elif '@sellDepth' in channel_name:
                symbol = channel_name.replace('@sellDepth', '')
                self.depth_messages += 1
                await self._store_order_data(symbol, 'sell', orders_data)
                
        except Exception as e:
            logger.error(f"{self.exchange_name}: Depth data processing error: {e}")

    async def _store_order_data(self, symbol: str, order_type: str, orders_data: list):
        """💾 Store order data and save when complete"""
        try:
            if not orders_data:
                return
                
            # Get best order
            best_order = orders_data[0]
            if not isinstance(best_order, dict):
                return
                
            price = Decimal(str(best_order.get('price', 0)))
            volume = Decimal(str(best_order.get('quantity', 0)))
            
            if price <= 0 or volume <= 0:
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
                    
        except Exception as e:
            logger.error(f"{self.exchange_name}: Store order data error for {symbol}: {e}")

    def is_healthy(self) -> bool:
        """🔍 Enhanced health check with message analysis"""
        if not self.is_connected:
            return False
            
        current_time = time.time()
        connection_age = current_time - self.connection_start_time if self.connection_start_time > 0 else 0
        
        # Log detailed stats every 30 seconds
        if int(connection_age) % 30 == 0 and connection_age > 0:
            logger.error(f"{self.exchange_name}: 🔍 DEBUG STATS:")
            logger.error(f"{self.exchange_name}: 🔍   Connection age: {connection_age:.0f}s")
            logger.error(f"{self.exchange_name}: 🔍   Total messages: {self.total_messages}")
            logger.error(f"{self.exchange_name}: 🔍   Depth messages: {self.depth_messages}")
            logger.error(f"{self.exchange_name}: 🔍   Non-depth messages: {self.non_depth_messages}")
            logger.error(f"{self.exchange_name}: 🔍   Server pings received: {self.ping_count}")
            logger.error(f"{self.exchange_name}: 🔍   Pongs sent: {self.pong_count}")
            
            # Expected ping count based on 20-second intervals
            expected_pings = int(connection_age / 20)
            logger.error(f"{self.exchange_name}: 🔍   Expected pings (20s intervals): {expected_pings}")
            
            if expected_pings > 0 and self.ping_count == 0:
                logger.error(f"{self.exchange_name}: 🚨 NO PINGS RECEIVED - SERVER NOT SENDING PINGS!")
        
        # Normal health check
        if self.last_message_time > 0:
            time_since_last = current_time - self.last_message_time
            if time_since_last > 120:  # 2 minutes
                return False
        
        # 30-minute limit
        if connection_age > self.config['max_connection_time']:
            logger.info(f"{self.exchange_name}: 30-minute limit reached - expected behavior")
            return False
            
        return True

    async def reset_state(self):
        """🔄 Reset Wallex-specific state"""
        await super().reset_state()
        
        # Clear subscriptions
        self.subscribed_pairs.clear()
        
        # Reset counters
        self.pong_count = 0
        self.ping_count = 0
        self.connection_start_time = 0
        self.total_messages = 0
        self.depth_messages = 0
        self.non_depth_messages = 0
        self.message_log.clear()
        
        # Clear partial data
        self.partial_data.clear()

    async def disconnect(self):
        """🔌 Disconnect with debug summary"""
        logger.error(f"{self.exchange_name}: 🔍 DISCONNECT DEBUG SUMMARY:")
        logger.error(f"{self.exchange_name}: 🔍   Session duration: {time.time() - self.connection_start_time:.0f}s")
        logger.error(f"{self.exchange_name}: 🔍   Total messages: {self.total_messages}")
        logger.error(f"{self.exchange_name}: 🔍   Depth messages: {self.depth_messages}")
        logger.error(f"{self.exchange_name}: 🔍   Non-depth messages: {self.non_depth_messages}")
        logger.error(f"{self.exchange_name}: 🔍   Server pings: {self.ping_count}")
        logger.error(f"{self.exchange_name}: 🔍   Pongs sent: {self.pong_count}")
        
        # Log first few non-depth messages for analysis
        if self.message_log:
            logger.error(f"{self.exchange_name}: 🔍 FIRST FEW NON-DEPTH MESSAGES:")
            for i, msg in enumerate(self.message_log[:10]):
                logger.error(f"{self.exchange_name}: 🔍   #{i+1}: {msg['raw_message'][:100]}")
        
        # Call parent disconnect
        await super().disconnect()
        
        logger.info(f"{self.exchange_name}: Disconnect completed")