import numpy as np
import asyncio
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass
import redis.asyncio as redis
from django.conf import settings

logger = logging.getLogger(__name__)

@dataclass
class PricePoint:
    exchange: str
    symbol: str
    bid_price: float
    ask_price: float
    volume: float
    timestamp: float
    pair_id: int
    min_volume: float
    max_volume: float
    threshold: float

@dataclass
class ArbitrageOpportunity:
    buy_exchange: str
    sell_exchange: str
    base_currency: str
    quote_currency: str
    buy_price: float
    sell_price: float
    profit_percentage: float
    volume: float
    timestamp: float

class FastArbitrageCalculator:
    def __init__(self):
        self.redis_client = None
        self.is_running = False
        self.price_matrix = {}
        
    async def init_redis(self):
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True
            )

    async def start_calculation(self):
        """Start fast arbitrage calculation using NumPy"""
        await self.init_redis()
        self.is_running = True
        
        logger.info("Starting fast arbitrage calculation...")
        
        while self.is_running:
            try:
                # Get all price data
                price_data = await self._get_all_price_data()
                
                if len(price_data) >= 2:
                    # Calculate opportunities using NumPy
                    opportunities = await self._calculate_opportunities_fast(price_data)
                    
                    # Save opportunities
                    await self._save_opportunities(opportunities)
                    
            except Exception as e:
                logger.error(f"Error in arbitrage calculation: {e}")
                
            await asyncio.sleep(0.02)  # Calculate every 20ms for maximum speed

    async def _get_all_price_data(self) -> Dict[str, List[PricePoint]]:
        """Get all price data grouped by currency pairs"""
        from ..models import TradingPair
        
        price_groups = {}
        
        # Get active pairs
        active_pairs = TradingPair.objects.filter(
            is_active=True,
            exchange__is_active=True
        ).select_related('exchange', 'base_currency', 'quote_currency')
        
        for pair in active_pairs:
            symbol = pair.symbol_format if pair.exchange.name != 'ramzinex' else pair.pair_id
            key = f"prices:{pair.exchange.name}:{symbol}"
            
            data = await self.redis_client.get(key)
            if data:
                price_info = json.loads(data)
                
                currency_key = f"{pair.base_currency.symbol}_{pair.quote_currency.symbol}"
                if currency_key not in price_groups:
                    price_groups[currency_key] = []
                
                price_point = PricePoint(
                    exchange=pair.exchange.name,
                    symbol=symbol,
                    bid_price=float(price_info['bid_price']),
                    ask_price=float(price_info['ask_price']),
                    volume=float(price_info['volume']),
                    timestamp=float(price_info['timestamp']),
                    pair_id=pair.id,
                    min_volume=float(pair.min_volume),
                    max_volume=float(pair.max_volume),
                    threshold=float(pair.arbitrage_threshold)
                )
                
                price_groups[currency_key].append(price_point)
        
        return price_groups

    async def _calculate_opportunities_fast(self, price_groups: Dict[str, List[PricePoint]]) -> List[ArbitrageOpportunity]:
        """Fast calculation using NumPy vectorization"""
        opportunities = []
        
        for currency_key, price_points in price_groups.items():
            if len(price_points) < 2:
                continue
                
            base_currency, quote_currency = currency_key.split('_')
            
            # Convert to NumPy arrays for vectorized operations
            n = len(price_points)
            
            # Create matrices
            bid_prices = np.array([p.bid_price for p in price_points])
            ask_prices = np.array([p.ask_price for p in price_points])
            volumes = np.array([p.volume for p in price_points])
            min_volumes = np.array([p.min_volume for p in price_points])
            max_volumes = np.array([p.max_volume for p in price_points])
            thresholds = np.array([p.threshold for p in price_points])
            
            # Vectorized calculation for all pairs
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    
                    buy_price = ask_prices[i]  # خرید از صرافی i
                    sell_price = bid_prices[j]  # فروش در صرافی j
                    
                    if sell_price <= buy_price:
                        continue
                    
                    # Calculate profit percentage
                    profit_pct = ((sell_price - buy_price) / buy_price) * 100
                    
                    # Check threshold
                    min_threshold = min(thresholds[i], thresholds[j])
                    if profit_pct < min_threshold:
                        continue
                    
                    # Calculate volume constraints
                    available_volume = min(volumes[i], volumes[j])
                    min_vol = max(min_volumes[i], min_volumes[j])
                    max_vol = min(max_volumes[i], max_volumes[j]) if max_volumes[i] > 0 and max_volumes[j] > 0 else available_volume
                    
                    if available_volume < min_vol or (max_vol > 0 and available_volume > max_vol):
                        continue
                    
                    opportunity = ArbitrageOpportunity(
                        buy_exchange=price_points[i].exchange,
                        sell_exchange=price_points[j].exchange,
                        base_currency=base_currency,
                        quote_currency=quote_currency,
                        buy_price=buy_price,
                        sell_price=sell_price,
                        profit_percentage=profit_pct,
                        volume=available_volume,
                        timestamp=asyncio.get_event_loop().time()
                    )
                    
                    opportunities.append(opportunity)
        
        return opportunities

    async def _save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Save opportunities to Redis and broadcast"""
        if not opportunities:
            return
            
        # Save each opportunity
        pipeline = self.redis_client.pipeline()
        
        for opp in opportunities:
            timestamp = int(opp.timestamp * 1000)  # milliseconds
            key = f"opportunity:{timestamp}:{opp.buy_exchange}:{opp.sell_exchange}:{opp.base_currency}"
            
            data = {
                'buy_exchange': opp.buy_exchange,
                'sell_exchange': opp.sell_exchange,
                'base_currency': opp.base_currency,
                'quote_currency': opp.quote_currency,
                'buy_price': opp.buy_price,
                'sell_price': opp.sell_price,
                'profit_percentage': round(opp.profit_percentage, 2),
                'volume': opp.volume,
                'timestamp': opp.timestamp
            }
            
            pipeline.setex(key, 30, json.dumps(data))
        
        await pipeline.execute()
        
        # Broadcast to WebSocket
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        if channel_layer:
            opportunities_data = [
                {
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'base_currency': opp.base_currency,
                    'quote_currency': opp.quote_currency,
                    'buy_price': round(opp.buy_price, 6),
                    'sell_price': round(opp.sell_price, 6),
                    'profit_percentage': round(opp.profit_percentage, 2),
                    'volume': round(opp.volume, 4),
                    'timestamp': opp.timestamp
                }
                for opp in opportunities[:50]  # Send only top 50
            ]
            
            await channel_layer.group_send(
                'arbitrage_updates',
                {
                    'type': 'send_opportunities',
                    'opportunities': opportunities_data
                }
            )

    async def stop_calculation(self):
        """Stop calculation"""
        self.is_running = False
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Fast arbitrage calculation stopped")