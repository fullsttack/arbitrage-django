import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from core.redis_manager import redis_manager
from core.models import TradingPair

logger = logging.getLogger(__name__)
performance_logger = logging.getLogger('performance')

@dataclass
class PricePoint:
    exchange: str
    symbol: str
    bid_price: float  # highest buy price
    ask_price: float  # lowest sell price
    bid_volume: float  # buy volume
    ask_volume: float  # sell volume
    timestamp: float
    # Trading pair settings
    arbitrage_threshold: float
    min_volume: float
    max_volume: float

@dataclass
class ArbitrageOpportunity:
    base_currency: str
    quote_currency: str
    buy_exchange: str  # exchange where we buy
    sell_exchange: str  # exchange where we sell
    buy_price: float  # buy price (ask price)
    sell_price: float  # sell price (bid price)
    buy_volume: float  # available buy volume (ask volume on buy exchange)
    sell_volume: float  # available sell volume (bid volume on sell exchange)
    trade_volume: float  # actual tradeable volume (minimum of buy/sell)
    profit_amount: float
    profit_percentage: float
    timestamp: float

class FastArbitrageCalculator:
    def __init__(self):
        self.is_running = False
        self.channel_layer = get_channel_layer()
        self.trading_pairs_cache = {}
        self.last_cache_update = 0
        self.calculation_count = 0
        self.last_opportunities_count = 0
        
        # Performance optimization settings
        self.CACHE_UPDATE_INTERVAL = 30  # Update cache every 30 seconds
        self.CALCULATION_INTERVAL = 0.15  # Faster calculation interval (150ms)
        self.MIN_CALCULATION_INTERVAL = 0.05  # Minimum interval (50ms)
        self.SIGNIFICANT_PROFIT_THRESHOLD = 1.0  # Only broadcast opportunities > 1%
        
    async def start_calculation(self):
        """Start arbitrage calculation loop with enhanced performance"""
        self.is_running = True
        logger.info("FastArbitrageCalculator started with enhanced performance")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Update trading pairs cache periodically
                if start_time - self.last_cache_update > self.CACHE_UPDATE_INTERVAL:
                    await self._update_trading_pairs_cache()
                    self.last_cache_update = start_time
                
                # Find arbitrage opportunities
                opportunities = await self._find_arbitrage_opportunities()
                
                if opportunities:
                    # Save all opportunities
                    await self._save_opportunities(opportunities)
                    
                    # Only broadcast significant opportunities to reduce channel load
                    significant_opportunities = [
                        opp for opp in opportunities 
                        if opp.profit_percentage > self.SIGNIFICANT_PROFIT_THRESHOLD
                    ]
                    
                    if significant_opportunities:
                        await self._broadcast_opportunities(significant_opportunities)
                    
                    # Log performance metrics
                    if len(opportunities) != self.last_opportunities_count:
                        performance_logger.info(
                            f"Arbitrage: Found {len(opportunities)} opportunities "
                            f"({len(significant_opportunities)} significant, "
                            f"threshold: {self.SIGNIFICANT_PROFIT_THRESHOLD}%)"
                        )
                        self.last_opportunities_count = len(opportunities)
                
                # Calculate processing time and adjust interval
                processing_time = time.time() - start_time
                
                # Dynamic interval adjustment based on processing time
                if processing_time > self.CALCULATION_INTERVAL:
                    sleep_time = self.MIN_CALCULATION_INTERVAL
                    if self.calculation_count % 100 == 0:  # Log every 100 calculations
                        logger.warning(f"Arbitrage calculation taking {processing_time:.3f}s, reducing interval")
                else:
                    sleep_time = max(self.MIN_CALCULATION_INTERVAL, self.CALCULATION_INTERVAL - processing_time)
                
                self.calculation_count += 1
                
                # Performance logging every 1000 calculations
                if self.calculation_count % 1000 == 0:
                    performance_logger.debug(f"Arbitrage: {self.calculation_count} calculations, avg time: {processing_time:.3f}s")
                
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in arbitrage calculation: {e}")
                await asyncio.sleep(1)  # Wait longer on error

    @database_sync_to_async
    def _update_trading_pairs_cache_sync(self):
        """Update trading pairs cache from database (sync version)"""
        try:
            # Get active trading pairs
            pairs = TradingPair.objects.filter(
                is_active=True,
                exchange__is_active=True
            ).select_related('exchange', 'base_currency', 'quote_currency')
            
            trading_pairs_cache = {}
            
            for pair in pairs:
                key = f"{pair.base_currency.symbol}_{pair.quote_currency.symbol}"
                if key not in trading_pairs_cache:
                    trading_pairs_cache[key] = []
                
                trading_pairs_cache[key].append({
                    'exchange': pair.exchange.name,
                    'symbol': pair.api_symbol,
                    'arbitrage_threshold': float(pair.arbitrage_threshold),
                    'min_volume': float(pair.min_volume),
                    'max_volume': float(pair.max_volume)
                })
            
            logger.debug(f"Updated trading pairs cache: {len(trading_pairs_cache)} currency pairs")
            return trading_pairs_cache
            
        except Exception as e:
            logger.error(f"Error updating trading pairs cache: {e}")
            return {}
            
    async def _update_trading_pairs_cache(self):
        """Update trading pairs cache from database"""
        self.trading_pairs_cache = await self._update_trading_pairs_cache_sync()

    async def _find_arbitrage_opportunities(self) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities between exchanges with optimized performance"""
        opportunities = []
        
        try:
            # Get all current prices from Redis
            all_prices = await redis_manager.get_all_current_prices()
            
            if not all_prices:
                return opportunities
            
            # Group prices by currency pair with optimized processing
            price_groups = self._group_prices_by_pair_optimized(all_prices)
            
            # Check each currency pair for arbitrage opportunities
            for currency_pair, prices in price_groups.items():
                if len(prices) < 2:  # Need at least 2 exchanges
                    continue
                
                # Find opportunities within this currency pair
                pair_opportunities = await self._check_pair_arbitrage_optimized(currency_pair, prices)
                opportunities.extend(pair_opportunities)
            
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities: {e}")
        
        return opportunities

    def _group_prices_by_pair_optimized(self, all_prices: Dict[str, Any]) -> Dict[str, List[PricePoint]]:
        """Optimized version of price grouping"""
        price_groups = {}
        
        # Pre-build lookup for trading pairs to avoid repeated dictionary lookups
        exchange_symbol_to_pair = {}
        for currency_pair, pairs in self.trading_pairs_cache.items():
            for pair in pairs:
                key = f"{pair['exchange']}:{pair['symbol']}"
                exchange_symbol_to_pair[key] = (currency_pair, pair)
        
        for redis_key, price_data in all_prices.items():
            try:
                # Extract exchange and symbol from key: "prices:exchange:symbol"
                parts = redis_key.split(':', 2)  # Limit splits for performance
                if len(parts) < 3:
                    continue
                    
                exchange = parts[1]
                symbol = parts[2]
                lookup_key = f"{exchange}:{symbol}"
                
                # Fast lookup using pre-built dictionary
                if lookup_key not in exchange_symbol_to_pair:
                    continue
                
                currency_pair, trading_pair_info = exchange_symbol_to_pair[lookup_key]
                
                # Create PricePoint with optimized data access
                price_point = PricePoint(
                    exchange=exchange,
                    symbol=symbol,
                    bid_price=price_data['bid_price'],
                    ask_price=price_data['ask_price'],
                    bid_volume=price_data.get('bid_volume', 0),
                    ask_volume=price_data.get('ask_volume', 0),
                    timestamp=price_data['timestamp'],
                    arbitrage_threshold=trading_pair_info['arbitrage_threshold'],
                    min_volume=trading_pair_info['min_volume'],
                    max_volume=trading_pair_info['max_volume']
                )
                
                if currency_pair not in price_groups:
                    price_groups[currency_pair] = []
                
                price_groups[currency_pair].append(price_point)
                
            except Exception as e:
                logger.debug(f"Error processing price data for {redis_key}: {e}")
                continue
        
        return price_groups

    async def _check_pair_arbitrage_optimized(self, currency_pair: str, prices: List[PricePoint]) -> List[ArbitrageOpportunity]:
        """Optimized arbitrage checking for a specific currency pair"""
        opportunities = []
        
        try:
            base_currency, quote_currency = currency_pair.split('_', 1)
            
            # Pre-sort prices for optimization if needed
            num_exchanges = len(prices)
            
            # For small number of exchanges, use simple nested loop
            # For larger numbers, could implement more sophisticated algorithms
            for i in range(num_exchanges):
                price1 = prices[i]
                for j in range(i + 1, num_exchanges):
                    price2 = prices[j]
                    
                    # Check both directions efficiently
                    # Direction 1: buy at price2, sell at price1
                    if price1.bid_price > price2.ask_price:
                        opportunity = self._calculate_opportunity_fast(
                            base_currency, quote_currency,
                            price2, price1,  # buy_settings, sell_settings
                            price2.ask_price, price1.bid_price  # buy_price, sell_price
                        )
                        if opportunity:
                            opportunities.append(opportunity)
                    
                    # Direction 2: buy at price1, sell at price2
                    if price2.bid_price > price1.ask_price:
                        opportunity = self._calculate_opportunity_fast(
                            base_currency, quote_currency,
                            price1, price2,  # buy_settings, sell_settings
                            price1.ask_price, price2.bid_price  # buy_price, sell_price
                        )
                        if opportunity:
                            opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error checking arbitrage for {currency_pair}: {e}")
        
        return opportunities

    def _calculate_opportunity_fast(self, base_currency: str, quote_currency: str,
                                  buy_settings: PricePoint, sell_settings: PricePoint,
                                  buy_price: float, sell_price: float) -> Optional[ArbitrageOpportunity]:
        """Fast opportunity calculation with separate buy/sell volumes"""
        try:
            # Quick profit check first (most opportunities will fail this)
            if sell_price <= buy_price:
                return None
            
            # Calculate profit percentage
            profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Use minimum threshold from both exchanges
            min_threshold = min(buy_settings.arbitrage_threshold, sell_settings.arbitrage_threshold)
            
            # Quick threshold check
            if profit_percentage < min_threshold:
                return None
            
            # Calculate volume constraints (only if profitable)
            min_volume = max(buy_settings.min_volume, sell_settings.min_volume)
            max_volume = min(buy_settings.max_volume, sell_settings.max_volume)
            
            # Available volumes for buy and sell
            buy_available_volume = buy_settings.ask_volume  # volume available for buying
            sell_available_volume = sell_settings.bid_volume  # volume available for selling
            
            # Actual tradeable volume is the minimum
            trade_volume = min(buy_available_volume, sell_available_volume, max_volume)
            
            # Volume constraint check
            if trade_volume < min_volume:
                return None
            
            # Calculate profit amount
            profit_amount = (sell_price - buy_price) * trade_volume
            
            return ArbitrageOpportunity(
                base_currency=base_currency,
                quote_currency=quote_currency,
                buy_exchange=buy_settings.exchange,
                sell_exchange=sell_settings.exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                buy_volume=buy_available_volume,
                sell_volume=sell_available_volume,
                trade_volume=trade_volume,
                profit_amount=profit_amount,
                profit_percentage=profit_percentage,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.debug(f"Error calculating opportunity: {e}")
            return None

    async def _save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Save opportunities to Redis with batch processing"""
        try:
            # Batch save for better performance
            save_tasks = []
            for opp in opportunities:
                opportunity_data = {
                    'base_currency': opp.base_currency,
                    'quote_currency': opp.quote_currency,
                    'symbol': f"{opp.base_currency}/{opp.quote_currency}",
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'buy_volume': opp.buy_volume,
                    'sell_volume': opp.sell_volume,
                    'trade_volume': opp.trade_volume,
                    'profit_amount': opp.profit_amount,
                    'profit_percentage': round(opp.profit_percentage, 2),
                    'timestamp': opp.timestamp
                }
                
                save_tasks.append(redis_manager.save_arbitrage_opportunity(opportunity_data))
            
            # Execute all saves concurrently
            if save_tasks:
                await asyncio.gather(*save_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error saving opportunities: {e}")

    async def _broadcast_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Broadcast opportunities to WebSocket with rate limiting"""
        if not self.channel_layer:
            return
            
        try:
            opportunities_data = []
            for opp in opportunities:
                opportunities_data.append({
                    'symbol': f"{opp.base_currency}/{opp.quote_currency}",
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'profit_percentage': round(opp.profit_percentage, 2),
                    'profit_amount': round(opp.profit_amount, 4),
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'buy_volume': opp.buy_volume,
                    'sell_volume': opp.sell_volume,
                    'trade_volume': opp.trade_volume,
                    'timestamp': opp.timestamp
                })
            
            await self.channel_layer.group_send(
                'arbitrage_updates',
                {
                    'type': 'send_opportunities',
                    'opportunities': opportunities_data
                }
            )
            
        except Exception as e:
            # Don't let broadcast errors stop the calculation
            logger.debug(f"Broadcast error (non-critical): {e}")

    async def stop_calculation(self):
        """Stop arbitrage calculation"""
        self.is_running = False
        performance_logger.info(f"FastArbitrageCalculator stopped after {self.calculation_count} calculations")