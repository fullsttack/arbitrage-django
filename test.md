8, Prices: 9, Redis Memory: 2.76M
arbitrage-web       | WARNING 2025-07-25 21:36:53,669 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | 192.168.16.1:60636 - - [25/Jul/2025:21:36:59] "GET /api/stats/" 200 751
arbitrage-web       | 192.168.16.1:39576 - - [25/Jul/2025:21:37:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:37:34,568 LBank: Server ping received, immediately responded with pong: 1753479454474
arbitrage-web       | INFO 2025-07-25 21:37:53,301 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.80M
arbitrage-web       | WARNING 2025-07-25 21:37:53,583 Wallex: No data for 119.9s - reconnecting proactively
arbitrage-web       | ERROR 2025-07-25 21:37:53,583 wallex connection marked as dead: Proactive reconnect - no data
arbitrage-web       | WARNING 2025-07-25 21:37:53,669 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | WARNING 2025-07-25 21:37:53,669 Wallex: No data received for 120.0s - possible server throttling
arbitrage-web       | 192.168.16.1:50918 - - [25/Jul/2025:21:37:59] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:38:02,091 wallex: Attempting connection...
arbitrage-web       | INFO 2025-07-25 21:38:02,091 Wallex connection attempt 1/5
arbitrage-web       | INFO 2025-07-25 21:38:02,608 Wallex WebSocket connected successfully (restart #2)
arbitrage-web       | INFO 2025-07-25 21:38:02,608 Wallex: Starting subscription to 3 pairs: ['DOGEUSDT', 'NOTUSDT', 'XRPUSDT']
arbitrage-web       | INFO 2025-07-25 21:38:02,609 Wallex subscribing to DOGEUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 21:38:04,110 Wallex subscribing to NOTUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 21:38:05,611 Wallex subscribing to XRPUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 21:38:06,729 Wallex: Confirmed subscription for XRPUSDT
arbitrage-web       | INFO 2025-07-25 21:38:07,645 Wallex: Confirmed subscription for NOTUSDT
arbitrage-web       | INFO 2025-07-25 21:38:11,111 Wallex: 2/3 subscriptions confirmed
arbitrage-web       | INFO 2025-07-25 21:38:11,111 wallex: Successfully connected and subscribed
arbitrage-web       | INFO 2025-07-25 21:38:12,814 Wallex: Confirmed subscription for DOGEUSDT
arbitrage-web       | 192.168.16.1:38438 - - [25/Jul/2025:21:38:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:38:34,667 LBank: Server ping received, immediately responded with pong: 1753479514397
arbitrage-web       | INFO 2025-07-25 21:38:53,237 Performance Metrics - Active Calculators: 8/8, Total Calculations: 57523, Redis Ops/sec: 1369, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:38:53,303 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.95M
arbitrage-web       | 192.168.16.1:54854 - - [25/Jul/2025:21:38:59] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:52746 - - [25/Jul/2025:21:39:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:39:35,258 LBank: Server ping received, immediately responded with pong: 1753479574486
arbitrage-web       | INFO 2025-07-25 21:39:53,307 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 3.03M
arbitrage-web       | 192.168.16.1:53954 - - [25/Jul/2025:21:39:59] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:44464 - - [25/Jul/2025:21:40:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:40:46,738 LBank: Server ping received, immediately responded with pong: 1753479634397
arbitrage-web       | INFO 2025-07-25 21:40:53,239 Performance Metrics - Active Calculators: 8/8, Total Calculations: 63915, Redis Ops/sec: 1242, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:40:53,311 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.92M
arbitrage-web       | 192.168.16.1:48174 - - [25/Jul/2025:21:40:58] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:40:58,299 ArbitrageConsumer disconnected: 1006
arbitrage-web       | 192.168.16.1:33594 - - [25/Jul/2025:21:41:25] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:33600 - - [25/Jul/2025:21:41:28] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:56760 - - [25/Jul/2025:21:41:35] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:56760 - - [25/Jul/2025:21:41:35] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:41:35,397 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 21:41:35,402 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 21:41:35,402 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 21:41:35,435 ArbitrageConsumer connected
arbitrage-web       | INFO 2025-07-25 21:41:35,733 LBank: Server ping received, immediately responded with pong: 1753479694472
arbitrage-web       | INFO 2025-07-25 21:41:53,315 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.98M
arbitrage-web       | 192.168.16.1:34030 - - [25/Jul/2025:21:41:59] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:60798 - - [25/Jul/2025:21:42:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:42:34,494 LBank: Server ping received, immediately responded with pong: 1753479754400
arbitrage-web       | INFO 2025-07-25 21:42:53,243 Performance Metrics - Active Calculators: 8/8, Total Calculations: 70307, Redis Ops/sec: 1227, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:42:53,322 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.99M
arbitrage-web       | 192.168.16.1:51902 - - [25/Jul/2025:21:42:59] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:48948 - - [25/Jul/2025:21:43:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:43:34,592 LBank: Server ping received, immediately responded with pong: 1753479814498
arbitrage-web       | 192.168.16.1:51656 - - [25/Jul/2025:21:43:49] "GET /" 200 79865
arbitrage-web       | 192.168.16.1:56760 - - [25/Jul/2025:21:43:50] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:43:50,027 ArbitrageConsumer disconnected: 1001
arbitrage-web       | 192.168.16.1:51668 - - [25/Jul/2025:21:43:50] "GET /api/opportunities/" 200 181118
arbitrage-web       | 192.168.16.1:51670 - - [25/Jul/2025:21:43:50] "GET /api/prices/" 200 1857
arbitrage-web       | 192.168.16.1:51674 - - [25/Jul/2025:21:43:50] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:51678 - - [25/Jul/2025:21:43:51] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:51678 - - [25/Jul/2025:21:43:51] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:43:51,485 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 21:43:51,489 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 21:43:51,489 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 21:43:51,523 ArbitrageConsumer connected
arbitrage-web       | INFO 2025-07-25 21:43:53,327 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 3.01M
arbitrage-web       | 192.168.16.1:44254 - - [25/Jul/2025:21:44:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:44:34,497 LBank: Server ping received, immediately responded with pong: 1753479874397
arbitrage-web       | 192.168.16.1:56626 - - [25/Jul/2025:21:44:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:44:53,245 Performance Metrics - Active Calculators: 8/8, Total Calculations: 76699, Redis Ops/sec: 1228, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:44:53,333 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.94M
arbitrage-web       | 192.168.16.1:45256 - - [25/Jul/2025:21:45:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:45:34,877 LBank: Server ping received, immediately responded with pong: 1753479934475
arbitrage-web       | 192.168.16.1:40544 - - [25/Jul/2025:21:45:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:45:53,336 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.94M
arbitrage-web       | 192.168.16.1:45630 - - [25/Jul/2025:21:46:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:46:34,493 LBank: Server ping received, immediately responded with pong: 1753479994398
arbitrage-web       | 192.168.16.1:46082 - - [25/Jul/2025:21:46:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:46:53,246 Performance Metrics - Active Calculators: 8/8, Total Calculations: 83091, Redis Ops/sec: 1156, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:46:53,342 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.97M
arbitrage-web       | 192.168.16.1:34658 - - [25/Jul/2025:21:47:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:47:39,554 LBank: Server ping received, immediately responded with pong: 1753480054481
arbitrage-web       | 192.168.16.1:57770 - - [25/Jul/2025:21:47:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:47:53,344 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.83M
arbitrage-web       | 192.168.16.1:40648 - - [25/Jul/2025:21:48:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:48:34,636 LBank: Server ping received, immediately responded with pong: 1753480114543
arbitrage-web       | 192.168.16.1:54548 - - [25/Jul/2025:21:48:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:48:53,248 Performance Metrics - Active Calculators: 8/8, Total Calculations: 89483, Redis Ops/sec: 1256, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:48:53,352 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.92M
arbitrage-web       | 192.168.16.1:39570 - - [25/Jul/2025:21:49:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:49:34,552 LBank: Server ping received, immediately responded with pong: 1753480174459
arbitrage-web       | 192.168.16.1:40662 - - [25/Jul/2025:21:49:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:49:53,357 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.89M
arbitrage-web       | 192.168.16.1:33362 - - [25/Jul/2025:21:50:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:50:34,491 LBank: Server ping received, immediately responded with pong: 1753480234395
arbitrage-web       | 192.168.16.1:45844 - - [25/Jul/2025:21:50:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:50:53,249 Performance Metrics - Active Calculators: 8/8, Total Calculations: 95875, Redis Ops/sec: 1115, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:50:53,363 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.87M
arbitrage-web       | 192.168.16.1:49472 - - [25/Jul/2025:21:51:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:51:34,595 LBank: Server ping received, immediately responded with pong: 1753480294502
arbitrage-web       | 192.168.16.1:50650 - - [25/Jul/2025:21:51:45] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:50664 - - [25/Jul/2025:21:51:48] "GET /" 200 79865
arbitrage-web       | 192.168.16.1:50668 - - [25/Jul/2025:21:51:49] "GET /api/opportunities/" 200 181118
arbitrage-web       | 192.168.16.1:50678 - - [25/Jul/2025:21:51:49] "GET /api/prices/" 200 1862
arbitrage-web       | 192.168.16.1:50688 - - [25/Jul/2025:21:51:50] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:50704 - - [25/Jul/2025:21:51:50] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:50714 - - [25/Jul/2025:21:51:50] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:50714 - - [25/Jul/2025:21:51:50] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:51:50,894 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 21:51:50,898 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 21:51:50,898 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 21:51:50,931 ArbitrageConsumer connected
arbitrage-web       | INFO 2025-07-25 21:51:53,366 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.96M
arbitrage-web       | 192.168.16.1:50714 - - [25/Jul/2025:21:52:09] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:52:09,807 ArbitrageConsumer disconnected: 1006
arbitrage-web       | 192.168.16.1:58784 - - [25/Jul/2025:21:52:12] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:58784 - - [25/Jul/2025:21:52:12] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:52:12,145 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 21:52:12,150 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 21:52:12,150 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 21:52:12,183 ArbitrageConsumer connected
arbitrage-web       | 192.168.16.1:58784 - - [25/Jul/2025:21:52:17] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 21:52:17,731 ArbitrageConsumer disconnected: 1006
arbitrage-web       | 192.168.16.1:55152 - - [25/Jul/2025:21:52:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:52:34,957 LBank: Server ping received, immediately responded with pong: 1753480354401
arbitrage-web       | 192.168.16.1:40066 - - [25/Jul/2025:21:52:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:52:53,252 Performance Metrics - Active Calculators: 8/8, Total Calculations: 102261, Redis Ops/sec: 1086, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:52:53,377 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.91M
arbitrage-web       | 192.168.16.1:43918 - - [25/Jul/2025:21:53:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:53:34,730 LBank: Server ping received, immediately responded with pong: 1753480414436
arbitrage-web       | 192.168.16.1:43208 - - [25/Jul/2025:21:53:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:53:53,378 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.73M
arbitrage-web       | WARNING 2025-07-25 21:54:05,418 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | 192.168.16.1:41744 - - [25/Jul/2025:21:54:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:54:35,427 LBank: Server ping received, immediately responded with pong: 1753480474457
arbitrage-web       | 192.168.16.1:36980 - - [25/Jul/2025:21:54:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:54:53,255 Performance Metrics - Active Calculators: 8/8, Total Calculations: 108652, Redis Ops/sec: 1340, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:54:53,382 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.66M
arbitrage-web       | WARNING 2025-07-25 21:55:02,619 Wallex: No data for 117.2s - reconnecting proactively
arbitrage-web       | ERROR 2025-07-25 21:55:02,619 wallex connection marked as dead: Proactive reconnect - no data
arbitrage-web       | WARNING 2025-07-25 21:55:05,418 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | WARNING 2025-07-25 21:55:05,419 Wallex: No data received for 120.0s - possible server throttling
arbitrage-web       | INFO 2025-07-25 21:55:11,130 wallex: Attempting connection...
arbitrage-web       | INFO 2025-07-25 21:55:11,131 Wallex connection attempt 1/5
arbitrage-web       | INFO 2025-07-25 21:55:11,651 Wallex WebSocket connected successfully (restart #3)
arbitrage-web       | INFO 2025-07-25 21:55:11,651 Wallex: Starting subscription to 3 pairs: ['DOGEUSDT', 'NOTUSDT', 'XRPUSDT']
arbitrage-web       | INFO 2025-07-25 21:55:11,651 Wallex subscribing to DOGEUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 21:55:12,610 Wallex: Confirmed subscription for DOGEUSDT
arbitrage-web       | INFO 2025-07-25 21:55:13,151 Wallex subscribing to NOTUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 21:55:14,654 Wallex subscribing to XRPUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 21:55:16,556 Wallex: Confirmed subscription for XRPUSDT
arbitrage-web       | INFO 2025-07-25 21:55:17,665 Wallex: Confirmed subscription for NOTUSDT
arbitrage-web       | INFO 2025-07-25 21:55:20,154 Wallex: 3/3 subscriptions confirmed
arbitrage-web       | INFO 2025-07-25 21:55:20,155 wallex: Successfully connected and subscribed
arbitrage-web       | 192.168.16.1:49296 - - [25/Jul/2025:21:55:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:55:34,654 LBank: Server ping received, immediately responded with pong: 1753480534476
arbitrage-web       | 192.168.16.1:51634 - - [25/Jul/2025:21:55:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:55:53,386 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.76M
arbitrage-web       | 192.168.16.1:53656 - - [25/Jul/2025:21:56:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:56:34,694 LBank: Server ping received, immediately responded with pong: 1753480594397
arbitrage-web       | 192.168.16.1:59732 - - [25/Jul/2025:21:56:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:56:53,256 Performance Metrics - Active Calculators: 8/8, Total Calculations: 115043, Redis Ops/sec: 1298, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:56:53,392 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.91M
arbitrage-web       | 192.168.16.1:42578 - - [25/Jul/2025:21:57:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:57:37,262 LBank: Server ping received, immediately responded with pong: 1753480654543
arbitrage-web       | 192.168.16.1:35240 - - [25/Jul/2025:21:57:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:57:53,397 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.84M
arbitrage-web       | 192.168.16.1:58528 - - [25/Jul/2025:21:58:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:58:40,121 LBank: Server ping received, immediately responded with pong: 1753480714420
arbitrage-web       | 192.168.16.1:43252 - - [25/Jul/2025:21:58:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:58:53,257 Performance Metrics - Active Calculators: 8/8, Total Calculations: 121435, Redis Ops/sec: 1155, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 21:58:53,402 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.74M
arbitrage-web       | 192.168.16.1:36984 - - [25/Jul/2025:21:59:20] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:60410 - - [25/Jul/2025:21:59:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 21:59:53,408 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.70M
arbitrage-web       | INFO 2025-07-25 22:00:04,876 LBank: Server ping received, immediately responded with pong: 1753480774400
arbitrage-web       | 192.168.16.1:43880 - - [25/Jul/2025:22:00:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:00:34,525 LBank: Server ping received, immediately responded with pong: 1753480834431
arbitrage-web       | 192.168.16.1:60850 - - [25/Jul/2025:22:00:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:00:53,259 Performance Metrics - Active Calculators: 8/8, Total Calculations: 127829, Redis Ops/sec: 1310, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:00:53,410 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.88M
arbitrage-web       | 192.168.16.1:56820 - - [25/Jul/2025:22:01:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:01:34,504 LBank: Server ping received, immediately responded with pong: 1753480894411
arbitrage-web       | 192.168.16.1:59074 - - [25/Jul/2025:22:01:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:01:53,412 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 3.01M
arbitrage-web       | 192.168.16.1:48960 - - [25/Jul/2025:22:02:20] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:02:34,517 LBank: Server ping received, immediately responded with pong: 1753480954416
arbitrage-web       | 192.168.16.1:34136 - - [25/Jul/2025:22:02:50] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:02:53,260 Performance Metrics - Active Calculators: 8/8, Total Calculations: 134227, Redis Ops/sec: 1156, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:02:53,414 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.95M
arbitrage-web       | 192.168.16.1:56028 - - [25/Jul/2025:22:03:20] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:40514 - - [25/Jul/2025:22:03:28] "GET /" 302 -
arbitrage-web       | 192.168.16.1:40530 - - [25/Jul/2025:22:03:28] "GET /admin/login/?next=%2F" 200 10989
arbitrage-web       | WARNING 2025-07-25 22:03:28,302 Not Found: /js/twint_ch.js
arbitrage-web       | WARNING 2025-07-25 22:03:28,302 Not Found: /js/twint_ch.js
arbitrage-web       | 192.168.16.1:40532 - - [25/Jul/2025:22:03:28] "GET /js/twint_ch.js" 404 179
arbitrage-web       | WARNING 2025-07-25 22:03:28,646 Not Found: /js/lkk_ch.js
arbitrage-web       | WARNING 2025-07-25 22:03:28,646 Not Found: /js/lkk_ch.js
arbitrage-web       | 192.168.16.1:40536 - - [25/Jul/2025:22:03:28] "GET /js/lkk_ch.js" 404 179
arbitrage-web       | INFO 2025-07-25 22:03:35,233 LBank: Server ping received, immediately responded with pong: 1753481014479
arbitrage-web       | INFO 2025-07-25 22:03:53,418 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.98M
arbitrage-web       | INFO 2025-07-25 22:04:35,380 LBank: Server ping received, immediately responded with pong: 1753481074419
arbitrage-web       | 192.168.16.1:41220 - - [25/Jul/2025:22:04:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:04:53,261 Performance Metrics - Active Calculators: 8/8, Total Calculations: 140619, Redis Ops/sec: 1141, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:04:53,421 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.94M
arbitrage-web       | 192.168.16.1:51678 - - [25/Jul/2025:22:05:05] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 22:05:05,075 ArbitrageConsumer disconnected: 1006
arbitrage-web       | INFO 2025-07-25 22:05:34,493 LBank: Server ping received, immediately responded with pong: 1753481134395
arbitrage-web       | 192.168.16.1:37142 - - [25/Jul/2025:22:05:42] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:33196 - - [25/Jul/2025:22:05:51] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:33196 - - [25/Jul/2025:22:05:51] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 22:05:51,748 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 22:05:51,753 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 22:05:51,753 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 22:05:51,789 ArbitrageConsumer connected
arbitrage-web       | INFO 2025-07-25 22:05:53,427 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.99M
arbitrage-web       | INFO 2025-07-25 22:06:34,571 LBank: Server ping received, immediately responded with pong: 1753481194478
arbitrage-web       | 192.168.16.1:34496 - - [25/Jul/2025:22:06:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:06:53,262 Performance Metrics - Active Calculators: 8/8, Total Calculations: 147008, Redis Ops/sec: 1177, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:06:53,429 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 3.05M
arbitrage-web       | INFO 2025-07-25 22:07:37,759 LBank: Server ping received, immediately responded with pong: 1753481254404
arbitrage-web       | 192.168.16.1:45090 - - [25/Jul/2025:22:07:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:07:53,433 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.95M
arbitrage-web       | INFO 2025-07-25 22:08:34,795 LBank: Server ping received, immediately responded with pong: 1753481314455
arbitrage-web       | 192.168.16.1:47988 - - [25/Jul/2025:22:08:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:08:53,264 Performance Metrics - Active Calculators: 8/8, Total Calculations: 153399, Redis Ops/sec: 1148, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:08:53,436 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.81M
arbitrage-web       | 192.168.16.1:49186 - - [25/Jul/2025:22:08:59] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:38208 - - [25/Jul/2025:22:09:09] "GET /" 200 79865
arbitrage-web       | 192.168.16.1:33196 - - [25/Jul/2025:22:09:09] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 22:09:09,516 ArbitrageConsumer disconnected: 1001
arbitrage-web       | 192.168.16.1:38216 - - [25/Jul/2025:22:09:09] "GET /api/opportunities/" 200 181118
arbitrage-web       | 192.168.16.1:38220 - - [25/Jul/2025:22:09:10] "GET /api/prices/" 200 1854
arbitrage-web       | 192.168.16.1:38222 - - [25/Jul/2025:22:09:10] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:38236 - - [25/Jul/2025:22:09:10] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:38236 - - [25/Jul/2025:22:09:10] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 22:09:10,941 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 22:09:10,945 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 22:09:10,946 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 22:09:10,982 ArbitrageConsumer connected
arbitrage-web       | INFO 2025-07-25 22:09:34,506 LBank: Server ping received, immediately responded with pong: 1753481374413
arbitrage-web       | 192.168.16.1:41272 - - [25/Jul/2025:22:09:40] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:09:53,440 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.89M
arbitrage-web       | 192.168.16.1:43716 - - [25/Jul/2025:22:10:10] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:10:34,557 LBank: Server ping received, immediately responded with pong: 1753481434464
arbitrage-web       | 192.168.16.1:42708 - - [25/Jul/2025:22:10:40] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:10:53,267 Performance Metrics - Active Calculators: 8/8, Total Calculations: 159787, Redis Ops/sec: 1145, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:10:53,443 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.73M
arbitrage-web       | 192.168.16.1:40916 - - [25/Jul/2025:22:11:10] "GET /api/stats/" 200 752
arbitrage-web       | WARNING 2025-07-25 22:11:12,325 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | INFO 2025-07-25 22:11:34,488 LBank: Server ping received, immediately responded with pong: 1753481494395
arbitrage-web       | 192.168.16.1:60254 - - [25/Jul/2025:22:11:40] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:11:53,447 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.68M
arbitrage-web       | 192.168.16.1:38484 - - [25/Jul/2025:22:12:11] "GET /api/stats/" 200 752
arbitrage-web       | WARNING 2025-07-25 22:12:11,663 Wallex: No data for 119.3s - reconnecting proactively
arbitrage-web       | ERROR 2025-07-25 22:12:11,663 wallex connection marked as dead: Proactive reconnect - no data
arbitrage-web       | WARNING 2025-07-25 22:12:12,326 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | WARNING 2025-07-25 22:12:12,326 Wallex: No data received for 120.0s - possible server throttling
arbitrage-web       | INFO 2025-07-25 22:12:20,177 wallex: Attempting connection...
arbitrage-web       | INFO 2025-07-25 22:12:20,177 Wallex connection attempt 1/5
arbitrage-web       | INFO 2025-07-25 22:12:20,922 Wallex WebSocket connected successfully (restart #4)
arbitrage-web       | INFO 2025-07-25 22:12:20,922 Wallex: Starting subscription to 3 pairs: ['DOGEUSDT', 'NOTUSDT', 'XRPUSDT']
arbitrage-web       | INFO 2025-07-25 22:12:20,922 Wallex subscribing to DOGEUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 22:12:22,422 Wallex subscribing to NOTUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 22:12:23,923 Wallex subscribing to XRPUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 22:12:26,537 Wallex: Confirmed subscription for XRPUSDT
arbitrage-web       | INFO 2025-07-25 22:12:27,664 Wallex: Confirmed subscription for DOGEUSDT
arbitrage-web       | INFO 2025-07-25 22:12:29,424 Wallex: 2/3 subscriptions confirmed
arbitrage-web       | INFO 2025-07-25 22:12:29,424 wallex: Successfully connected and subscribed
arbitrage-web       | INFO 2025-07-25 22:12:31,538 Wallex: Confirmed subscription for NOTUSDT
arbitrage-web       | INFO 2025-07-25 22:12:34,696 LBank: Server ping received, immediately responded with pong: 1753481554514
arbitrage-web       | 192.168.16.1:49766 - - [25/Jul/2025:22:12:40] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:12:53,269 Performance Metrics - Active Calculators: 8/8, Total Calculations: 166179, Redis Ops/sec: 1226, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:12:53,453 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.75M
arbitrage-web       | 192.168.16.1:48798 - - [25/Jul/2025:22:13:10] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:13:34,682 LBank: Server ping received, immediately responded with pong: 1753481614418
arbitrage-web       | 192.168.16.1:41360 - - [25/Jul/2025:22:13:40] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:13:53,467 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.94M
arbitrage-web       | INFO 2025-07-25 22:14:34,613 LBank: Server ping received, immediately responded with pong: 1753481674517
arbitrage-web       | 192.168.16.1:33696 - - [25/Jul/2025:22:14:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:14:53,271 Performance Metrics - Active Calculators: 8/8, Total Calculations: 172571, Redis Ops/sec: 1157, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:14:53,469 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.90M
arbitrage-web       | INFO 2025-07-25 22:15:34,506 LBank: Server ping received, immediately responded with pong: 1753481734400
arbitrage-web       | 192.168.16.1:42956 - - [25/Jul/2025:22:15:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:15:53,471 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.89M
arbitrage-web       | INFO 2025-07-25 22:16:35,387 LBank: Server ping received, immediately responded with pong: 1753481794605
arbitrage-web       | 192.168.16.1:42606 - - [25/Jul/2025:22:16:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:16:53,273 Performance Metrics - Active Calculators: 8/8, Total Calculations: 178963, Redis Ops/sec: 1257, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:16:53,475 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.94M
arbitrage-web       | INFO 2025-07-25 22:17:34,495 LBank: Server ping received, immediately responded with pong: 1753481854399
arbitrage-web       | 192.168.16.1:37006 - - [25/Jul/2025:22:17:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:17:53,477 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 3.03M
arbitrage-web       | INFO 2025-07-25 22:18:34,679 LBank: Server ping received, immediately responded with pong: 1753481914586
arbitrage-web       | 192.168.16.1:58654 - - [25/Jul/2025:22:18:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:18:53,274 Performance Metrics - Active Calculators: 8/8, Total Calculations: 185355, Redis Ops/sec: 1109, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:18:53,481 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.92M
arbitrage-web       | INFO 2025-07-25 22:19:34,569 LBank: Server ping received, immediately responded with pong: 1753481974409
arbitrage-web       | 192.168.16.1:59530 - - [25/Jul/2025:22:19:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:19:53,482 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.85M
arbitrage-web       | 192.168.16.1:50462 - - [25/Jul/2025:22:20:10] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:50476 - - [25/Jul/2025:22:20:12] "GET /" 200 79865
arbitrage-web       | 192.168.16.1:38236 - - [25/Jul/2025:22:20:12] "WSDISCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 22:20:12,646 ArbitrageConsumer disconnected: 1001
arbitrage-web       | 192.168.16.1:50492 - - [25/Jul/2025:22:20:12] "GET /api/opportunities/" 200 181118
arbitrage-web       | 192.168.16.1:50498 - - [25/Jul/2025:22:20:13] "GET /api/prices/" 200 1864
arbitrage-web       | 192.168.16.1:50502 - - [25/Jul/2025:22:20:13] "GET /api/stats/" 200 752
arbitrage-web       | 192.168.16.1:38800 - - [25/Jul/2025:22:20:13] "WSCONNECTING /ws/arbitrage/" - -
arbitrage-web       | 192.168.16.1:38800 - - [25/Jul/2025:22:20:14] "WSCONNECT /ws/arbitrage/" - -
arbitrage-web       | INFO 2025-07-25 22:20:14,083 Sending 338 initial opportunities
arbitrage-web       | INFO 2025-07-25 22:20:14,086 Got 9 price keys from Redis: ['prices:ramzinex:DOGE/USDT', 'prices:lbank:xrp_usdt', 'prices:ramzinex:XRP/USDT', 'prices:ramzinex:NOT/USDT', 'prices:lbank:not_usdt', 'prices:lbank:doge_usdt', 'prices:wallex:NOTUSDT', 'prices:wallex:XRPUSDT', 'prices:wallex:DOGEUSDT']
arbitrage-web       | INFO 2025-07-25 22:20:14,087 Sending 9 initial prices to WebSocket
arbitrage-web       | INFO 2025-07-25 22:20:14,120 ArbitrageConsumer connected
arbitrage-web       | INFO 2025-07-25 22:20:34,600 LBank: Server ping received, immediately responded with pong: 1753482034507
arbitrage-web       | 192.168.16.1:53518 - - [25/Jul/2025:22:20:43] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:20:53,275 Performance Metrics - Active Calculators: 8/8, Total Calculations: 191747, Redis Ops/sec: 1293, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:20:53,498 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.92M
arbitrage-web       | 192.168.16.1:46658 - - [25/Jul/2025:22:21:13] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:21:34,492 LBank: Server ping received, immediately responded with pong: 1753482094399
arbitrage-web       | 192.168.16.1:37574 - - [25/Jul/2025:22:21:43] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:21:53,504 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.88M
arbitrage-web       | 192.168.16.1:58202 - - [25/Jul/2025:22:22:13] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:22:34,593 LBank: Server ping received, immediately responded with pong: 1753482154500
arbitrage-web       | 192.168.16.1:33318 - - [25/Jul/2025:22:22:43] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:22:53,276 Performance Metrics - Active Calculators: 8/8, Total Calculations: 198136, Redis Ops/sec: 1368, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:22:53,510 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.90M
arbitrage-web       | 192.168.16.1:57684 - - [25/Jul/2025:22:23:13] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:23:34,490 LBank: Server ping received, immediately responded with pong: 1753482214395
arbitrage-web       | INFO 2025-07-25 22:23:53,525 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.86M
arbitrage-web       | INFO 2025-07-25 22:24:34,583 LBank: Server ping received, immediately responded with pong: 1753482274490
arbitrage-web       | 192.168.16.1:51834 - - [25/Jul/2025:22:24:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:24:53,277 Performance Metrics - Active Calculators: 8/8, Total Calculations: 204526, Redis Ops/sec: 1442, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:24:53,529 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.89M
arbitrage-web       | INFO 2025-07-25 22:25:34,495 LBank: Server ping received, immediately responded with pong: 1753482334401
arbitrage-web       | 192.168.16.1:56542 - - [25/Jul/2025:22:25:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:25:53,537 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.95M
arbitrage-web       | INFO 2025-07-25 22:26:34,571 LBank: Server ping received, immediately responded with pong: 1753482394478
arbitrage-web       | 192.168.16.1:46726 - - [25/Jul/2025:22:26:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:26:53,280 Performance Metrics - Active Calculators: 8/8, Total Calculations: 210915, Redis Ops/sec: 1246, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:26:53,539 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.90M
arbitrage-web       | 192.168.16.1:60088 - - [25/Jul/2025:22:27:29] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:27:34,546 LBank: Server ping received, immediately responded with pong: 1753482454450
arbitrage-web       | 192.168.16.1:40838 - - [25/Jul/2025:22:27:43] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:27:53,541 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.68M
arbitrage-web       | 192.168.16.1:48960 - - [25/Jul/2025:22:28:13] "GET /api/stats/" 200 752
arbitrage-web       | WARNING 2025-07-25 22:28:18,613 Wallex: Message timeout (60s) - checking connection health
arbitrage-web       | INFO 2025-07-25 22:28:39,737 LBank: Server ping received, immediately responded with pong: 1753482514686
arbitrage-web       | 192.168.16.1:48766 - - [25/Jul/2025:22:28:43] "GET /api/stats/" 200 752
arbitrage-web       | WARNING 2025-07-25 22:28:50,928 Wallex: No data for 92.3s - reconnecting proactively
arbitrage-web       | ERROR 2025-07-25 22:28:50,928 wallex connection marked as dead: Proactive reconnect - no data
arbitrage-web       | INFO 2025-07-25 22:28:53,284 Performance Metrics - Active Calculators: 8/8, Total Calculations: 217310, Redis Ops/sec: 1114, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:28:53,545 System Status - Connections: 2/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.61M
arbitrage-web       | INFO 2025-07-25 22:28:59,460 wallex: Attempting connection...
arbitrage-web       | INFO 2025-07-25 22:28:59,460 Wallex connection attempt 1/5
arbitrage-web       | WARNING 2025-07-25 22:28:59,574 Wallex WebSocket connection closed: sent 1000 (OK); then received 1000 (OK)
arbitrage-web       | ERROR 2025-07-25 22:28:59,574 wallex connection marked as dead: Connection closed: sent 1000 (OK); then received 1000 (OK)
arbitrage-web       | INFO 2025-07-25 22:28:59,945 Wallex WebSocket connected successfully (restart #5)
arbitrage-web       | INFO 2025-07-25 22:28:59,946 Wallex: Starting subscription to 3 pairs: ['DOGEUSDT', 'NOTUSDT', 'XRPUSDT']
arbitrage-web       | INFO 2025-07-25 22:28:59,946 Wallex subscribing to DOGEUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 22:29:01,445 Wallex subscribing to NOTUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 22:29:02,706 Wallex: Confirmed subscription for NOTUSDT
arbitrage-web       | INFO 2025-07-25 22:29:02,946 Wallex subscribing to XRPUSDT (buy/sell depth)...
arbitrage-web       | INFO 2025-07-25 22:29:05,487 Wallex: Confirmed subscription for XRPUSDT
arbitrage-web       | INFO 2025-07-25 22:29:07,359 Wallex: Confirmed subscription for DOGEUSDT
arbitrage-web       | INFO 2025-07-25 22:29:08,448 Wallex: 3/3 subscriptions confirmed
arbitrage-web       | INFO 2025-07-25 22:29:08,448 wallex: Successfully connected and subscribed
arbitrage-web       | 192.168.16.1:55738 - - [25/Jul/2025:22:29:13] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:29:35,400 LBank: Server ping received, immediately responded with pong: 1753482574446
arbitrage-web       | 192.168.16.1:38496 - - [25/Jul/2025:22:29:43] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:29:53,559 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.83M
arbitrage-web       | 192.168.16.1:53606 - - [25/Jul/2025:22:30:13] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:30:34,654 LBank: Server ping received, immediately responded with pong: 1753482634561
arbitrage-web       | INFO 2025-07-25 22:30:53,287 Performance Metrics - Active Calculators: 8/8, Total Calculations: 223702, Redis Ops/sec: 1109, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:30:53,562 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.92M
arbitrage-web       | INFO 2025-07-25 22:31:34,500 LBank: Server ping received, immediately responded with pong: 1753482694406
arbitrage-web       | 192.168.16.1:55254 - - [25/Jul/2025:22:31:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:31:53,568 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.89M
arbitrage-web       | INFO 2025-07-25 22:32:34,685 LBank: Server ping received, immediately responded with pong: 1753482754593
arbitrage-web       | 192.168.16.1:46894 - - [25/Jul/2025:22:32:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:32:53,288 Performance Metrics - Active Calculators: 8/8, Total Calculations: 230094, Redis Ops/sec: 1156, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:32:53,571 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.88M
arbitrage-web       | INFO 2025-07-25 22:33:34,709 LBank: Server ping received, immediately responded with pong: 1753482814453
arbitrage-web       | 192.168.16.1:59496 - - [25/Jul/2025:22:33:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:33:53,577 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.97M
arbitrage-web       | INFO 2025-07-25 22:34:35,811 LBank: Server ping received, immediately responded with pong: 1753482874477
arbitrage-web       | 192.168.16.1:42860 - - [25/Jul/2025:22:34:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:34:53,289 Performance Metrics - Active Calculators: 8/8, Total Calculations: 236486, Redis Ops/sec: 1323, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:34:53,580 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.87M
arbitrage-web       | INFO 2025-07-25 22:35:34,594 LBank: Server ping received, immediately responded with pong: 1753482934500
arbitrage-web       | 192.168.16.1:34926 - - [25/Jul/2025:22:35:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:35:53,584 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.87M
arbitrage-web       | INFO 2025-07-25 22:36:37,142 LBank: Server ping received, immediately responded with pong: 1753482994557
arbitrage-web       | 192.168.16.1:37168 - - [25/Jul/2025:22:36:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:36:53,290 Performance Metrics - Active Calculators: 8/8, Total Calculations: 242878, Redis Ops/sec: 1082, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:36:53,587 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.84M
arbitrage-web       | INFO 2025-07-25 22:37:34,512 LBank: Server ping received, immediately responded with pong: 1753483054418
arbitrage-web       | 192.168.16.1:43296 - - [25/Jul/2025:22:37:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:37:53,594 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.85M
arbitrage-web       | INFO 2025-07-25 22:38:34,602 LBank: Server ping received, immediately responded with pong: 1753483114510
arbitrage-web       | 192.168.16.1:52598 - - [25/Jul/2025:22:38:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:38:53,292 Performance Metrics - Active Calculators: 8/8, Total Calculations: 249270, Redis Ops/sec: 1327, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:38:53,600 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.84M
arbitrage-web       | INFO 2025-07-25 22:39:34,641 LBank: Server ping received, immediately responded with pong: 1753483174534
arbitrage-web       | 192.168.16.1:33990 - - [25/Jul/2025:22:39:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:39:53,604 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.86M
arbitrage-web       | INFO 2025-07-25 22:40:36,596 LBank: Server ping received, immediately responded with pong: 1753483234418
arbitrage-web       | 192.168.16.1:43048 - - [25/Jul/2025:22:40:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:40:53,295 Performance Metrics - Active Calculators: 8/8, Total Calculations: 255662, Redis Ops/sec: 1020, Redis Hit Rate: 99.8%
arbitrage-web       | INFO 2025-07-25 22:40:53,606 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 338, Prices: 9, Redis Memory: 2.73M
arbitrage-web       | 192.168.16.1:33214 - - [25/Jul/2025:22:41:42] "GET /api/stats/" 200 752
arbitrage-web       | INFO 2025-07-25 22:41:53,618 System Status - Connections: 3/3, Tasks: 14/14, Calculators: 8/8, Opportunities: 3