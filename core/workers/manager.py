import asyncio
import logging
import time
from typing import Dict, List
from django.conf import settings
from channels.db import database_sync_to_async

# Import our optimized services
from ..services.wallex import WallexService
from ..services.lbank import LBankService
from ..services.ramzinex import RamzinexService
from ..services.tabdeal import TabdealService
from ..services.bitpin import BitpinService
from ..services.mexc import MexcService
from ..arbitrage import FastArbitrageCalculator
from ..models import TradingPair
from ..redis import redis_manager
from ..config_manager import get_worker_config

logger = logging.getLogger(__name__)

class SimpleWorkersManager:
    """🚀 Simple and Fast Workers Manager"""
    
    def __init__(self, config_profile: str = 'default'):
        self.config = get_worker_config(config_profile)
        self.is_running = False
        self.tasks = []
        
        # Exchange services
        self.services = {
            'wallex': WallexService(),
            'lbank': LBankService(),
            'ramzinex': RamzinexService(),
            'tabdeal': TabdealService(),
            'bitpin': BitpinService(),
            'mexc': MexcService()
        }
        
        # Arbitrage calculators
        self.calculators = []
        for i in range(self.config['arbitrage_calculators']):
            self.calculators.append(FastArbitrageCalculator())
        
        logger.info(f"✅ Initialized with {config_profile} config: "
                   f"{len(self.services)} exchanges, "
                   f"{len(self.calculators)} calculators")

    async def start(self):
        """🚀 Start all workers"""
        self.is_running = True
        logger.info("🚀 Starting optimized workers...")
        
        # Initialize Redis
        await redis_manager.connect()
        
        # Get trading pairs
        pairs_by_exchange = await self._get_trading_pairs()
        
        # Start exchange workers
        for exchange_name, pairs in pairs_by_exchange.items():
            if pairs and exchange_name in self.services:
                task = asyncio.create_task(
                    self._exchange_worker(exchange_name, pairs)
                )
                self.tasks.append(task)
                logger.info(f"✅ Started {exchange_name} worker with {len(pairs)} pairs")
        
        # Start arbitrage calculators
        for i, calculator in enumerate(self.calculators):
            task = asyncio.create_task(calculator.start_calculation())
            self.tasks.append(task)
            logger.debug(f"✅ Started arbitrage calculator {i+1}")
        
        # Start system workers
        self.tasks.extend([
            asyncio.create_task(self._system_monitor()),
            asyncio.create_task(self._cleanup_worker())
        ])
        
        logger.info(f"✅ Started {len(self.tasks)} workers")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks)
        except Exception as e:
            logger.error(f"❌ Workers error: {e}")
        finally:
            await self.stop()

    async def _exchange_worker(self, exchange_name: str, pairs: List[str]):
        """📡 Enhanced exchange worker with better logging"""
        service = self.services[exchange_name]
        failures = 0
        max_failures = self.config['max_connection_failures']
        retry_interval = self.config['connection_retry_interval']
        
        logger.info(f"{exchange_name}: Worker started with pairs: {pairs}")
        
        while self.is_running:
            try:
                # Check connection
                if not service.is_connected:
                    logger.info(f"{exchange_name}: Connection lost, attempting reconnect (failure #{failures + 1})")
                    
                    if await service.connect_with_retries():
                        # Subscribe to pairs
                        logger.info(f"{exchange_name}: Connection successful, subscribing to {len(pairs)} pairs")
                        
                        if await service.subscribe_to_pairs(pairs):
                            failures = 0  # Reset on success
                            logger.info(f"{exchange_name}: ✅ Connected and subscribed successfully")
                        else:
                            failures += 1
                            logger.warning(f"{exchange_name}: ❌ Subscription failed (failure #{failures})")
                    else:
                        failures += 1
                        logger.warning(f"{exchange_name}: ❌ Connection failed (failure #{failures})")
                
                # Health check for connected services
                elif not service.is_healthy():
                    logger.warning(f"{exchange_name}: ⚠️ Health check failed, marking as dead")
                    service.mark_dead("Health check failed")
                    failures += 1
                
                # Exit if too many failures
                if failures >= max_failures:
                    logger.error(f"{exchange_name}: 💀 Permanently failed after {failures} attempts")
                    break
                
                # Wait before next check
                await asyncio.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                failures += 1
                logger.error(f"{exchange_name}: ❌ Worker error: {e} (failure #{failures})")
                service.mark_dead(f"Worker error: {e}")
                
                if failures < max_failures:
                    logger.info(f"{exchange_name}: Waiting {retry_interval}s before retry")
                    await asyncio.sleep(retry_interval)
                else:
                    logger.error(f"{exchange_name}: 💀 Max failures reached, stopping worker")
                    break
        
        # Cleanup
        try:
            await service.disconnect()
            logger.info(f"{exchange_name}: 🔌 Worker stopped and disconnected")
        except Exception as e:
            logger.error(f"{exchange_name}: ❌ Cleanup error: {e}")

    async def _system_monitor(self):
        """📊 Enhanced system monitoring with detailed logging"""
        logger.info("📊 System monitor started")
        
        while self.is_running:
            try:
                # Get basic stats
                connected_exchanges = sum(1 for service in self.services.values() if service.is_connected)
                running_calculators = sum(1 for calc in self.calculators if hasattr(calc, 'is_running') and calc.is_running)
                
                # Log system status
                logger.info(f"📊 System Status: "
                           f"Exchanges: {connected_exchanges}/{len(self.services)}, "
                           f"Calculators: {running_calculators}/{len(self.calculators)}")
                
                # Log individual exchange status with details
                for name, service in self.services.items():
                    if service.is_connected:
                        uptime = time.time() - service.last_message_time if service.last_message_time > 0 else 0
                        subscribed_count = len(getattr(service, 'subscribed_pairs', []))
                        logger.debug(f"✅ {name}: Connected "
                                   f"(uptime: {uptime:.0f}s, "
                                   f"messages: {service.message_count}, "
                                   f"subscribed: {subscribed_count})")
                    else:
                        logger.debug(f"❌ {name}: Disconnected")
                
                # Get Redis stats
                try:
                    opportunities_count = await redis_manager.get_opportunities_count()
                    prices_count = await redis_manager.get_active_prices_count()
                    logger.debug(f"📊 Redis: {opportunities_count} opportunities, {prices_count} prices")
                except Exception as e:
                    logger.warning(f"📊 Redis stats error: {e}")
                
                await asyncio.sleep(self.config['system_monitor_interval'])
                
            except Exception as e:
                logger.error(f"❌ System monitor error: {e}")
                await asyncio.sleep(30)

    async def _cleanup_worker(self):
        """🧹 Enhanced cleanup worker"""
        logger.debug("🧹 Cleanup worker started")
        
        while self.is_running:
            try:
                # Cleanup old data
                start_time = time.time()
                await redis_manager.cleanup_old_data()
                cleanup_time = time.time() - start_time
                
                logger.debug(f"🧹 Cleanup completed in {cleanup_time:.2f}s")
                
                await asyncio.sleep(self.config['cleanup_interval'])
                
            except Exception as e:
                logger.error(f"❌ Cleanup error: {e}")
                await asyncio.sleep(60)

    @database_sync_to_async
    def _get_trading_pairs_sync(self):
        """📋 Get trading pairs from database with enhanced logging"""
        pairs_by_exchange = {}
        
        try:
            active_pairs = TradingPair.objects.filter(
                is_active=True,
                exchange__is_active=True
            ).select_related('exchange')
            
            for pair in active_pairs:
                exchange_name = pair.exchange.name
                if exchange_name not in pairs_by_exchange:
                    pairs_by_exchange[exchange_name] = []
                
                pairs_by_exchange[exchange_name].append(pair.api_symbol)
            
            total_pairs = sum(len(pairs) for pairs in pairs_by_exchange.values())
            logger.info(f"📋 Loaded {total_pairs} trading pairs from {len(pairs_by_exchange)} exchanges")
            
            # Log pairs per exchange
            for exchange, pairs in pairs_by_exchange.items():
                logger.debug(f"📋 {exchange}: {len(pairs)} pairs - {pairs}")
            
        except Exception as e:
            logger.error(f"❌ Error loading trading pairs: {e}")
        
        return pairs_by_exchange

    async def _get_trading_pairs(self) -> Dict[str, List[str]]:
        """📋 Get trading pairs async wrapper"""
        return await self._get_trading_pairs_sync()

    async def stop(self):
        """🛑 Stop all workers with enhanced logging"""
        if not self.is_running:
            return
            
        logger.info("🛑 Stopping workers...")
        self.is_running = False
        
        # Cancel all tasks
        canceled_count = 0
        for task in self.tasks:
            if not task.done():
                try:
                    task.cancel()
                    canceled_count += 1
                except Exception as e:
                    logger.error(f"❌ Task cancel error: {e}")
        
        logger.info(f"🛑 Canceled {canceled_count} tasks")
        
        # Wait for tasks to complete
        if self.tasks:
            logger.debug("🛑 Waiting for tasks to complete...")
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop calculators
        stopped_calculators = 0
        for calculator in self.calculators:
            try:
                await calculator.stop_calculation()
                stopped_calculators += 1
            except Exception as e:
                logger.error(f"❌ Calculator stop error: {e}")
        
        logger.info(f"🛑 Stopped {stopped_calculators} calculators")
        
        # Disconnect services
        disconnected_services = 0
        for name, service in self.services.items():
            try:
                await service.disconnect()
                disconnected_services += 1
                logger.debug(f"🛑 {name} disconnected")
            except Exception as e:
                logger.error(f"❌ {name} disconnect error: {e}")
        
        logger.info(f"🛑 Disconnected {disconnected_services} services")
        
        # Close Redis
        try:
            await redis_manager.close()
            logger.debug("🛑 Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Redis close error: {e}")
        
        logger.info("✅ All workers stopped successfully")

# Legacy compatibility
workers_manager = SimpleWorkersManager()