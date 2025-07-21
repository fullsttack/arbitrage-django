import asyncio
import logging
import multiprocessing
import uvloop
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from django.conf import settings
from .services.wallex import WallexService
from .services.lbank import LBankService
from .services.ramzinex import RamzinexService
from .arbitrage.calculator import FastArbitrageCalculator
from .models import TradingPair
from .redis_manager import redis_manager

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')

class HighPerformanceWorkersManager:
    def __init__(self, worker_count=None):
        # Use uvloop for better performance
        try:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except:
            logger.warning("uvloop not available, using default event loop")
        
        self.worker_count = worker_count or getattr(settings, 'WORKER_COUNT', multiprocessing.cpu_count() * 2)
        
        # Exchange services
        self.services = {
            'wallex': WallexService(),
            'lbank': LBankService(),
            'ramzinex': RamzinexService()
        }
        
        # Arbitrage calculators
        self.arbitrage_calculators = []
        self.is_running = False
        self.worker_tasks = []
        
        performance_logger.info(f"Initialized with {self.worker_count} workers")

    async def start_all_workers(self):
        """Start all workers with maximum performance"""
        self.is_running = True
        performance_logger.info(f"Starting {self.worker_count} high-performance workers...")
        
        # Initialize Redis
        await redis_manager.connect()
        
        # Get trading pairs by exchange
        pairs_by_exchange = await self._get_trading_pairs()
        
        # Create arbitrage calculators (2-4 instances for parallel processing)
        calculator_count = min(4, max(2, self.worker_count // 2))
        for i in range(calculator_count):
            calc = FastArbitrageCalculator()
            self.arbitrage_calculators.append(calc)
        
        # Start all workers concurrently
        worker_tasks = [
            # Worker 1-3: Exchange price updaters
            self._start_wallex_worker(pairs_by_exchange.get('wallex', [])),
            self._start_lbank_worker(pairs_by_exchange.get('lbank', [])),
            self._start_ramzinex_worker(pairs_by_exchange.get('ramzinex', [])),
            
            # Worker 4-7: Arbitrage calculators
            *[calc.start_calculation() for calc in self.arbitrage_calculators],
            
            # Worker 8: Cleanup and monitoring
            self._start_cleanup_worker(),
            self._start_monitoring_worker(),
        ]
        
        self.worker_tasks = [asyncio.create_task(task) for task in worker_tasks]
        
        performance_logger.info(f"Started {len(self.worker_tasks)} worker tasks")
        
        # Wait for all workers to run
        try:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Worker error: {e}")

    async def _get_trading_pairs(self) -> Dict[str, List[str]]:
        """Get active trading pairs from database"""
        pairs_by_exchange = {}
        
        try:
            # Get active trading pairs
            active_pairs = TradingPair.objects.filter(
                is_active=True,
                exchange__is_active=True
            ).select_related('exchange', 'base_currency', 'quote_currency')
            
            for pair in active_pairs:
                exchange_name = pair.exchange.name
                if exchange_name not in pairs_by_exchange:
                    pairs_by_exchange[exchange_name] = []
                
                # Use appropriate symbol/ID for each exchange
                symbol = pair.api_symbol
                pairs_by_exchange[exchange_name].append(symbol)
            
            total_pairs = sum(len(pairs) for pairs in pairs_by_exchange.values())
            performance_logger.info(f"Loaded {total_pairs} trading pairs across {len(pairs_by_exchange)} exchanges")
            
        except Exception as e:
            logger.error(f"Error loading trading pairs: {e}")
        
        return pairs_by_exchange

    async def _start_wallex_worker(self, pairs: List[str]):
        """Worker 1: Wallex price updater"""
        if not pairs:
            logger.info("No Wallex pairs configured")
            return
        
        try:
            service = self.services['wallex']
            await service.connect()
            await service.subscribe_to_pairs(pairs)
            
            performance_logger.info(f"Wallex worker started with {len(pairs)} pairs")
            
            # Keep worker alive
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Wallex worker error: {e}")
        finally:
            await service.disconnect()

    async def _start_lbank_worker(self, pairs: List[str]):
        """Worker 2: LBank price updater"""
        if not pairs:
            logger.info("No LBank pairs configured")
            return
        
        try:
            service = self.services['lbank']
            await service.connect()
            await service.subscribe_to_pairs(pairs)
            
            performance_logger.info(f"LBank worker started with {len(pairs)} pairs")
            
            # Keep worker alive
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"LBank worker error: {e}")
        finally:
            await service.disconnect()

    async def _start_ramzinex_worker(self, pairs: List[str]):
        """Worker 3: Ramzinex price updater"""
        if not pairs:
            logger.info("No Ramzinex pairs configured")
            return
        
        try:
            service = self.services['ramzinex']
            await service.connect()
            await service.subscribe_to_pairs(pairs)
            
            performance_logger.info(f"Ramzinex worker started with {len(pairs)} pairs")
            
            # Keep worker alive
            while self.is_running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ramzinex worker error: {e}")
        finally:
            await service.disconnect()

    async def _start_cleanup_worker(self):
        """Worker: Cleanup old data"""
        performance_logger.info("Cleanup worker started")
        
        while self.is_running:
            try:
                await redis_manager.cleanup_old_data()
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(10)

    async def _start_monitoring_worker(self):
        """Worker: System monitoring"""
        performance_logger.info("Monitoring worker started")
        
        while self.is_running:
            try:
                # Log system statistics
                stats = await redis_manager.get_redis_stats()
                opportunities_count = await redis_manager.get_opportunities_count()
                prices_count = await redis_manager.get_active_prices_count()
                
                performance_logger.info(
                    f"System stats - Opportunities: {opportunities_count}, "
                    f"Prices: {prices_count}, "
                    f"Redis memory: {stats.get('memory_used', 'N/A')}"
                )
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")
                await asyncio.sleep(30)

    async def stop_all_workers(self):
        """Stop all workers gracefully"""
        performance_logger.info("Stopping all workers...")
        self.is_running = False
        
        # Stop arbitrage calculators
        for calc in self.arbitrage_calculators:
            await calc.stop_calculation()
        
        # Stop exchange services
        for service in self.services.values():
            await service.disconnect()
        
        # Cancel all tasks
        for task in self.worker_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Close Redis connection
        await redis_manager.close()
        
        performance_logger.info("All workers stopped")

# Global instance
workers_manager = HighPerformanceWorkersManager()