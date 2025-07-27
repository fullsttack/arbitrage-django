// CSRF Token Helper
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

class ArbitrageDashboard {
    constructor() {
        this.websocket = null;
        this.reconnectInterval = 5000;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.pricesData = new Map();
        this.allPricesData = new Map();
        this.opportunitiesData = [];
        this.allOpportunitiesData = [];
        this.opportunitiesMap = new Map();
        this.currencyNames = {};
        this.bestOpportunity = null;
        
        // Ramzinex pair_id to symbol mapping
        this.ramzinexMapping = {
            '13': { symbol: 'ETH/USDT', currency: 'ETH', name: 'Ethereum' },
            '432': { symbol: 'DOGE/USDT', currency: 'DOGE', name: 'Dogecoin' },
            '509': { symbol: 'NOT/USDT', currency: 'NOT', name: 'Notcoin' },
            '643': { symbol: 'XRP/USDT', currency: 'XRP', name: 'Ripple' }
        };
        this.lastUpdateTimes = new Map();
        this.totalOpportunitiesCount = 0;
        this.isInitialDataLoaded = false;
        
        // Pagination
        this.currentPage = 1;
        this.itemsPerPage = 20;
        
        // Filters and Sorting
        this.priceFilters = {
            exchange: 'all',
            currency: 'all',
            search: ''
        };
        this.priceSort = { column: null, direction: 'asc' };
        this.opportunityFilters = {
            minProfit: 0,
            sort: 'time_desc'
        };
        
        // Performance tracking
        this.performanceMetrics = {
            priceUpdates: 0,
            opportunityUpdates: 0,
            lastMinute: Date.now()
        };
        
        this.init();
    }

    init() {
        this.setupTabs();
        this.setupPagination();
        this.setupFilters();
        this.setupEventListeners();
        
        this.loadInitialData().then(() => {
            this.setupWebSocket();
            this.isInitialDataLoaded = true;
        }).catch(error => {
            this.setupWebSocket();
        });
        
        // Auto-refresh stats every 30 seconds
        setInterval(() => this.loadSystemStats(), 30000);
        
        // Update performance metrics every minute
        setInterval(() => this.updatePerformanceMetrics(), 60000);
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadInitialData();
        });
        
        // Export opportunities
        document.getElementById('export-opportunities')?.addEventListener('click', () => {
            this.exportOpportunities();
        });
        
        // Refresh monitoring
        document.getElementById('refresh-monitoring')?.addEventListener('click', () => {
            this.loadSystemStats();
        });
    }

    setupFilters() {
        // Price filters
        const exchangeFilter = document.getElementById('exchange-filter');
        const currencyFilter = document.getElementById('currency-filter');
        const symbolSearch = document.getElementById('symbol-search');
        const clearFilters = document.getElementById('clear-filters');
        
        exchangeFilter?.addEventListener('change', (e) => {
            this.priceFilters.exchange = e.target.value;
            this.applyPriceFilters();
        });
        
        currencyFilter?.addEventListener('change', (e) => {
            this.priceFilters.currency = e.target.value;
            this.applyPriceFilters();
        });
        
        symbolSearch?.addEventListener('input', (e) => {
            this.priceFilters.search = e.target.value.toLowerCase();
            this.applyPriceFilters();
        });
        
        clearFilters?.addEventListener('click', () => {
            this.clearPriceFilters();
        });
        
        // Opportunity filters
        const minProfitFilter = document.getElementById('min-profit-filter');
        const opportunitiesSort = document.getElementById('opportunities-sort');
        
        minProfitFilter?.addEventListener('input', (e) => {
            this.opportunityFilters.minProfit = parseFloat(e.target.value) || 0;
            this.applyOpportunityFilters();
        });
        
        opportunitiesSort?.addEventListener('change', (e) => {
            this.opportunityFilters.sort = e.target.value;
            this.applyOpportunityFilters();
        });
        
        // Price table sorting
        document.querySelectorAll('#content-prices .sortable').forEach(header => {
            header.addEventListener('click', () => {
                this.sortPrices(header.dataset.sort);
            });
        });
    }

    populateFilterDropdowns() {
        // Populate exchange filter
        const exchanges = [...new Set(Array.from(this.allPricesData.values()).map(p => p.exchange))];
        const exchangeFilter = document.getElementById('exchange-filter');
        if (exchangeFilter) {
            exchangeFilter.innerHTML = '<option value="all">All Exchanges</option>';
            exchanges.forEach(exchange => {
                exchangeFilter.innerHTML += `<option value="${exchange}">${exchange.charAt(0).toUpperCase() + exchange.slice(1)}</option>`;
            });
        }
        
        // Populate currency filter with enhanced data
        const currencies = [...new Set(Array.from(this.allPricesData.values()).map(p => {
            // Apply Ramzinex mapping for currency extraction
            if (p.exchange === 'ramzinex' && this.ramzinexMapping[p.symbol]) {
                return this.ramzinexMapping[p.symbol].currency;
            }
            if (p.base_currency) {
                return p.base_currency;
            }
            return this.extractBaseSymbol(p.symbol);
        }))];
        
        const currencyFilter = document.getElementById('currency-filter');
        if (currencyFilter) {
            currencyFilter.innerHTML = '<option value="all">All Currencies</option>';
            currencies.forEach(currency => {
                // Find a price entry for this currency to get the display name
                const samplePrice = Array.from(this.allPricesData.values()).find(p => {
                    if (p.exchange === 'ramzinex' && this.ramzinexMapping[p.symbol]) {
                        return this.ramzinexMapping[p.symbol].currency === currency;
                    }
                    return (p.base_currency && p.base_currency === currency) || 
                           this.extractBaseSymbol(p.symbol) === currency;
                });
                
                // Get currency name with Ramzinex mapping
                let currencyName = currency;
                if (samplePrice?.exchange === 'ramzinex' && this.ramzinexMapping[samplePrice.symbol]) {
                    currencyName = this.ramzinexMapping[samplePrice.symbol].name;
                } else {
                    currencyName = samplePrice?.currency_name || this.currencyNames[currency] || currency;
                }
                
                currencyFilter.innerHTML += `<option value="${currency}">${currencyName} (${currency})</option>`;
            });
        }
    }

    applyPriceFilters() {
        let filteredPrices = Array.from(this.allPricesData.values());
        
        // Apply exchange filter
        if (this.priceFilters.exchange !== 'all') {
            filteredPrices = filteredPrices.filter(p => p.exchange === this.priceFilters.exchange);
        }
        
        // Apply currency filter
        if (this.priceFilters.currency !== 'all') {
            filteredPrices = filteredPrices.filter(p => {
                // Apply Ramzinex mapping for filtering
                if (p.exchange === 'ramzinex' && this.ramzinexMapping[p.symbol]) {
                    return this.ramzinexMapping[p.symbol].currency === this.priceFilters.currency;
                }
                if (p.base_currency) {
                    return p.base_currency === this.priceFilters.currency;
                }
                return this.extractBaseSymbol(p.symbol) === this.priceFilters.currency;
            });
        }
        
        // Apply search filter
        if (this.priceFilters.search) {
            filteredPrices = filteredPrices.filter(p => 
                p.symbol.toLowerCase().includes(this.priceFilters.search) ||
                (p.display_symbol && p.display_symbol.toLowerCase().includes(this.priceFilters.search)) ||
                (p.currency_name && p.currency_name.toLowerCase().includes(this.priceFilters.search)) ||
                p.exchange.toLowerCase().includes(this.priceFilters.search)
            );
        }
        
        // Convert back to Map
        this.pricesData = new Map();
        filteredPrices.forEach(price => {
            const key = `${price.exchange}_${price.symbol}`;
            this.pricesData.set(key, price);
        });
        
        this.updatePricesTable(filteredPrices);
        
        // Update filter count
        const filteredCount = document.getElementById('prices-filtered-count');
        if (filteredPrices.length !== this.allPricesData.size) {
            filteredCount.textContent = `${filteredPrices.length} shown`;
            filteredCount.classList.remove('hidden');
        } else {
            filteredCount.classList.add('hidden');
        }
    }

    applyOpportunityFilters() {
        let filteredOpportunities = [...this.allOpportunitiesData];
        
        // Apply minimum profit filter
        if (this.opportunityFilters.minProfit > 0) {
            filteredOpportunities = filteredOpportunities.filter(opp => 
                opp.profit_percentage >= this.opportunityFilters.minProfit
            );
        }
        
        // Apply sorting
        this.sortOpportunities(filteredOpportunities);
        
        this.opportunitiesData = filteredOpportunities;
        this.currentPage = 1; // Reset to first page
        this.updateOpportunitiesTable();
        
        // Update filter count
        const filteredCount = document.getElementById('opportunities-filtered-count');
        if (filteredOpportunities.length !== this.allOpportunitiesData.length) {
            filteredCount.textContent = `${filteredOpportunities.length} shown`;
            filteredCount.classList.remove('hidden');
        } else {
            filteredCount.classList.add('hidden');
        }
        
        // Update stats box with actual filtered count
        this.updateOpportunitiesStats(filteredOpportunities.length);
    }

    sortOpportunities(opportunities) {
        switch (this.opportunityFilters.sort) {
            case 'time_desc':
                opportunities.sort((a, b) => (b.last_seen || b.timestamp || 0) - (a.last_seen || a.timestamp || 0));
                break;
            case 'time_asc':
                opportunities.sort((a, b) => (a.last_seen || a.timestamp || 0) - (b.last_seen || b.timestamp || 0));
                break;
            case 'profit_desc':
                opportunities.sort((a, b) => b.profit_percentage - a.profit_percentage);
                break;
            case 'profit_asc':
                opportunities.sort((a, b) => a.profit_percentage - b.profit_percentage);
                break;
            case 'exchange':
                opportunities.sort((a, b) => {
                    const aExchange = `${a.buy_exchange}_${a.sell_exchange}`;
                    const bExchange = `${b.buy_exchange}_${b.sell_exchange}`;
                    return aExchange.localeCompare(bExchange);
                });
                break;
        }
    }

    sortPrices(column) {
        if (this.priceSort.column === column) {
            this.priceSort.direction = this.priceSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.priceSort.column = column;
            this.priceSort.direction = 'asc';
        }
        
        // Update header indicators
        document.querySelectorAll('#content-prices .sortable').forEach(header => {
            header.classList.remove('sorted-asc', 'sorted-desc');
            if (header.dataset.sort === column) {
                header.classList.add(`sorted-${this.priceSort.direction}`);
            }
        });
        
        // Sort the filtered data
        const sortedPrices = Array.from(this.pricesData.values()).sort((a, b) => {
            let aVal, bVal;
            
            switch (column) {
                case 'exchange':
                    aVal = a.exchange;
                    bVal = b.exchange;
                    break;
                case 'symbol':
                    aVal = a.display_symbol || a.symbol;
                    bVal = b.display_symbol || b.symbol;
                    break;
                case 'currency':
                    aVal = a.base_currency || this.extractBaseSymbol(a.symbol);
                    bVal = b.base_currency || this.extractBaseSymbol(b.symbol);
                    break;
                case 'bid_price':
                    aVal = a.bid_price;
                    bVal = b.bid_price;
                    break;
                case 'ask_price':
                    aVal = a.ask_price;
                    bVal = b.ask_price;
                    break;
                case 'spread':
                    aVal = ((a.ask_price - a.bid_price) / a.bid_price) * 100;
                    bVal = ((b.ask_price - b.bid_price) / b.bid_price) * 100;
                    break;
                case 'bid_volume':
                    aVal = a.bid_volume;
                    bVal = b.bid_volume;
                    break;
                case 'ask_volume':
                    aVal = a.ask_volume;
                    bVal = b.ask_volume;
                    break;
                case 'timestamp':
                    aVal = a.timestamp;
                    bVal = b.timestamp;
                    break;
                default:
                    return 0;
            }
            
            if (typeof aVal === 'string') {
                return this.priceSort.direction === 'asc' ? 
                    aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            } else {
                return this.priceSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
            }
        });
        
        this.updatePricesTable(sortedPrices);
    }

    clearPriceFilters() {
        this.priceFilters = { exchange: 'all', currency: 'all', search: '' };
        
        document.getElementById('exchange-filter').value = 'all';
        document.getElementById('currency-filter').value = 'all';
        document.getElementById('symbol-search').value = '';
        
        this.pricesData = new Map(this.allPricesData);
        this.updatePricesTable(Array.from(this.allPricesData.values()));
        
        document.getElementById('prices-filtered-count').classList.add('hidden');
    }

    exportOpportunities() {
        const dataToExport = this.opportunitiesData.map((opp, index) => ({
            '#': index + 1,
            'Symbol': opp.symbol || `${opp.base_currency}/${opp.quote_currency}`,
            'Buy Exchange': opp.buy_exchange,
            'Sell Exchange': opp.sell_exchange,
            'Buy Price': opp.buy_price,
            'Sell Price': opp.sell_price,
            'Profit %': opp.profit_percentage.toFixed(2),
            'Trade Volume': opp.trade_volume || 0,
            'Last Seen': new Date((opp.last_seen || opp.timestamp) * 1000).toLocaleString()
        }));
        
        const csv = this.arrayToCSV(dataToExport);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `arbitrage_opportunities_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
        
        this.showToast('Opportunities exported successfully!', 'success');
    }

    arrayToCSV(data) {
        if (!data.length) return '';
        
        const headers = Object.keys(data[0]);
        const csvHeaders = headers.join(',');
        const csvRows = data.map(row => 
            headers.map(header => {
                const value = row[header];
                return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
            }).join(',')
        );
        
        return [csvHeaders, ...csvRows].join('\n');
    }

    updatePerformanceMetrics() {
        const now = Date.now();
        const timeDiff = (now - this.performanceMetrics.lastMinute) / 60000; // Convert to minutes
        
        if (timeDiff >= 1) {
            // Calculate rates per minute
            const priceRate = Math.round(this.performanceMetrics.priceUpdates / timeDiff);
            const opportunityRate = Math.round(this.performanceMetrics.opportunityUpdates / timeDiff);
            
            // Update display
            document.getElementById('price-updates-rate').textContent = priceRate;
            document.getElementById('opportunity-rate').textContent = opportunityRate;
            document.getElementById('websocket-status').textContent = this.websocket?.readyState === 1 ? 'Connected' : 'Disconnected';
            
            // Reset counters
            this.performanceMetrics.priceUpdates = 0;
            this.performanceMetrics.opportunityUpdates = 0;
            this.performanceMetrics.lastMinute = now;
        }
    }

    setupTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabId = button.id.replace('tab-', '');
                
                tabButtons.forEach(btn => {
                    btn.classList.remove('active', 'border-primary-500', 'text-primary-500');
                    btn.classList.add('border-transparent', 'text-gray-400');
                });
                
                button.classList.add('active', 'border-primary-500', 'text-primary-500');
                button.classList.remove('border-transparent', 'text-gray-400');
                
                tabContents.forEach(content => {
                    content.classList.add('hidden');
                });
                
                document.getElementById(`content-${tabId}`).classList.remove('hidden');
            });
        });
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/arbitrage/`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.updateConnectionStatus(true);
                this.reconnectAttempts = 0;
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                this.updateConnectionStatus(false);
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            this.updateConnectionStatus(false);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            
            setTimeout(() => {
                this.setupWebSocket();
            }, this.reconnectInterval);
        } else {
            this.showToast('Connection lost. Please refresh the page.', 'error');
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'initial_prices':
                this.updateAllPricesData(data.data);
                break;
            case 'price_update':
                this.updateSinglePrice(data.data);
                this.performanceMetrics.priceUpdates++;
                break;
            case 'initial_opportunities':
                if (!this.isInitialDataLoaded) {
                    this.handleInitialOpportunities(data.data);
                }
                break;
            case 'opportunities_update':
                this.handleNewOpportunities(data.data);
                this.performanceMetrics.opportunityUpdates += data.data?.length || 0;
                break;
            case 'best_opportunity_update':
                this.updateBestOpportunityDisplay(data.data);
                break;
            case 'redis_stats':
                this.updateSystemStats(data.data);
                break;
        }
    }

    updateAllPricesData(prices) {
        if (!prices || !Array.isArray(prices)) return;
        
        // Store all prices
        this.allPricesData.clear();
        prices.forEach(price => {
            const key = `${price.exchange}_${price.symbol}`;
            this.allPricesData.set(key, price);
        });
        
        // Populate filter dropdowns
        this.populateFilterDropdowns();
        
        // Apply current filters
        this.applyPriceFilters();
    }

    handleInitialOpportunities(opportunities) {
        this.allOpportunitiesData = [];
        this.opportunitiesMap.clear();
        
        if (opportunities && Array.isArray(opportunities)) {
            opportunities.forEach(opp => this.addOrUpdateOpportunity(opp, false));
        }
        
        this.applyOpportunityFilters();
    }

    createOpportunityKey(opp) {
        const keyParts = [
            opp.buy_exchange || '',
            opp.sell_exchange || '',
            opp.symbol || (opp.base_currency + '/' + opp.quote_currency),
            (opp.buy_price || 0).toFixed(10),
            (opp.sell_price || 0).toFixed(10),
            (opp.buy_volume || 0).toFixed(8),
            (opp.sell_volume || 0).toFixed(8)
        ];
        return keyParts.join('|');
    }

    addOrUpdateOpportunity(opportunity, addToFront = true) {
        const key = this.createOpportunityKey(opportunity);
        const existing = this.opportunitiesMap.get(key);
        
        if (existing) {
            existing.last_seen = opportunity.last_seen || opportunity.timestamp;
            existing.seen_count = (existing.seen_count || 1) + 1;
            return false;
        } else {
            opportunity.frontend_key = key;
            opportunity.seen_count = 1;
            this.opportunitiesMap.set(key, opportunity);
            
            if (addToFront) {
                this.allOpportunitiesData.unshift(opportunity);
            } else {
                this.allOpportunitiesData.push(opportunity);
            }
            
            return true;
        }
    }

    handleNewOpportunities(newOpportunities) {
        if (!Array.isArray(newOpportunities) || newOpportunities.length === 0) {
            return;
        }

        let hasNewOpportunities = false;
        const trulyNewOpportunities = [];

        newOpportunities.forEach(opp => {
            const isNew = this.addOrUpdateOpportunity(opp, true);
            if (isNew) {
                hasNewOpportunities = true;
                trulyNewOpportunities.push(opp);
            }
        });
        
        if (hasNewOpportunities) {
            this.applyOpportunityFilters();
            
            const highProfitOpps = trulyNewOpportunities.filter(opp => opp.profit_percentage > 1.5);
            if (highProfitOpps.length > 0) {
                const bestNew = highProfitOpps.reduce((best, current) => 
                    current.profit_percentage > best.profit_percentage ? current : best
                );
                
                const baseSymbol = bestNew.base_currency || this.extractBaseSymbol(bestNew.symbol);
                const currencyName = bestNew.currency_name || this.currencyNames[baseSymbol] || baseSymbol;
                
                this.showToast(
                    `🚀 New ${currencyName} opportunity: ${bestNew.profit_percentage.toFixed(2)}% profit (${bestNew.buy_exchange} → ${bestNew.sell_exchange})`,
                    'success'
                );
            }
        }
    }

    updateBestOpportunityDisplay(bestOpp) {
        if (!bestOpp) {
            document.getElementById('stat-best-profit').textContent = '-';
            document.getElementById('stat-best-pair').textContent = '-';
            this.bestOpportunity = null;
            return;
        }
        
        document.getElementById('stat-best-profit').textContent = `${bestOpp.profit_percentage.toFixed(2)}%`;
        
        const baseSymbol = bestOpp.base_currency || this.extractBaseSymbol(bestOpp.symbol);
        const currencyName = bestOpp.currency_name || this.currencyNames[baseSymbol] || baseSymbol;
        
        document.getElementById('stat-best-pair').textContent = 
            `${currencyName} (${bestOpp.buy_exchange} → ${bestOpp.sell_exchange})`;
        
        if (!this.bestOpportunity || bestOpp.profit_percentage > this.bestOpportunity.profit_percentage + 0.01) {
            const profitElement = document.getElementById('stat-best-profit');
            profitElement.classList.add('animate-pulse');
            setTimeout(() => {
                profitElement.classList.remove('animate-pulse');
            }, 2000);
        }
        
        this.bestOpportunity = bestOpp;
    }

    updateConnectionStatus(connected) {
        const indicator = document.getElementById('status-indicator');
        const text = document.getElementById('status-text');
        
        if (connected) {
            indicator.className = 'w-3 h-3 rounded-full bg-green-500 mr-2';
            text.textContent = 'Connected';
        } else {
            indicator.className = 'w-3 h-3 rounded-full bg-red-500 mr-2';
            text.textContent = 'Disconnected';
        }
    }

    updatePricesTable(prices) {
        const tbody = document.getElementById('prices-table-body');
        
        if (!prices || prices.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center py-8 text-gray-500">
                        <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
                        <div>No price data available</div>
                    </td>
                </tr>
            `;
            return;
        }

        const currentTime = Date.now();
        tbody.innerHTML = prices.map((price, index) => {
            const spread = ((price.ask_price - price.bid_price) / price.bid_price * 100).toFixed(2);
            const timeAgo = this.getTimeAgo(price.timestamp);
            const key = `${price.exchange}_${price.symbol}`;
            
            // Enhanced display for Ramzinex and other exchanges
            let displaySymbol = price.display_symbol || price.symbol;
            let currencyName = price.currency_name || this.currencyNames[this.extractBaseSymbol(price.symbol)] || this.extractBaseSymbol(price.symbol);
            
            // Apply Ramzinex mapping
            if (price.exchange === 'ramzinex' && this.ramzinexMapping[price.symbol]) {
                const mapping = this.ramzinexMapping[price.symbol];
                displaySymbol = mapping.symbol;
                currencyName = mapping.name;
            }
            
            const lastUpdate = this.lastUpdateTimes.get(key) || 0;
            const isRecentlyUpdated = (currentTime - lastUpdate) < 2000;
            const animationClass = isRecentlyUpdated ? 'bg-green-900 bg-opacity-30 transition-all duration-1000' : '';
            
            return `
                <tr class="hover:bg-gray-800 transition-colors ${animationClass}" data-key="${key}">
                    <td class="py-3 px-4 text-gray-500 text-sm">${index + 1}</td>
                    <td class="py-3 px-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500 bg-opacity-20 text-blue-400 border border-blue-500">
                            ${price.exchange}
                        </span>
                    </td>
                    <td class="py-3 px-4 font-medium">${displaySymbol}</td>
                    <td class="py-3 px-4 text-gray-300">${currencyName}</td>
                    <td class="py-3 px-4 text-right text-green-400 font-mono">${price.bid_price.toFixed(4)}</td>
                    <td class="py-3 px-4 text-right text-red-400 font-mono">${price.ask_price.toFixed(4)}</td>
                    <td class="py-3 px-4 text-right ${parseFloat(spread) > 1 ? 'text-yellow-400' : 'text-gray-300'} font-mono">${spread}%</td>
                    <td class="py-3 px-4 text-right text-blue-400 font-mono">${price.bid_volume.toFixed(2)}</td>
                    <td class="py-3 px-4 text-right text-orange-400 font-mono">${price.ask_volume.toFixed(2)}</td>
                    <td class="py-3 px-4 text-right text-gray-400 text-sm">${timeAgo}</td>
                </tr>
            `;
        }).join('');

        setTimeout(() => {
            const animatedRows = tbody.querySelectorAll('.bg-green-900');
            animatedRows.forEach(row => row.classList.remove('bg-green-900', 'bg-opacity-30'));
        }, 1000);

        document.getElementById('prices-count').textContent = `${this.allPricesData.size} active prices`;
        document.getElementById('prices-last-update').textContent = `Last update: ${new Date().toLocaleTimeString()}`;
        
        // Update stats
        const exchanges = [...new Set(Array.from(this.allPricesData.values()).map(p => p.exchange))];
        document.getElementById('stat-exchanges').textContent = `${exchanges.length} exchanges`;
    }

    updateSinglePrice(priceData) {
        const key = `${priceData.exchange}_${priceData.symbol}`;
        const previousPrice = this.allPricesData.get(key);
        this.allPricesData.set(key, priceData);
        
        if (previousPrice && 
            (previousPrice.bid_price !== priceData.bid_price || 
             previousPrice.ask_price !== priceData.ask_price)) {
            this.lastUpdateTimes.set(key, Date.now());
        }
        
        if (!document.getElementById('content-prices').classList.contains('hidden')) {
            this.applyPriceFilters();
        }
    }

    updateOpportunitiesTable() {
        const tbody = document.getElementById('opportunities-table-body');
        
        if (!this.opportunitiesData || this.opportunitiesData.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="text-center py-8 text-gray-500">
                        <i class="fas fa-search text-2xl mb-2"></i>
                        <div>No opportunities found</div>
                    </td>
                </tr>
            `;
            this.updatePaginationControls(0);
            return;
        }

        const totalPages = Math.ceil(this.opportunitiesData.length / this.itemsPerPage);
        const startIndex = (this.currentPage - 1) * this.itemsPerPage;
        const endIndex = startIndex + this.itemsPerPage;
        const paginatedData = this.opportunitiesData.slice(startIndex, endIndex);

        tbody.innerHTML = paginatedData.map((opp, index) => {
            const globalIndex = startIndex + index + 1;
            const profitClass = opp.profit_percentage > 2 ? 'text-green-400 animate-pulse' : 
                              opp.profit_percentage > 1 ? 'text-green-400' : 'text-yellow-400';
            const timeAgo = this.getTimeAgo(opp.last_seen || opp.timestamp);
            
            // Apply Ramzinex mapping for symbol display
            let displaySymbol = opp.symbol || opp.base_currency + '/' + opp.quote_currency;
            if (this.ramzinexMapping[opp.symbol]) {
                displaySymbol = this.ramzinexMapping[opp.symbol].symbol;
            }
            
            return `
                <tr class="hover:bg-gray-800 transition-colors">
                    <td class="py-3 px-4 text-gray-500 text-sm">${globalIndex}</td>
                    <td class="py-3 px-4 font-medium">${displaySymbol}</td>
                    <td class="py-3 px-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500 bg-opacity-20 text-green-400 border border-green-500">
                            ${opp.buy_exchange}
                        </span>
                    </td>
                    <td class="py-3 px-4">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500 bg-opacity-20 text-red-400 border border-red-500">
                            ${opp.sell_exchange}
                        </span>
                    </td>
                    <td class="py-3 px-4 text-right text-green-400 font-mono">${opp.buy_price.toFixed(4)}</td>
                    <td class="py-3 px-4 text-right text-blue-400 font-mono">${(opp.buy_volume || 0).toFixed(2)}</td>
                    <td class="py-3 px-4 text-right text-red-400 font-mono">${opp.sell_price.toFixed(4)}</td>
                    <td class="py-3 px-4 text-right text-orange-400 font-mono">${(opp.sell_volume || 0).toFixed(2)}</td>
                    <td class="py-3 px-4 text-right font-bold ${profitClass} font-mono">
                        ${opp.profit_percentage.toFixed(2)}%
                    </td>
                    <td class="py-3 px-4 text-right text-purple-400 font-mono">${(opp.trade_volume || 0).toFixed(2)}</td>
                    <td class="py-3 px-4 text-right text-gray-400 text-sm">${timeAgo}</td>
                </tr>
            `;
        }).join('');

        document.getElementById('opportunities-count').textContent = `${this.allOpportunitiesData.length} opportunities`;
        document.getElementById('opportunities-last-update').textContent = `Last update: ${new Date().toLocaleTimeString()}`;
        this.updatePaginationControls(this.opportunitiesData.length);
        
        // Update stats
        document.getElementById('stat-opportunities-shown').textContent = `${this.opportunitiesData.length} shown`;
    }

    updatePaginationControls(totalItems) {
        const validTotalItems = Math.max(0, totalItems || 0);
        const totalPages = Math.max(1, Math.ceil(validTotalItems / this.itemsPerPage));
        
        if (this.currentPage > totalPages) {
            this.currentPage = totalPages;
        }
        if (this.currentPage < 1) {
            this.currentPage = 1;
        }
        
        document.getElementById('page-info').textContent = `Page ${this.currentPage} of ${totalPages}`;
        
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        if (prevBtn && nextBtn) {
            prevBtn.disabled = this.currentPage <= 1;
            nextBtn.disabled = this.currentPage >= totalPages || validTotalItems === 0;
            
            prevBtn.classList.toggle('opacity-50', prevBtn.disabled);
            prevBtn.classList.toggle('cursor-not-allowed', prevBtn.disabled);
            nextBtn.classList.toggle('opacity-50', nextBtn.disabled);
            nextBtn.classList.toggle('cursor-not-allowed', nextBtn.disabled);
        }
    }

    updateSystemStats(stats) {
        // Don't update stat-opportunities-shown here - it's managed by applyOpportunityFilters
        document.getElementById('stat-prices').textContent = stats.prices_count || 0;
        document.getElementById('stat-memory').textContent = stats.redis_memory || 'N/A';
        document.getElementById('stat-health').textContent = `${stats.redis_clients || 0} clients`;
        
        this.totalOpportunitiesCount = stats.opportunities_count || 0;
        
        // Call monitoring stats update
        this.updateMonitoringStats(stats);
    }

    updateOpportunitiesStats(count) {
        // Update the stats box with actual filtered opportunities count
        document.getElementById('stat-opportunities-shown').textContent = count;
    }

    updateMonitoringStats(stats) {
        // Update monitoring tab
        document.getElementById('redis-memory').textContent = stats.redis_memory || 'N/A';
        document.getElementById('redis-clients').textContent = stats.redis_clients || 0;
        document.getElementById('redis-ops').textContent = stats.redis_ops_per_sec || 0;
        document.getElementById('redis-hit-rate').textContent = stats.redis_hit_rate || 'N/A';
        document.getElementById('redis-uptime').textContent = this.formatUptime(stats.uptime || 0);
        
        // Update additional stats
        document.getElementById('stat-redis-ops').textContent = `${stats.redis_ops_per_sec || 0} ops/sec`;
        document.getElementById('stat-uptime').textContent = this.formatUptime(stats.uptime || 0);
        
        // Calculate market summary
        this.updateMarketSummary();
        
        document.getElementById('monitoring-last-update').textContent = `Last update: ${new Date().toLocaleTimeString()}`;
    }

    updateMarketSummary() {
        const prices = Array.from(this.allPricesData.values());
        const symbols = [...new Set(prices.map(p => this.extractBaseSymbol(p.symbol)))];
        
        let totalSpread = 0;
        let spreadCount = 0;
        let totalVolume = 0;
        
        prices.forEach(price => {
            const spread = ((price.ask_price - price.bid_price) / price.bid_price) * 100;
            totalSpread += spread;
            spreadCount++;
            totalVolume += (price.bid_volume + price.ask_volume);
        });
        
        const avgSpread = spreadCount > 0 ? (totalSpread / spreadCount).toFixed(2) : 0;
        const bestProfitToday = this.bestOpportunity ? this.bestOpportunity.profit_percentage.toFixed(2) : 0;
        
        document.getElementById('active-symbols').textContent = symbols.length;
        document.getElementById('avg-spread').textContent = `${avgSpread}%`;
        document.getElementById('best-profit-today').textContent = `${bestProfitToday}%`;
        document.getElementById('total-volume').textContent = totalVolume.toFixed(0);
    }

    showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        
        const bgColor = type === 'success' ? 'bg-green-600' : 
                       type === 'error' ? 'bg-red-600' : 'bg-blue-600';
        
        const icon = type === 'success' ? 'check-circle' : 
                   type === 'error' ? 'exclamation-circle' : 'info-circle';
        
        toast.className = `${bgColor} text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3 max-w-md transform translate-x-full transition-transform duration-300 ease-out`;
        toast.innerHTML = `
            <i class="fas fa-${icon} flex-shrink-0"></i>
            <span class="flex-1">${message}</span>
            <button class="text-white hover:text-gray-200 flex-shrink-0 ml-2">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
            toast.classList.add('translate-x-0');
        }, 10);
        
        // Auto remove
        setTimeout(() => {
            this.removeToast(toast);
        }, duration);
        
        // Manual close
        toast.querySelector('button').addEventListener('click', () => {
            this.removeToast(toast);
        });
    }

    removeToast(toast) {
        toast.classList.add('translate-x-full');
        toast.classList.remove('translate-x-0');
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    setupPagination() {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const itemsSelect = document.getElementById('items-per-page');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.updateOpportunitiesTable();
                }
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                const totalPages = Math.ceil(this.opportunitiesData.length / this.itemsPerPage);
                if (this.currentPage < totalPages) {
                    this.currentPage++;
                    this.updateOpportunitiesTable();
                }
            });
        }
        
        if (itemsSelect) {
            itemsSelect.addEventListener('change', (e) => {
                this.itemsPerPage = parseInt(e.target.value);
                this.currentPage = 1;
                this.updateOpportunitiesTable();
            });
        }
    }

    async loadInitialData() {
        try {
            const headers = {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json',
            };
            
            const [oppsResponse, pricesResponse] = await Promise.all([
                fetch('/api/opportunities/', { method: 'GET', headers: headers, credentials: 'same-origin' }),
                fetch('/api/prices/', { method: 'GET', headers: headers, credentials: 'same-origin' })
            ]);
            
            if (oppsResponse.ok) {
                const oppsData = await oppsResponse.json();
                if (oppsData.success) {
                    if (oppsData.currency_names) {
                        this.currencyNames = { ...this.currencyNames, ...oppsData.currency_names };
                    }
                    
                    this.allOpportunitiesData = [];
                    this.opportunitiesMap.clear();
                    
                    if (oppsData.data && Array.isArray(oppsData.data)) {
                        oppsData.data.forEach(opp => this.addOrUpdateOpportunity(opp, false));
                    }
                    
                    this.applyOpportunityFilters();
                    
                    if (oppsData.best_opportunity) {
                        this.updateBestOpportunityDisplay(oppsData.best_opportunity);
                    }
                    
                    this.totalOpportunitiesCount = oppsData.total_count || 0;
                }
            }
            
            if (pricesResponse.ok) {
                const pricesData = await pricesResponse.json();
                if (pricesData.success) {
                    if (pricesData.currency_names) {
                        this.currencyNames = { ...this.currencyNames, ...pricesData.currency_names };
                    }
                    this.updateAllPricesData(pricesData.data);
                }
            }
            
            await this.loadSystemStats();
            
        } catch (error) {
            this.showToast('Failed to load initial data', 'error');
            throw error;
        }
    }

    async loadSystemStats() {
        try {
            const headers = {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json',
            };
            
            const response = await fetch('/api/stats/', {
                method: 'GET',
                headers: headers,
                credentials: 'same-origin'
            });
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.updateSystemStats(data.data);
                    
                    if (data.data.best_opportunity) {
                        this.updateBestOpportunityDisplay(data.data.best_opportunity);
                    }
                }
            }
        } catch (error) {
            // Silently handle stats loading errors
        }
    }

    getTimeAgo(timestamp) {
        const now = Date.now() / 1000;
        const diff = now - timestamp;
        
        if (diff < 60) return `${Math.floor(diff)}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) return `${days}d ${hours}h`;
        if (hours > 0) return `${hours}h ${mins}m`;
        return `${mins}m`;
    }

    extractBaseSymbol(symbolFormat) {
        try {
            const symbolUpper = symbolFormat.toUpperCase();
            
            if (symbolUpper.includes('/')) {
                return symbolUpper.split('/')[0];
            }
            if (symbolUpper.includes('_')) {
                return symbolUpper.split('_')[0];
            }
            if (symbolUpper.endsWith('USDT')) {
                return symbolUpper.slice(0, -4);
            }
            if (symbolUpper.endsWith('TMN')) {
                return symbolUpper.slice(0, -3);
            }
                
            return symbolUpper;
        } catch {
            return symbolFormat;
        }
    }
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    new ArbitrageDashboard();
}); 