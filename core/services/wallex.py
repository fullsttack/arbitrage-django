import asyncio
import aiohttp
import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from .base import BaseExchangeService

logger = logging.getLogger(__name__)

class WallexService(BaseExchangeService):
    def __init__(self):
        super().__init__('wallex')
        self.base_url = 'https://api.wallex.ir'
        self.session = None
        self.polling_tasks = {}

    async def connect(self):
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=5)
            self.session = aiohttp.ClientSession(timeout=timeout)
        self.is_connected = True
        logger.info("Wallex service connected")

    async def subscribe_to_pairs(self, pairs: List[str]):
        await self.connect()
        
        # Start concurrent polling for all pairs
        tasks = []
        for pair in pairs:
            if pair not in self.polling_tasks:
                task = asyncio.create_task(self._poll_pair(pair))
                self.polling_tasks[pair] = task
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_pair(self, symbol: str):
        """Ultra-fast polling with minimal overhead"""
        url = f"{self.base_url}/v1/depth"
        params = {'symbol': symbol}
        
        while self.is_connected:
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        parsed_data = self.parse_price_data(data)
                        
                        if parsed_data:
                            await self.save_price_data(
                                symbol=symbol,
                                bid_price=parsed_data['bid_price'],
                                ask_price=parsed_data['ask_price'],
                                volume=parsed_data['volume']
                            )
                            
            except Exception as e:
                logger.debug(f"Wallex polling error for {symbol}: {e}")
                
            await asyncio.sleep(0.05)  # Poll every 50ms

    def parse_price_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if not data.get('success'):
                return None
                
            result = data.get('result', {})
            asks = result.get('ask', [])
            bids = result.get('bid', [])
            
            if not asks or not bids:
                return None
                
            ask_price = Decimal(str(asks[0]['price']))
            bid_price = Decimal(str(bids[0]['price']))
            volume = Decimal(str(asks[0].get('quantity', 0)))
            
            return {
                'bid_price': bid_price,
                'ask_price': ask_price,
                'volume': volume
            }
            
        except (KeyError, IndexError, ValueError):
            return None

    async def disconnect(self):
        await super().disconnect()
        
        for task in self.polling_tasks.values():
            task.cancel()
        self.polling_tasks.clear()
        
        if self.session:
            await self.session.close()
            self.session = None