import asyncio
import signal
import logging
import multiprocessing
from django.core.management.base import BaseCommand
from core.workers import workers_manager

class Command(BaseCommand):
    help = 'Start high-performance arbitrage workers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=multiprocessing.cpu_count() * 2,
            help='Number of worker processes'
        )
        parser.add_argument(
            '--log-level',
            default='INFO',
            help='Set log level (DEBUG, INFO, WARNING, ERROR)'
        )

    def handle(self, *args, **options):
        # Setup logging
        log_level = getattr(logging, options['log_level'])
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Update worker count
        workers_manager.worker_count = options['workers']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting {options['workers']} high-performance workers..."
            )
        )

        # Setup signal handlers
        def signal_handler(signum, frame):
            self.stdout.write("Gracefully shutting down workers...")
            asyncio.create_task(workers_manager.stop_all_workers())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start workers
        try:
            asyncio.run(self._run_workers())
        except KeyboardInterrupt:
            self.stdout.write("Received interrupt signal")
        finally:
            self.stdout.write("Workers stopped")

    async def _run_workers(self):
        await workers_manager.start_all_workers()