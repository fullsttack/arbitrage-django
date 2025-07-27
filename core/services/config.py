# 🚀 Exchange Services Configuration
# Fast, Simple, No Hardcoding

EXCHANGE_CONFIGS = {
    'ramzinex': {
        'url': 'wss://websocket.ramzinex.com/websocket',
        'ping_interval': 25,  # Server pings every 25s
        'timeout': 30,
        'connect_msg': {'connect': {'name': 'js'}, 'id': 1},
        'subscribe_prefix': 'orderbook:',
        'ping_format': 'empty_json',  # {}
        'pong_format': 'empty_json'   # {}
    },
    
    'wallex': {
        'url': 'wss://api.wallex.ir/ws',
        'ping_interval': 20,  # Server pings every 20s  
        'timeout': 25,
        'max_pongs': 100,     # Max 100 pongs
        'max_connection_time': 1800,  # 30 minutes
        'subscribe_format': ["subscribe", {"channel": "{symbol}@{type}"}],
        'ping_format': 'json_ping',   # {"ping": "id"}
        'pong_format': 'json_pong'    # {"pong": "id"}
    },
    
    'lbank': {
        'url': 'wss://www.lbkex.net/ws/V2/',
        'ping_interval': 60,  # Flexible ping timing
        'timeout': 120,       # 2 minute timeout
        'subscribe_format': {
            "action": "subscribe",
            "subscribe": "depth", 
            "pair": "{symbol}",
            "depth": "100"
        },
        'ping_format': 'json_action',  # {"action":"ping", "ping":"id"}
        'pong_format': 'json_action'   # {"action":"pong", "pong":"id"}
    }
}

# 🚀 Performance Settings
PERFORMANCE_CONFIG = {
    'broadcast_throttle': 2,      # Seconds between broadcasts per symbol
    'health_check_interval': 10,  # Health check every 10s
    'max_retries': 3,             # Connection retries
    'retry_delay_base': 2,        # Exponential backoff base
}

# Ramzinex Pair ID Mapping (based on actual database pairs)
RAMZINEX_PAIR_MAPPING = {
    # Active pairs from database
    '432': {'symbol': 'DOGEUSDT', 'base': 'DOGE', 'quote': 'USDT', 'name': 'Dogecoin'},
    '13': {'symbol': 'ETHUSDT', 'base': 'ETH', 'quote': 'USDT', 'name': 'Ethereum'},
    '509': {'symbol': 'NOTUSDT', 'base': 'NOT', 'quote': 'USDT', 'name': 'Notcoin'},
    '643': {'symbol': 'XRPUSDT', 'base': 'XRP', 'quote': 'USDT', 'name': 'Ripple'},
    
    # Common TMN pairs (for future use)
    '2': {'symbol': 'BTCTMN', 'base': 'BTC', 'quote': 'TMN', 'name': 'Bitcoin'},
    '11': {'symbol': 'USDTTMN', 'base': 'USDT', 'quote': 'TMN', 'name': 'Tether'},
    '46': {'symbol': 'ETHTMN', 'base': 'ETH', 'quote': 'TMN', 'name': 'Ethereum'},
    '10': {'symbol': 'LTCTMN', 'base': 'LTC', 'quote': 'TMN', 'name': 'Litecoin'},
    '101': {'symbol': 'ADATMN', 'base': 'ADA', 'quote': 'TMN', 'name': 'Cardano'},
}

def get_ramzinex_pair_info(pair_id: str) -> dict:
    """🪙 Get Ramzinex pair information by ID"""
    return RAMZINEX_PAIR_MAPPING.get(str(pair_id), None)

def get_ramzinex_display_symbol(pair_id: str) -> str:
    """📊 Get display symbol for Ramzinex pair (for frontend display)"""
    pair_info = get_ramzinex_pair_info(pair_id)
    return f"{pair_info['base']}/{pair_info['quote']}"

def get_ramzinex_arbitrage_symbol(pair_id: str) -> str:
    """📊 Get arbitrage symbol for Ramzinex pair (for Redis storage and matching)"""
    pair_info = get_ramzinex_pair_info(pair_id)
    return f"{pair_info['base']}{pair_info['quote']}"

def get_ramzinex_currency_name(pair_id: str) -> str:
    """💰 Get currency name for Ramzinex pair"""
    pair_info = get_ramzinex_pair_info(pair_id)
    return pair_info['name']

def get_config(exchange_name: str) -> dict:
    """🔧 Get configuration for exchange"""
    return EXCHANGE_CONFIGS.get(exchange_name, {}) 