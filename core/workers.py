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

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')

class HighPerformanceWorkersManager:
    def __init__(self, worker_count=None):
        # Use uvloop for better performance
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        
        self.worker_count = worker_count or getattr(settings, 'WORKER_COUNT', multiprocessing.cpu_count() * 2)
        self.services = {
            'wallex': WallexService(),
            'lbank': LBankService(),
            'ramzinex': RamzinexService()
        }
        self.arbitrage_calculators = []
        self.is_running = False
        self.worker_tasks = []
        self.thread_executor = ThreadPoolExecutor(max_workers=self.worker_count)
        
        performance_logger.info(f"Initialized with {self.worker_count} workers")

    async def start_all_workers(self):
        """Start all workers with maximum performance"""
        self.is_running = True
        performance_logger.info(f"Starting {self.worker_count} high-performance workers...")
        
        # Get trading pairs
        pairs_by_exchange = await self._get_trading_pairs()
        
        # Create multiple arbitrage calculators for parallel processing
        for i in range(min(4, self.worker_count)):  # Max 4 arbitrage workers
            calc = FastArbitrageCalculator()
            self.arbitrage_calculators.append(calc)
        
        # Start all workers concurrently
        worker_tasks = [
            # Exchange workers (concurrent connections)
            self._start_exchange_workers(pairs_by_exchange),
            
            # Multiple arbitrage calculators for parallel processing
            *[calc.start_calculation() for calc in self.arbitrage_calculators],
            
            # Utility workers
            self._start_cleanup_worker(),
            self._start_performance_monitor(),
            self._start_connection_monitor(),
        ]
        
        self.worker_tasks = [asyncio.create_task(task) for task in worker_tasks]
        
        # Wait for all workers to start and run
        try:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Worker error: {e}")

    async def _get_trading_pairs(self) -> Dict[str, List[str]]:
        """Get active trading pairs with caching"""
        pairs_by_exchange = {}
        
        # Use database connection pooling for better performance
        active_pairs = TradingPair.objects.filter(
            is_active=True,
            exchange__is_active=True
        ).select_related('exchange', 'base_currency', 'quote_currency').prefetch_related()
        
        for pair in active_pairs:
            exchange_name = pair.exchange.name
            if exchange_name not in pairs_by_exchange:
                pairs_by_exchange[exchange_name] = []
            
            symbol = pair.symbol_format if exchange_name != 'ramzinex' else pair.pair_id
            pairs_by_exchange[exchange_name].append(symbol)
        
        performance_logger.info(f"Loaded {sum(len(pairs) for pairs in pairs_by_exchange.values())} trading pairs")
        return pairs_by_exchange

    async def _start_exchange_workers(self, pairs_by_exchange: Dict[str, List[str]]):
        """Start all exchange services with concurrent connections"""
        connection_tasks = []
        
        for exchange_name, service in self.services.items():
            if exchange_name in pairs_by_exchange:
                pairs = pairs_by_exchange[exchange_name]
                
                # Create multiple instances for high throughput
                num_instances = min(3, len(pairs) // 5 + 1)  # Scale based on pairs count
                
                for i in range(num_instances):
                    pairs_subset = pairs[i::num_instances]  # Distribute pairs
                    if pairs_subset:
                        task = self._start_single_exchange_instance(
                            service.__class__(), pairs_subset, f"{exchange_name}_{i}"
                        )
                        connection_tasks.append(task)
        
        if connection_tasks:
            await asyncio.gather(*connection_tasks, return_exceptions=True)

    async def _start_single_exchange_instance(self, service, pairs: List[str], instance_name: str):
        """Start a single exchange service instance"""
        try:
            performance_logger.info(f"Starting {instance_name} with {len(pairs)} pairs")
            
            await service.connect()
            await service.subscribe_to_pairs(pairs)
            
            # Keep connection alive with health checks
            while self.is_running:
                if not service.is_connected:
                    performance_logger.warning(f"{instance_name} disconnected, reconnecting...")
                    await service.connect()
                    await service.subscribe_to_pairs(pairs)
                
                await asyncio.sleep(5)  # Health check every 5 seconds
                
        except Exception as e:
            logger.error(f"Error in {instance_name}: {e}")

    async def _start_performance_monitor(self):
        """Monitor and log performance metrics"""
        import psutil
        import gc
        
        while self.is_running:
            try:
                # System metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # Python garbage collection
                gc_stats = gc.get_stats()
                
                performance_logger.info(
                    f"METRICS - CPU: {cpu_percent}%, Memory: {memory.percent}%, "
                    f"GC: {sum(stat['collections'] for stat in gc_stats)}"
                )
                
                # Force garbage collection if memory usage is high
                if memory.percent > 80:
                    gc.collect()
                    performance_logger.warning("High memory usage, forced garbage collection")
                
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                
            await asyncio.sleep(10)  # Monitor every 10 seconds

    async def _start_connection_monitor(self):
        """Monitor connection health and auto-reconnect"""
        import redis.asyncio as redis
        
        redis_client = redis.Redis(
            host=settings.REDIS_CONFIG['HOST'],
            port=settings.REDIS_CONFIG['PORT'],
            db=settings.REDIS_CONFIG['DB'],
            **settings.REDIS_CONFIG['CONNECTION_POOL_KWARGS']
        )
        
        while self.is_running:
            try:
                # Test Redis connection
                await redis_client.ping()
                
                # Test exchange connections
                for exchange_name, service in self.services.items():
                    if not service.is_connected:
                        performance_logger.warning(f"{exchange_name} disconnected")
                
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
                
            await asyncio.sleep(5)
        
        await redis_client.close()

    async def _start_cleanup_worker(self):
        """Enhanced cleanup with batch operations"""
        import redis.asyncio as redis
        
        redis_client = redis.Redis(
            host=settings.REDIS_CONFIG['HOST'],
            port=settings.REDIS_CONFIG['PORT'],
            db=settings.REDIS_CONFIG['DB'],
            **settings.REDIS_CONFIG['CONNECTION_POOL_KWARGS']
        )
        
        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                
                # Batch cleanup for better performance
                async with redis_client.pipeline() as pipe:
                    # Clean old opportunities (batch operation)
                    opportunity_keys = await redis_client.keys("opportunity:*")
                    old_keys = []
                    
                    for key in opportunity_keys:
                        try:
                            timestamp_ms = int(key.split(':')[1])
                            timestamp = timestamp_ms / 1000
                            if current_time - timestamp > 60:  # 1 minute old
                                old_keys.append(key)
                        except (IndexError, ValueError):
                            continue
                    
                    if old_keys:
                        pipe.delete(*old_keys)
                    
                    # Clean old price data
                    price_keys = await redis_client.keys("prices:*")
                    old_price_keys = []
                    
                    for key in price_keys:
                        data = await redis_client.get(key)
                        if data:
                            try:
                                import json
                                price_data = json.loads(data)
                                if current_time - price_data['timestamp'] > 30:  # 30 seconds old
                                    old_price_keys.append(key)
                            except:
                                continue
                    
                    if old_price_keys:
                        pipe.delete(*old_price_keys)
                    
                    # Execute batch operations
                    await pipe.execute()
                    
                    if old_keys or old_price_keys:
                        performance_logger.info(
                            f"Cleaned {len(old_keys)} opportunities, {len(old_price_keys)} prices"
                        )
                    
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                
            await asyncio.sleep(15)  # Cleanup every 15 seconds
        
        await redis_client.close()

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
            task.cancel()
        
        # Shutdown thread executor
        self.thread_executor.shutdown(wait=True)
        
        performance_logger.info("All workers stopped")

# Global instance
workers_manager = HighPerformanceWorkersManager()