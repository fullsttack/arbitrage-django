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
            'ramzinex': RamzinexService()
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
        """📡 Simple exchange worker"""
        service = self.services[exchange_name]
        failures = 0
        max_failures = self.config['max_connection_failures']
        retry_interval = self.config['connection_retry_interval']
        
        while self.is_running:
            try:
                # Check connection
                if not service.is_connected:
                    logger.debug(f"🔌 Connecting to {exchange_name}...")
                    
                    if await service.connect_with_retries():
                        # Subscribe to pairs
                        if await service.subscribe_to_pairs(pairs):
                            failures = 0  # Reset on success
                            logger.info(f"✅ {exchange_name} connected and subscribed")
                        else:
                            failures += 1
                            logger.warning(f"❌ {exchange_name} subscription failed")
                    else:
                        failures += 1
                        logger.warning(f"❌ {exchange_name} connection failed")
                
                # Health check
                elif not service.is_healthy():
                    logger.warning(f"⚠️ {exchange_name} health check failed")
                    service.mark_dead("Health check failed")
                    failures += 1
                
                # Exit if too many failures
                if failures >= max_failures:
                    logger.error(f"💀 {exchange_name} permanently failed after {failures} attempts")
                    break
                
                # Wait before next check
                await asyncio.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                failures += 1
                logger.error(f"❌ {exchange_name} worker error: {e}")
                service.mark_dead(f"Worker error: {e}")
                
                if failures < max_failures:
                    await asyncio.sleep(retry_interval)
                else:
                    break
        
        # Cleanup
        try:
            await service.disconnect()
            logger.info(f"🔌 {exchange_name} disconnected")
        except Exception as e:
            logger.error(f"❌ {exchange_name} cleanup error: {e}")

    async def _system_monitor(self):
        """📊 Simple system monitoring"""
        while self.is_running:
            try:
                # Get basic stats
                connected_exchanges = sum(1 for service in self.services.values() if service.is_connected)
                running_calculators = sum(1 for calc in self.calculators if hasattr(calc, 'is_running') and calc.is_running)
                
                # Log system status
                logger.info(f"📊 System Status: "
                           f"Exchanges: {connected_exchanges}/{len(self.services)}, "
                           f"Calculators: {running_calculators}/{len(self.calculators)}")
                
                # Log individual exchange status
                for name, service in self.services.items():
                    if service.is_connected:
                        uptime = time.time() - service.last_message_time if service.last_message_time > 0 else 0
                        logger.debug(f"✅ {name}: Connected (uptime: {uptime:.0f}s)")
                    else:
                        logger.debug(f"❌ {name}: Disconnected")
                
                await asyncio.sleep(self.config['system_monitor_interval'])
                
            except Exception as e:
                logger.error(f"❌ System monitor error: {e}")
                await asyncio.sleep(30)

    async def _cleanup_worker(self):
        """🧹 Simple cleanup worker"""
        while self.is_running:
            try:
                # Cleanup old data
                await redis_manager.cleanup_old_data()
                logger.debug("🧹 Cleanup completed")
                
                await asyncio.sleep(self.config['cleanup_interval'])
                
            except Exception as e:
                logger.error(f"❌ Cleanup error: {e}")
                await asyncio.sleep(60)

    @database_sync_to_async
    def _get_trading_pairs_sync(self):
        """📋 Get trading pairs from database"""
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
            
        except Exception as e:
            logger.error(f"❌ Error loading trading pairs: {e}")
        
        return pairs_by_exchange

    async def _get_trading_pairs(self) -> Dict[str, List[str]]:
        """📋 Get trading pairs async wrapper"""
        return await self._get_trading_pairs_sync()

    async def stop(self):
        """🛑 Stop all workers"""
        if not self.is_running:
            return
            
        logger.info("🛑 Stopping workers...")
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop calculators
        for calculator in self.calculators:
            try:
                await calculator.stop_calculation()
            except Exception as e:
                logger.error(f"❌ Calculator stop error: {e}")
        
        # Disconnect services
        for service in self.services.values():
            try:
                await service.disconnect()
            except Exception as e:
                logger.error(f"❌ Service disconnect error: {e}")
        
        # Close Redis
        try:
            await redis_manager.close()
        except Exception as e:
            logger.error(f"❌ Redis close error: {e}")
        
        logger.info("✅ All workers stopped")

# Legacy compatibility
workers_manager = SimpleWorkersManager()