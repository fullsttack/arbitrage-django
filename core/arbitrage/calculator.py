import asyncio
import json
import logging
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
    profit_amount: float
    profit_percentage: float
    volume: float
    timestamp: float

class FastArbitrageCalculator:
    def __init__(self):
        self.is_running = False
        self.channel_layer = get_channel_layer()
        self.trading_pairs_cache = {}
        self.last_cache_update = 0
        
    async def start_calculation(self):
        """Start arbitrage calculation loop"""
        self.is_running = True
        logger.info("FastArbitrageCalculator started")
        
        while self.is_running:
            try:
                start_time = asyncio.get_event_loop().time()
                
                # Update trading pairs cache every 30 seconds
                if start_time - self.last_cache_update > 30:
                    await self._update_trading_pairs_cache()
                    self.last_cache_update = start_time
                
                # Find arbitrage opportunities
                opportunities = await self._find_arbitrage_opportunities()
                
                if opportunities:
                    # Save opportunities
                    await self._save_opportunities(opportunities)
                    
                    # Only broadcast significant opportunities (> 1% profit) to reduce channel load
                    significant_opportunities = [opp for opp in opportunities if opp.profit_percentage > 1.0]
                    if significant_opportunities:
                        await self._broadcast_opportunities(significant_opportunities)
                    
                    performance_logger.info(f"Found {len(opportunities)} arbitrage opportunities ({len(significant_opportunities)} significant)")
                
                # Calculate processing time
                processing_time = asyncio.get_event_loop().time() - start_time
                performance_logger.debug(f"Arbitrage calculation took {processing_time:.4f}s")
                
                # Sleep to maintain 200ms cycle (reduced to prevent channel overflow)
                await asyncio.sleep(max(0.2 - processing_time, 0.1))
                
            except Exception as e:
                logger.error(f"Error in arbitrage calculation: {e}")
                await asyncio.sleep(1)

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
        """Find arbitrage opportunities between exchanges"""
        opportunities = []
        
        try:
            # Get all current prices from Redis
            all_prices = await redis_manager.get_all_current_prices()
            
            if not all_prices:
                return opportunities
            
            # Group prices by currency pair
            price_groups = self._group_prices_by_pair(all_prices)
            
            # Check each currency pair for arbitrage opportunities
            for currency_pair, prices in price_groups.items():
                if len(prices) < 2:  # Need at least 2 exchanges
                    continue
                
                # Find opportunities within this currency pair
                pair_opportunities = await self._check_pair_arbitrage(currency_pair, prices)
                opportunities.extend(pair_opportunities)
            
        except Exception as e:
            logger.error(f"Error finding arbitrage opportunities: {e}")
        
        return opportunities

    def _group_prices_by_pair(self, all_prices: Dict[str, Any]) -> Dict[str, List[PricePoint]]:
        """Group prices by currency pair"""
        price_groups = {}
        
        for key, price_data in all_prices.items():
            try:
                # Extract exchange and symbol from key: "prices:exchange:symbol"
                parts = key.split(':')
                if len(parts) < 3:
                    continue
                    
                exchange = parts[1]
                symbol = parts[2]
                
                # Find corresponding trading pair in cache
                trading_pair_info = None
                currency_pair = None
                
                for cp, pairs in self.trading_pairs_cache.items():
                    for pair in pairs:
                        if pair['exchange'] == exchange and pair['symbol'] == symbol:
                            trading_pair_info = pair
                            currency_pair = cp
                            break
                    if trading_pair_info:
                        break
                
                if not trading_pair_info or not currency_pair:
                    continue
                
                # Create PricePoint
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
                logger.error(f"Error processing price data for {key}: {e}")
                continue
        
        return price_groups

    async def _check_pair_arbitrage(self, currency_pair: str, prices: List[PricePoint]) -> List[ArbitrageOpportunity]:
        """Check arbitrage opportunities for a specific currency pair"""
        opportunities = []
        
        try:
            base_currency, quote_currency = currency_pair.split('_')
            
            # Compare all combinations of exchanges
            for i, price1 in enumerate(prices):
                for j, price2 in enumerate(prices):
                    if i >= j:  # Avoid duplicate comparisons
                        continue
                    
                    # Check if price1.bid > price2.ask (sell at price1, buy at price2)
                    opportunity1 = self._calculate_opportunity(
                        base_currency, quote_currency,
                        buy_exchange=price2.exchange,
                        sell_exchange=price1.exchange,
                        buy_price=price2.ask_price,
                        sell_price=price1.bid_price,
                        buy_settings=price2,
                        sell_settings=price1
                    )
                    
                    if opportunity1:
                        opportunities.append(opportunity1)
                    
                    # Check if price2.bid > price1.ask (sell at price2, buy at price1)
                    opportunity2 = self._calculate_opportunity(
                        base_currency, quote_currency,
                        buy_exchange=price1.exchange,
                        sell_exchange=price2.exchange,
                        buy_price=price1.ask_price,
                        sell_price=price2.bid_price,
                        buy_settings=price1,
                        sell_settings=price2
                    )
                    
                    if opportunity2:
                        opportunities.append(opportunity2)
            
        except Exception as e:
            logger.error(f"Error checking arbitrage for {currency_pair}: {e}")
        
        return opportunities

    def _calculate_opportunity(self, base_currency: str, quote_currency: str,
                             buy_exchange: str, sell_exchange: str,
                             buy_price: float, sell_price: float,
                             buy_settings: PricePoint, sell_settings: PricePoint) -> Optional[ArbitrageOpportunity]:
        """Calculate arbitrage opportunity"""
        try:
            # Check if profitable: sell_price > buy_price
            if sell_price <= buy_price:
                return None
            
            # Calculate profit percentage
            profit_percentage = ((sell_price - buy_price) / buy_price) * 100
            
            # Use minimum threshold from both exchanges
            min_threshold = min(buy_settings.arbitrage_threshold, sell_settings.arbitrage_threshold)
            
            # Check if profit meets threshold
            if profit_percentage < min_threshold:
                return None
            
            # Calculate volume constraints
            min_volume = max(buy_settings.min_volume, sell_settings.min_volume)
            max_volume = min(buy_settings.max_volume, sell_settings.max_volume)
            
            # For buy from exchange A, we need to check ask_volume of that exchange
            # For sell to exchange B, we need to check bid_volume of that exchange
            available_volume = min(buy_settings.ask_volume, sell_settings.bid_volume)
            
            # Tradeable volume
            trade_volume = min(available_volume, max_volume)
            
            # Check if volume is within constraints
            if trade_volume < min_volume:
                return None
            
            # Calculate profit amount
            profit_amount = (sell_price - buy_price) * trade_volume
            
            return ArbitrageOpportunity(
                base_currency=base_currency,
                quote_currency=quote_currency,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
                profit_amount=profit_amount,
                profit_percentage=profit_percentage,
                volume=trade_volume,
                timestamp=asyncio.get_event_loop().time()
            )
            
        except Exception as e:
            logger.error(f"Error calculating opportunity: {e}")
            return None

    async def _save_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Save opportunities to Redis"""
        for opp in opportunities:
            opportunity_data = {
                'base_currency': opp.base_currency,
                'quote_currency': opp.quote_currency,
                'symbol': f"{opp.base_currency}/{opp.quote_currency}",
                'buy_exchange': opp.buy_exchange,
                'sell_exchange': opp.sell_exchange,
                'buy_price': opp.buy_price,
                'sell_price': opp.sell_price,
                'profit_amount': opp.profit_amount,
                'profit_percentage': round(opp.profit_percentage, 2),
                'volume': opp.volume,
                'timestamp': opp.timestamp
            }
            
            await redis_manager.save_arbitrage_opportunity(opportunity_data)

    async def _broadcast_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """Broadcast opportunities to WebSocket"""
        if self.channel_layer:
            opportunities_data = []
            for opp in opportunities:
                opportunities_data.append({
                    'symbol': f"{opp.base_currency}/{opp.quote_currency}",
                    'buy_exchange': opp.buy_exchange,
                    'sell_exchange': opp.sell_exchange,
                    'profit_percentage': round(opp.profit_percentage, 2),
                    'profit_amount': round(opp.profit_amount, 4),
                    'volume': opp.volume,
                    'buy_price': opp.buy_price,
                    'sell_price': opp.sell_price,
                    'timestamp': opp.timestamp
                })
            
            await self.channel_layer.group_send(
                'arbitrage_updates',
                {
                    'type': 'send_opportunities',
                    'opportunities': opportunities_data
                }
            )

    async def stop_calculation(self):
        """Stop arbitrage calculation"""
        self.is_running = False
        logger.info("FastArbitrageCalculator stopped")