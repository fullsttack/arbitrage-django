import asyncio
import logging
import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor

# Try to import uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False
    logging.warning("uvloop not available, using default event loop")
    
from typing import Dict, List
from django.conf import settings
from channels.db import database_sync_to_async
from .services.wallex import WallexService
from .services.lbank import LBankService
from .services.ramzinex import RamzinexService
from .arbitrage.calculator import FastArbitrageCalculator
from .models import TradingPair
from .redis_manager import redis_manager

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')

class WorkerTask:
    """Individual worker task wrapper with health monitoring"""
    
    def __init__(self, name: str, coro, restart_on_failure: bool = True):
        self.name = name
        self.coro = coro
        self.restart_on_failure = restart_on_failure
        self.task = None
        self.start_time = None
        self.failure_count = 0
        self.max_failures = 10  # Increased tolerance
        self.last_restart_time = 0
        self.min_restart_interval = 0   # NO DELAY - instant restart
        self.restart_delay = 0          # INSTANT restart - no waiting
        
    async def start(self):
        """Start the worker task"""
        self.start_time = time.time()
        self.task = asyncio.create_task(self.coro)
        self.task.add_done_callback(self._task_done_callback)
        logger.info(f"Worker task '{self.name}' started")
        
    def _task_done_callback(self, task):
        """Handle task completion/failure"""
        try:
            if task.cancelled():
                logger.info(f"Worker task '{self.name}' was cancelled")
                return
                
            exception = task.exception()
            if exception:
                self.failure_count += 1
                logger.error(f"Worker task '{self.name}' failed (attempt {self.failure_count}/{self.max_failures}): {exception}")
                
                # Schedule restart if enabled and not too many failures
                if self.restart_on_failure and self.failure_count < self.max_failures:
                    current_time = time.time()
                    if current_time - self.last_restart_time >= self.min_restart_interval:
                        logger.info(f"INSTANT restart for worker task '{self.name}' - NO DELAY!")
                        asyncio.create_task(self._instant_restart())
                    # No minimum interval check - always restart instantly
                else:
                    logger.error(f"Worker task '{self.name}' permanently failed after {self.failure_count} attempts")
            else:
                logger.info(f"Worker task '{self.name}' completed successfully")
                
        except Exception as e:
            logger.error(f"Error in task done callback for '{self.name}': {e}")
    
    async def _instant_restart(self):
        """INSTANT restart with absolutely NO delay"""
        # NO SLEEP - instant restart!
        self.last_restart_time = time.time()
        logger.info(f"🚀 INSTANT restart worker task '{self.name}' (attempt {self.failure_count + 1}) - NO DELAY!")
        await self.start()
    
    def is_running(self):
        """Check if task is currently running"""
        return self.task and not self.task.done()
    
    def get_uptime(self):
        """Get task uptime in seconds"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    async def stop(self):
        """Stop the worker task"""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"Worker task '{self.name}' stopped")

class HighPerformanceWorkersManager:
    def __init__(self, worker_count=None):
        # Use uvloop for better performance if available
        if UVLOOP_AVAILABLE:
            try:
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
                logger.info("Using uvloop for better performance")
            except Exception as e:
                logger.warning(f"Failed to set uvloop: {e}")
        else:
            logger.info("Using default asyncio event loop")
        
        self.worker_count = worker_count or getattr(settings, 'WORKER_COUNT', multiprocessing.cpu_count() * 2)
        
        # Exchange services
        self.services = {
            'wallex': WallexService(),
            'lbank': LBankService(),
            'ramzinex': RamzinexService()
        }
        
        # Arbitrage calculators - OPTIMIZED COUNT
        self.arbitrage_calculators = []
        self.is_running = False
        self.worker_tasks = {}  # Dict of WorkerTask objects
        
        # Calculate optimal number of arbitrage calculators
        cpu_cores = multiprocessing.cpu_count()
        self.optimal_calculator_count = min(8, max(6, cpu_cores))  # 6-8 calculators
        
        performance_logger.info(f"Initialized with {self.worker_count} workers and {self.optimal_calculator_count} arbitrage calculators")

    async def start_all_workers(self):
        """Start all workers with enhanced monitoring and auto-restart"""
        self.is_running = True
        performance_logger.info(f"Starting {self.worker_count} high-performance workers with {self.optimal_calculator_count} arbitrage calculators...")
        
        # Initialize Redis
        await redis_manager.connect()
        
        # Get trading pairs by exchange
        pairs_by_exchange = await self._get_trading_pairs()
        
        # Create optimized arbitrage calculators
        for i in range(self.optimal_calculator_count):
            calc = FastArbitrageCalculator()
            self.arbitrage_calculators.append(calc)
            performance_logger.info(f"Created arbitrage calculator {i+1}/{self.optimal_calculator_count}")
        
        # Create and start worker tasks
        await self._create_worker_tasks(pairs_by_exchange)
        
        # Start monitoring task
        monitoring_task = WorkerTask(
            "system_monitor",
            self._system_monitor(),
            restart_on_failure=True
        )
        await monitoring_task.start()
        self.worker_tasks["system_monitor"] = monitoring_task
        
        performance_logger.info(f"Started {len(self.worker_tasks)} worker tasks with auto-restart capability")
        
        # Main monitoring loop
        try:
            await self._main_monitoring_loop()
        except Exception as e:
            logger.error(f"Main monitoring loop error: {e}")

    async def _create_worker_tasks(self, pairs_by_exchange: Dict[str, List[str]]):
        """Create all worker tasks with optimized arbitrage calculators"""
        
        # Exchange workers
        exchange_workers = [
            ("wallex_worker", self._enhanced_exchange_worker('wallex', pairs_by_exchange.get('wallex', []))),
            ("lbank_worker", self._enhanced_exchange_worker('lbank', pairs_by_exchange.get('lbank', []))),
            ("ramzinex_worker", self._enhanced_exchange_worker('ramzinex', pairs_by_exchange.get('ramzinex', []))),
        ]
        
        # Optimized arbitrage calculator workers
        arbitrage_workers = [
            (f"arbitrage_calc_{i}", calc.start_calculation()) 
            for i, calc in enumerate(self.arbitrage_calculators)
        ]
        
        # System workers
        system_workers = [
            ("cleanup_worker", self._start_cleanup_worker()),
            ("performance_monitor", self._start_performance_monitor()),  # New performance monitor
        ]
        
        # Start all workers
        all_workers = exchange_workers + arbitrage_workers + system_workers
        
        for name, coro in all_workers:
            worker_task = WorkerTask(name, coro, restart_on_failure=True)
            await worker_task.start()
            self.worker_tasks[name] = worker_task
            
        performance_logger.info(f"Created {len(exchange_workers)} exchange workers, {len(arbitrage_workers)} arbitrage workers, {len(system_workers)} system workers")

    async def _enhanced_exchange_worker(self, exchange_name: str, pairs: List[str]):
        """Enhanced exchange worker with robust reconnection"""
        if not pairs:
            logger.info(f"No {exchange_name} pairs configured")
            return
        
        service = self.services[exchange_name]
        consecutive_failures = 0
        max_consecutive_failures = 20  # Even more tolerance
        base_retry_delay = 0   # NO DELAY - instant retry
        max_retry_delay = 0    # NO MAXIMUM DELAY - always instant
        
        logger.info(f"Starting {exchange_name} worker with {len(pairs)} pairs")
        
        while self.is_running:
            try:
                # Connection state check
                if not service.is_connected:
                    logger.info(f"{exchange_name}: Attempting connection...")
                    
                    # NO DELAY - INSTANT retry for all attempts
                    if consecutive_failures > 0:
                        logger.info(f"{exchange_name}: 🚀 INSTANT retry (attempt {consecutive_failures + 1}) - NO DELAY!")
                    # No sleep - instant retry!
                    
                    # Attempt connection
                    connection_success = await service.connect()
                    
                    if connection_success:
                        # Subscribe to pairs
                        subscription_success = await service.subscribe_to_pairs(pairs)
                        
                        if subscription_success:
                            consecutive_failures = 0
                            logger.info(f"{exchange_name}: Successfully connected and subscribed")
                        else:
                            logger.error(f"{exchange_name}: Subscription failed")
                            service.mark_connection_dead("Subscription failed")
                    else:
                        consecutive_failures += 1
                        logger.error(f"{exchange_name}: Connection failed (attempt {consecutive_failures})")
                        
                        if consecutive_failures >= max_consecutive_failures:
                            logger.error(f"{exchange_name}: Maximum consecutive failures reached, resetting counter...")
                            # NO BACKOFF DELAY - instant reset and retry
                            consecutive_failures = 0  # Reset counter immediately
                
                # Health monitoring while connected
                else:
                    # Check connection health
                    if not service.is_connection_healthy():
                        logger.warning(f"{exchange_name}: Connection health check failed")
                        service.mark_connection_dead("Health check failed")
                        consecutive_failures += 1
                    else:
                        # Connection is healthy, reset failure counter
                        consecutive_failures = 0
                    
                    # ULTRA-FAST health check - check every second
                    await asyncio.sleep(1)
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"{exchange_name} worker error (failure {consecutive_failures}): {e}")
                
                # Ensure service is marked as disconnected
                service.mark_connection_dead(f"Worker exception: {e}")
                
                # Brief pause before retry
                await asyncio.sleep(5)
        
        # Cleanup on exit
        try:
            await service.disconnect()
            logger.info(f"{exchange_name} worker stopped and disconnected")
        except Exception as e:
            logger.error(f"{exchange_name} cleanup error: {e}")

    @database_sync_to_async
    def _get_trading_pairs_sync(self):
        """Get active trading pairs from database (sync version)"""
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
        
    async def _get_trading_pairs(self) -> Dict[str, List[str]]:
        """Get active trading pairs from database"""
        return await self._get_trading_pairs_sync()

    async def _start_cleanup_worker(self):
        """Worker: Cleanup old data"""
        performance_logger.info("Cleanup worker started")
        
        while self.is_running:
            try:
                await redis_manager.cleanup_old_data()
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def _start_performance_monitor(self):
        """Worker: Monitor system performance metrics"""
        performance_logger.info("Performance monitor started")
        
        while self.is_running:
            try:
                # Monitor arbitrage calculator performance
                active_calculators = len([calc for calc in self.arbitrage_calculators if calc.is_running])
                total_calculations = sum(calc.calculation_count for calc in self.arbitrage_calculators if hasattr(calc, 'calculation_count'))
                
                # Monitor Redis performance
                stats = await redis_manager.get_redis_stats()
                
                # Log performance metrics every 2 minutes
                performance_logger.info(
                    f"Performance Metrics - "
                    f"Active Calculators: {active_calculators}/{len(self.arbitrage_calculators)}, "
                    f"Total Calculations: {total_calculations}, "
                    f"Redis Ops/sec: {stats.get('operations_per_sec', 0)}, "
                    f"Redis Hit Rate: {self._calculate_hit_rate(stats)}"
                )
                
                await asyncio.sleep(120)  # Monitor every 2 minutes
                
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(60)

    def _calculate_hit_rate(self, stats: Dict) -> str:
        """Calculate Redis cache hit rate"""
        try:
            hits = stats.get('keyspace_hits', 0)
            misses = stats.get('keyspace_misses', 0)
            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                return f"{hit_rate:.1f}%"
            return "N/A"
        except:
            return "N/A"

    async def _system_monitor(self):
        """Enhanced system monitoring with detailed metrics"""
        performance_logger.info("System monitor started")
        
        while self.is_running:
            try:
                # Log system statistics
                stats = await redis_manager.get_redis_stats()
                opportunities_count = await redis_manager.get_opportunities_count()
                prices_count = await redis_manager.get_active_prices_count()
                
                # Count healthy connections
                healthy_connections = 0
                total_connections = 0
                
                for name, service in self.services.items():
                    total_connections += 1
                    if service.is_connected and service.is_connection_healthy():
                        healthy_connections += 1
                
                # Count running worker tasks
                running_tasks = sum(1 for task in self.worker_tasks.values() if task.is_running())
                total_tasks = len(self.worker_tasks)
                
                # Count active arbitrage calculators
                active_calculators = len([calc for calc in self.arbitrage_calculators if calc.is_running])
                
                performance_logger.info(
                    f"System Status - "
                    f"Connections: {healthy_connections}/{total_connections}, "
                    f"Tasks: {running_tasks}/{total_tasks}, "
                    f"Calculators: {active_calculators}/{len(self.arbitrage_calculators)}, "
                    f"Opportunities: {opportunities_count}, "
                    f"Prices: {prices_count}, "
                    f"Redis Memory: {stats.get('memory_used', 'N/A')}"
                )
                
                # Log individual service status
                for name, service in self.services.items():
                    if service.is_connected:
                        uptime = time.time() - service.connection_start_time if service.connection_start_time else 0
                        data_age = time.time() - service.last_data_time if service.last_data_time else float('inf')
                        logger.debug(f"{name}: Connected for {uptime:.0f}s, last data {data_age:.0f}s ago")
                    else:
                        logger.debug(f"{name}: Disconnected")
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"System monitor error: {e}")
                await asyncio.sleep(30)

    async def _main_monitoring_loop(self):
        """Main monitoring loop to keep the manager running"""
        while self.is_running:
            try:
                # Check worker task health
                dead_tasks = []
                for name, worker_task in self.worker_tasks.items():
                    if not worker_task.is_running() and worker_task.failure_count >= worker_task.max_failures:
                        dead_tasks.append(name)
                
                # Remove permanently failed tasks
                for name in dead_tasks:
                    logger.error(f"Removing permanently failed worker task: {name}")
                    del self.worker_tasks[name]
                
                # Check arbitrage calculator health
                dead_calculators = []
                for i, calc in enumerate(self.arbitrage_calculators):
                    if hasattr(calc, 'is_running') and not calc.is_running:
                        dead_calculators.append(i)
                
                # Restart dead calculators
                for i in dead_calculators:
                    logger.warning(f"Restarting dead arbitrage calculator {i}")
                    calc = FastArbitrageCalculator()
                    self.arbitrage_calculators[i] = calc
                    
                    # Create new worker task for the calculator
                    worker_task = WorkerTask(f"arbitrage_calc_{i}", calc.start_calculation(), restart_on_failure=True)
                    await worker_task.start()
                    self.worker_tasks[f"arbitrage_calc_{i}"] = worker_task
                
                # Sleep and continue monitoring
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Main monitoring loop error: {e}")
                await asyncio.sleep(10)

    async def stop_all_workers(self):
        """Stop all workers gracefully"""
        performance_logger.info("Stopping all workers...")
        self.is_running = False
        
        # Stop all worker tasks
        stop_tasks = []
        for worker_task in self.worker_tasks.values():
            stop_tasks.append(worker_task.stop())
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # Stop arbitrage calculators
        for calc in self.arbitrage_calculators:
            await calc.stop_calculation()
        
        # Stop exchange services
        for service in self.services.values():
            await service.disconnect()
        
        # Close Redis connection
        await redis_manager.close()
        
        performance_logger.info("All workers stopped")

# Global instance
workers_manager = HighPerformanceWorkersManager()