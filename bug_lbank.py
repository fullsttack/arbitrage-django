#!/usr/bin/env python3
"""
🔥 LBank Full Production Test
Includes Redis, Channel Layer, and all production interactions to reproduce the EXACT issue
"""

import asyncio
import json
import logging
import time
import signal
import sys
from decimal import Decimal
from typing import List, Dict, Any, Optional
import websockets

# Setup exact production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(asctime)s,%(msecs)03d %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lbank_full_production_test.log')
    ]
)
logger = logging.getLogger(__name__)

class MockRedisManager:
    """🔧 Mock Redis Manager to simulate Redis interactions"""
    
    def __init__(self):
        self.is_connected = False
        self.save_calls = 0
        self.save_errors = 0
        
    async def connect(self):
        """Mock Redis connection"""
        await asyncio.sleep(0.01)  # Simulate connection delay
        self.is_connected = True
        
    async def save_price_data(self, exchange: str, symbol: str, bid_price: float, ask_price: float, 
                             bid_volume: float = 0, ask_volume: float = 0):
        """Mock save price data with potential delays/errors"""
        self.save_calls += 1
        
        # Simulate Redis latency
        await asyncio.sleep(0.001)
        
        # Simulate occasional Redis errors (like production)
        if self.save_calls % 1000 == 0:  # Every 1000th call fails
            self.save_errors += 1
            raise Exception(f"Redis timeout #{self.save_errors}")

class MockChannelLayer:
    """🔧 Mock Channel Layer to simulate WebSocket broadcasting"""
    
    def __init__(self):
        self.broadcast_calls = 0
        self.broadcast_errors = 0
        
    async def group_send(self, group_name: str, message: dict):
        """Mock group send with potential delays/errors"""
        self.broadcast_calls += 1
        
        # Simulate channel layer latency
        await asyncio.sleep(0.002)
        
        # Simulate occasional broadcast errors (like production)
        if self.broadcast_calls % 500 == 0:  # Every 500th call fails
            self.broadcast_errors += 1
            raise Exception(f"Channel layer timeout #{self.broadcast_errors}")

class BaseExchangeServiceFullTest:
    """🔥 Full production replica including all interactions"""
    
    def __init__(self, exchange_name: str, config: Dict[str, Any]):
        self.exchange_name = exchange_name
        self.config = config
        self.websocket = None
        self.is_connected = False
        
        # Production-exact tracking
        self.last_message_time = 0
        self.last_data_time = 0
        self.message_count = 0
        self._last_broadcast = {}
        
        # Mock production dependencies
        self.redis_manager = MockRedisManager()
        self.channel_layer = MockChannelLayer()
        
        # Test tracking
        self.save_price_calls = 0
        self.broadcast_calls = 0
        self.redis_errors = 0
        self.broadcast_errors = 0

    async def init_redis(self):
        """Initialize Redis like production"""
        if not self.redis_manager.is_connected:
            await self.redis_manager.connect()

    async def save_price_data(self, symbol: str, bid_price: Decimal, ask_price: Decimal, 
                             bid_volume: Decimal = Decimal('0'), ask_volume: Decimal = Decimal('0')):
        """💾 EXACT replica of production save_price_data with all interactions"""
        current_time = time.time()
        self.last_data_time = current_time
        self.save_price_calls += 1
        
        try:
            # Initialize Redis if needed (like production)
            await self.init_redis()
            
            # Save to Redis (like production) - THIS CAN CAUSE DELAYS/ERRORS
            await self.redis_manager.save_price_data(
                exchange=self.exchange_name,
                symbol=symbol,
                bid_price=float(bid_price),
                ask_price=float(ask_price),
                bid_volume=float(bid_volume),
                ask_volume=float(ask_volume)
            )
            
            # Throttled broadcast (like production) - THIS CAN ALSO CAUSE DELAYS/ERRORS
            key = f"{symbol}"
            if current_time - self._last_broadcast.get(key, 0) > 2:
                try:
                    await self.channel_layer.group_send('arbitrage_updates', {
                        'type': 'send_price_update',
                        'price_data': {
                            'exchange': self.exchange_name,
                            'symbol': symbol,
                            'bid_price': float(bid_price),
                            'ask_price': float(ask_price),
                            'bid_volume': float(bid_volume),
                            'ask_volume': float(ask_volume),
                            'timestamp': current_time
                        }
                    })
                    self._last_broadcast[key] = current_time
                    self.broadcast_calls += 1
                except Exception as e:
                    self.broadcast_errors += 1
                    # Don't let broadcast errors stop the function (like production)
                    pass
                    
        except Exception as e:
            self.redis_errors += 1
            # Production would log this but continue
            logger.debug(f"❌ {self.exchange_name} Redis error #{self.redis_errors}: {e}")

    def update_message_time(self):
        """📡 Update message tracking (production replica)"""
        self.last_message_time = time.time()
        self.message_count += 1

    def is_healthy(self) -> bool:
        """🔍 EXACT production health check"""
        if not self.is_connected:
            return False
        
        current_time = time.time()
        
        # EXACT same 30-second timeout as production
        if self.last_message_time > 0 and current_time - self.last_message_time > 30:
            return False
            
        return True

    def mark_dead(self, reason: str = ""):
        """💀 Mark connection as dead (production replica)"""
        self.is_connected = False
        if reason:
            logger.warning(f"{self.exchange_name}: {reason}")

    async def connect_with_retries(self, max_retries: int = 3) -> bool:
        """🔄 EXACT replica of production connection with retries"""
        for attempt in range(max_retries):
            try:
                if await self.connect():
                    return True
                await asyncio.sleep(2 ** attempt)  # exponential backoff
            except Exception as e:
                logger.error(f"{self.exchange_name} attempt {attempt + 1}: {e}")
        return False

    async def listen_loop(self):
        """👂 EXACT production listen_loop"""
        try:
            while self.is_connected and self.websocket:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                self.update_message_time()
                await self.handle_message(message)
        except Exception as e:
            self.mark_dead(f"Listen error: {e}")

    async def health_monitor(self):
        """💓 EXACT production health monitoring"""
        while self.is_connected:
            await asyncio.sleep(10)
            if not self.is_healthy():
                self.mark_dead("Health check failed")
                break

    async def disconnect(self):
        """🔌 Clean disconnect"""
        self.is_connected = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        self.websocket = None

    # Abstract methods
    async def connect(self) -> bool:
        pass
    
    async def handle_message(self, message: str):
        pass
    
    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        pass

class LBankFullProductionTest(BaseExchangeServiceFullTest):
    """🔥 LBank with FULL production interactions"""
    
    def __init__(self):
        config = {
            'url': 'wss://www.lbkex.net/ws/V2/',
            'ping_interval': 60,
            'timeout': 120,
            'subscribe_format': {
                "action": "subscribe",
                "subscribe": "depth", 
                "pair": "{symbol}",
                "depth": "100"
            }
        }
        super().__init__('lbank', config)
        self.subscribed_pairs = set()
        self.ping_counter = 1
        
        # Additional tracking
        self.connection_start_time = 0
        self.depth_messages = 0
        self.ping_errors = 0
        self.subscription_attempts = 0
        self.subscription_successes = 0

    async def connect(self) -> bool:
        """🔌 EXACT production connect"""
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
            self.connection_start_time = time.time()
            
            # EXACT same task creation as production
            asyncio.create_task(self.listen_loop())
            asyncio.create_task(self.health_monitor())
            asyncio.create_task(self._client_ping_task())
            
            logger.info("LBank connected")
            return True
            
        except Exception as e:
            logger.error(f"❌ LBank connect failed: {e}")
            return False

    async def subscribe_to_pairs(self, pairs: List[str]) -> bool:
        """📡 EXACT production subscription"""
        if not self.is_connected:
            return False
            
        success_count = 0
        
        for symbol in pairs:
            if symbol not in self.subscribed_pairs:
                try:
                    self.subscription_attempts += 1
                    
                    msg = self.config['subscribe_format'].copy()
                    msg['pair'] = symbol
                    
                    await self.websocket.send(json.dumps(msg))
                    self.subscribed_pairs.add(symbol)
                    success_count += 1
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ LBank subscribe error {symbol}: {e}")
        
        if success_count > 0:
            self.subscription_successes = success_count
        
        logger.info(f"LBank subscribed to {success_count}/{len(pairs)} pairs")
        return success_count > 0

    async def handle_message(self, message: str):
        """📨 EXACT production message handling"""
        try:
            data = json.loads(message)
            
            if isinstance(data, dict) and data.get('action') == 'ping':
                await self._handle_server_ping(data)
                
            elif isinstance(data, dict) and data.get('action') == 'pong':
                await self._handle_server_pong(data)
                
            elif data.get('type') == 'depth' and 'depth' in data:
                await self._handle_depth_data(data)
                
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"❌ LBank message error: {e}")

    async def _handle_server_ping(self, data: dict):
        """🏓 EXACT production server ping handling"""
        try:
            ping_id = data.get('ping')
            if ping_id:
                pong_msg = {"action": "pong", "pong": ping_id}
                await self.websocket.send(json.dumps(pong_msg))
                logger.debug(f"🏓 LBank server PING->PONG: {ping_id}")
                
        except Exception as e:
            logger.error(f"❌ LBank server ping error: {e}")

    async def _handle_server_pong(self, data: dict):
        """📨 EXACT production server pong handling"""
        pong_id = data.get('pong')
        logger.debug(f"📨 LBank server PONG received: {pong_id}")

    async def _handle_depth_data(self, data: dict):
        """📊 EXACT production depth data processing WITH ALL INTERACTIONS"""
        try:
            depth = data.get('depth', {})
            symbol = data.get('pair', '')
            
            if not symbol:
                return
                
            self.depth_messages += 1
            asks = depth.get('asks', [])
            bids = depth.get('bids', [])
            
            if asks and bids:
                ask_price = Decimal(str(asks[0][0]))
                ask_volume = Decimal(str(asks[0][1]))
                bid_price = Decimal(str(bids[0][0]))
                bid_volume = Decimal(str(bids[0][1]))
                
                # THIS IS THE CRITICAL PART - CALL save_price_data WITH ALL INTERACTIONS
                # This involves Redis calls + Channel layer broadcasts
                await self.save_price_data(symbol, bid_price, ask_price, bid_volume, ask_volume)
                
        except Exception as e:
            logger.error(f"❌ LBank depth error: {e}")

    async def _client_ping_task(self):
        """🏓 EXACT production client ping task"""
        while self.is_connected:
            try:
                await asyncio.sleep(self.config['ping_interval'])
                
                if not self.is_connected:
                    break
                    
                ping_id = f"client-{self.ping_counter}-{int(time.time())}"
                ping_msg = {"action": "ping", "ping": ping_id}
                
                # THIS IS WHERE RACE CONDITION CAN HAPPEN
                await self.websocket.send(json.dumps(ping_msg))
                self.ping_counter += 1
                
                logger.debug(f"🏓 LBank client PING sent: {ping_id}")
                
            except Exception as e:
                error_msg = str(e).lower()
                if "recv" in error_msg and ("running" in error_msg or "streaming" in error_msg):
                    logger.error(f"🔥 LBank PING RECV ERROR: {e}")
                else:
                    logger.error(f"❌ LBank client ping error: {e}")
                self.ping_errors += 1
                break

class FullProductionSimulator:
    """🏭 Full production environment simulator with ALL components"""
    
    def __init__(self):
        self.services = {'lbank': LBankFullProductionTest()}
        self.test_pairs = ['xrp_usdt', 'doge_usdt', 'eth_usdt', 'btc_usdt']
        self.is_running = False
        
        # Simulate multiple arbitrage calculators (like production)
        self.calculator_tasks = []
        
        # Production-like config
        self.config = {
            'connection_retry_interval': 2,
            'health_check_interval': 5,
            'max_connection_failures': 5
        }
        
        # Test tracking
        self.start_time = time.time()
        self.reconnections = 0
        self.total_errors = 0

    async def start_full_simulation(self, test_duration: int = 3600):
        """🚀 Start full production simulation"""
        self.is_running = True
        logger.info("🚀 Starting optimized arbitrage workers...")
        
        try:
            # Start multiple arbitrage calculators (like production)
            for i in range(3):
                task = asyncio.create_task(self._mock_arbitrage_calculator(i))
                self.calculator_tasks.append(task)
            
            # Start exchange worker (like production)
            exchange_task = asyncio.create_task(self._exchange_worker_full('lbank', self.test_pairs))
            
            # Start system monitor (like production)
            monitor_task = asyncio.create_task(self._system_monitor())
            
            # Wait for test duration
            await asyncio.wait_for(
                asyncio.gather(exchange_task, monitor_task, *self.calculator_tasks), 
                timeout=test_duration
            )
            
        except asyncio.TimeoutError:
            logger.info(f"⏰ Full simulation completed after {test_duration} seconds")
        except Exception as e:
            logger.error(f"❌ Full simulation error: {e}")
        finally:
            await self.stop_full_simulation()

    async def _mock_arbitrage_calculator(self, calculator_id: int):
        """🧮 Mock arbitrage calculator (like production)"""
        logger.info("🚀 Fast arbitrage calculator started")
        
        while self.is_running:
            try:
                # Simulate arbitrage calculation workload
                await asyncio.sleep(0.15)  # Same interval as production
                
                # Simulate Redis reads (like production calculators)
                service = self.services['lbank']
                if hasattr(service.redis_manager, 'save_calls'):
                    # Simulate reading price data
                    await asyncio.sleep(0.001)
                
            except Exception as e:
                logger.error(f"❌ Calculator {calculator_id} error: {e}")

    async def _exchange_worker_full(self, exchange_name: str, pairs: List[str]):
        """📡 EXACT production exchange worker"""
        service = self.services[exchange_name]
        failures = 0
        max_failures = self.config['max_connection_failures']
        retry_interval = self.config['connection_retry_interval']
        
        logger.info(f"✅ Started {exchange_name} worker with {len(pairs)} pairs")
        
        while self.is_running:
            try:
                # Check connection
                if not service.is_connected:
                    self.reconnections += 1
                    
                    if await service.connect_with_retries():
                        if await service.subscribe_to_pairs(pairs):
                            failures = 0
                            logger.info(f"✅ {exchange_name} connected and subscribed")
                        else:
                            failures += 1
                            logger.warning(f"❌ {exchange_name} subscription failed")
                    else:
                        failures += 1
                        logger.warning(f"❌ {exchange_name} connection failed")
                
                elif not service.is_healthy():
                    logger.warning(f"⚠️ {exchange_name} health check failed")
                    service.mark_dead("Health check failed")
                    failures += 1
                
                if failures >= max_failures:
                    logger.error(f"💀 {exchange_name} permanently failed after {failures} attempts")
                    break
                
                await asyncio.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                failures += 1
                self.total_errors += 1
                logger.error(f"❌ {exchange_name} worker error: {e}")
                service.mark_dead(f"Worker error: {e}")
                
                if failures < max_failures:
                    await asyncio.sleep(retry_interval)
                else:
                    break
        
        try:
            await service.disconnect()
            logger.info(f"🔌 {exchange_name} disconnected")
        except Exception as e:
            logger.error(f"❌ {exchange_name} cleanup error: {e}")

    async def _system_monitor(self):
        """📊 EXACT production system monitoring"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Every minute like production
                
                service = self.services['lbank']
                connected_exchanges = 1 if service.is_connected else 0
                
                logger.info(f"📊 System Status: Exchanges: {connected_exchanges}/1, Calculators: {len(self.calculator_tasks)}/3")
                
            except Exception as e:
                logger.error(f"❌ System monitor error: {e}")

    async def stop_full_simulation(self):
        """🛑 Stop full simulation"""
        self.is_running = False
        
        # Stop calculators
        for task in self.calculator_tasks:
            if not task.done():
                task.cancel()
        
        # Disconnect services
        for service in self.services.values():
            try:
                await service.disconnect()
            except Exception as e:
                logger.error(f"❌ Service disconnect error: {e}")
        
        # Generate final report
        await self._generate_full_report()

    async def _generate_full_report(self):
        """📋 Generate comprehensive production report"""
        total_time = time.time() - self.start_time
        service = self.services['lbank']
        
        uptime = 0
        if service.connection_start_time > 0:
            uptime = time.time() - service.connection_start_time
        
        report = f"""
🔥 FULL PRODUCTION SIMULATION REPORT
===================================

⏱️  Total Test Time: {total_time:.0f} seconds ({total_time/60:.1f} minutes)
🔄 Reconnection Attempts: {self.reconnections}
🏭 Worker Errors: {self.total_errors}

🔌 CONNECTION ANALYSIS:
  • Current uptime: {uptime:.0f} seconds ({uptime/60:.1f} minutes)
  • Ping errors: {service.ping_errors}

📡 SUBSCRIPTION ANALYSIS:
  • Subscription attempts: {service.subscription_attempts}
  • Subscription successes: {service.subscription_successes}
  • Success rate: {service.subscription_successes/max(1,service.subscription_attempts)*100:.1f}%

📨 MESSAGE & DATA FLOW:
  • Total messages: {service.message_count}
  • Depth messages: {service.depth_messages}
  • save_price_data calls: {service.save_price_calls}
  • Redis errors: {service.redis_errors}
  • Broadcast calls: {service.broadcast_calls}
  • Broadcast errors: {service.broadcast_errors}

🔥 INTERACTION ANALYSIS:
  • Redis save calls: {service.redis_manager.save_calls}
  • Redis errors: {service.redis_manager.save_errors}
  • Channel broadcasts: {service.channel_layer.broadcast_calls}
  • Channel errors: {service.channel_layer.broadcast_errors}

🎯 ROOT CAUSE DIAGNOSIS:
"""
        
        # Detailed analysis
        if service.subscription_successes == 0 and service.subscription_attempts > 0:
            report += "  🔥 CRITICAL: Subscription failure detected\n"
        
        if service.ping_errors > 0:
            report += f"  🔥 CRITICAL: {service.ping_errors} ping errors (race condition source)\n"
        
        if service.redis_errors > 0:
            report += f"  ⚠️ Redis interaction issues: {service.redis_errors} errors\n"
        
        if service.broadcast_errors > 0:
            report += f"  ⚠️ Channel layer issues: {service.broadcast_errors} errors\n"
        
        # Calculate interaction load
        interactions_per_second = (service.save_price_calls + service.broadcast_calls) / max(1, uptime)
        report += f"  📊 Interaction load: {interactions_per_second:.2f} ops/sec\n"
        
        if interactions_per_second > 10:
            report += "  ⚠️ High interaction load may cause timing issues\n"
        
        report += f"""
💡 PRODUCTION ISSUE SIMULATION:
  • Pattern matches production: {'Yes' if service.subscription_successes == 0 else 'No'}
  • Race condition reproduced: {'Yes' if service.ping_errors > 0 else 'No'}
  • Health check sensitivity: {'High' if uptime < 300 else 'Normal'}
"""
        
        logger.info(report)
        
        with open('lbank_full_production_report.txt', 'w') as f:
            f.write(report)
        
        logger.info("📄 Full production report saved")

async def main():
    """🚀 Main full production simulation"""
    print("🔥 LBank FULL Production Simulation")
    print("===================================")
    print("This simulation includes ALL production components:")
    print("  • Redis interactions")
    print("  • Channel layer broadcasting") 
    print("  • Multiple arbitrage calculators")
    print("  • WorkersManager behavior")
    print("  • Health check logic")
    print("  • Full message flow")
    print("")
    print("🎯 This should reproduce the EXACT production issue!")
    print("")
    print("📝 Logs: lbank_full_production_test.log")
    print("📄 Report: lbank_full_production_report.txt")
    print("🛑 Press Ctrl+C to stop")
    
    simulator = FullProductionSimulator()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("🛑 Received interrupt signal")
        simulator.is_running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await simulator.start_full_simulation(test_duration=1800)  # 30 minutes
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Main error: {e}")
    finally:
        logger.info("✅ Full production simulation completed")

if __name__ == "__main__":
    asyncio.run(main())