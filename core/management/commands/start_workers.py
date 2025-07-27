import asyncio
import signal
import logging
import sys
from django.core.management.base import BaseCommand
from core.workers import SimpleWorkersManager

class Command(BaseCommand):
    """🚀 Simple and Fast Workers Starter"""
    help = 'Start optimized arbitrage workers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--log-level',
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            help='Set log level'
        )
        parser.add_argument(
            '--config',
            default='default',
            help='Configuration profile to use'
        )

    def handle(self, *args, **options):
        # Setup logging
        log_level = getattr(logging, options['log_level'])
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        self.stdout.write(
            self.style.SUCCESS(f"🚀 Starting optimized arbitrage workers...")
        )

        # Create workers manager
        manager = SimpleWorkersManager(config_profile=options['config'])

        # Setup signal handlers
        def signal_handler(signum, frame):
            self.stdout.write("🛑 Gracefully shutting down workers...")
            asyncio.create_task(manager.stop())
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start workers
        try:
            asyncio.run(manager.start())
        except KeyboardInterrupt:
            self.stdout.write("🛑 Received interrupt signal")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
            sys.exit(1)
        finally:
            self.stdout.write("✅ Workers stopped")