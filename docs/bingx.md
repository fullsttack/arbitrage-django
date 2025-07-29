Introduction
Connection limitations
A websocket is limited to a maximum of 200 topics, and 80403 error codes will be returned.

An IP limit is up to 60 websockets, beyond which the link will fail.

Access
the base URL of Live Websocket Market Data ：wss://open-api-swap.bingx.com/swap-market

the base URL of VST Websocket Market Data ：wss://vst-open-api-ws.bingx.com/swap-market

Data Compression
All response data from Websocket server are compressed into GZIP format. Clients have to decompress them for further use.

Heartbeats
Once the Websocket Client and Websocket Server get connected, the server will send a heartbeat- Ping message every 5 seconds (the frequency might change).

When the Websocket Client receives this heartbeat message, it should return Pong message.

Subscriptions
After successfully establishing a connection with the Websocket server, the Websocket client sends the following request to subscribe to a specific topic:

{ "id": "id1", "reqType": "sub", "dataType": "data to sub" }

After a successful subscription, the Websocket client will receive a confirmation message:

{ "id": "id1", "code": 0, "msg": "" }

After that, once the subscribed data is updated, the Websocket client will receive the update message pushed by the server.

Unsubscribe
The format of unsubscription is as follows:

{ "id": "id1", "reqType": "unsub", "dataType": "data to unsub"}

Confirmation of Unsubscription:

{ "id": "id1", "code": 0, "msg": "" }



Websocket Market Data
Subscribe Market Depth Data
Push limited order book depth information.

Subscription Type

The dataType is <symbol>@depth<level>@<interval>, for example, BTC-USDT@depth20@200ms, SOL-USDT@depth100@500ms.

The push interval for BTC-USDT and ETH-USDT is 200ms, and for other contracts it is 500ms.

Subscription Parameters

 
RequestResponselevelinterval
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD.Depth level, such as 5，10，20，50，100.Interval, e.g., 200ms, 500ms
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"e745cd6d-d0f6-4a70-8d5a-043e4c741b40","reqType": "sub","dataType":"BTC-USDT@depth5@500ms"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Subscribe the Latest Trade Detail
Real time push.

Subscribe to the trade detail data of a trading pair

Subscription Type

The dataType is <symbol>@trade E.g. BTC-USDT@trade ETH-USDT@trade

Subscription Parameters

 
RequestResponse
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"e745cd6d-d0f6-4a70-8d5a-043e4c741b40","reqType": "sub","dataType":"BTC-USDT@trade"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Subscribe K-Line Data
Subscribe to market k-line data of one trading pair

Subscription Type

The dataType is <symbol>@kline_<interval> E.g. BTC-USDT@kline_1m

Subscription Example

{"id":"e745cd6d-d0f6-4a70-8d5a-043e4c741b40","reqType": "sub","dataType":"BTC-USDT@kline_1m"}

For more about return error codes, please see the error code description on the homepage.

Subscription Parameters

 
RequestResponseinterval
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD.The type of K-Line ( minutes, hours, weeks etc.)
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"e745cd6d-d0f6-4a70-8d5a-043e4c741b40","reqType": "sub","dataType":"BTC-USDT@kline_1m"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Subscribe to 24-hour price changes
Push every 1 second.

Push 24-hour price changes.

Subscription Type

dataType is <symbol>@ticker, such as BTC-USDT@ticker.

Subscription Parameters

 
RequestResponse
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"24dd0e35-56a4-4f7a-af8a-394c7060909c","reqType": "sub","dataType":"BTC-USDT@ticker"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Subscribe to latest price changes
Real time push.

Push latest price changes.

Subscription Type

dataType is <symbol>@lastPrice, such as BTC-USDT@lastPrice.

Subscription Parameters

 
RequestResponse
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"24dd0e35-56a4-4f7a-af8a-394c7060909c","reqType": "sub","dataType":"BTC-USDT@lastPrice"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Subscribe to latest mark price changes
Real time push.

Push latest mark price changes.

Subscription Type

dataType is <symbol>@markPrice, such as BTC-USDT@markPrice.

Subscription Parameters

 
RequestResponse
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"24dd0e35-56a4-4f7a-af8a-394c7060909c","reqType": "sub","dataType":"BTC-USDT@markPrice"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Subscribe to the Book Ticker Streams
Push every 200 ms.

Push the Book Ticker Streams.

Subscription Type

dataType is <symbol>@bookTicker, such as BTC-USDT@bookTicker.

Subscription Parameters

 
RequestResponse
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"24dd0e35-56a4-4f7a-af8a-394c7060909c","reqType": "sub","dataType":"BTC-USDT@bookTicker"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)  #this is the message you need 
        if utf8_data == "Ping": # this is very important , if you receive 'Ping' you need to send 'Pong' 
           ws.send("Pong")

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print('The connection is closed!')

    def start(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            # on_data=self.on_data,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


if __name__ == "__main__":
    test = Test()
    test.start()
Incremental Depth Information
Push Frequency Description

The push frequency for BTC-USDT and ETH-USDT is 200ms, while for other trading pairs it is 800ms.

How the client should maintain incremental depth locally

1. After successfully subscribing, a full depth with an action field value of 'all' will be returned, along with a lastUpdateId used to handle the continuity of subsequent incremental depth. After receiving the full depth, the WebSocket should cache the full depth data in memory.

2. Subsequent depth changes will return incremental depth, with the action field set to 'update'. The value of the Nth incremental depth's lastUpdateId should be the N-1th depth's lastUpdateId + 1.

3. In rare cases where lastUpdateId is not continuous, you can choose to reconnect, or cache the last three incremental depths and try to merge the data by finding continuous lastUpdateId from the cache (because due to multithreading or network routing issues, data order may not be strongly guaranteed).

4. Then, iterate over the received incremental depth and compare it with the current depth one by one. It's recommended to consider thread-safe design and coding practices (as the push frequency may increase later). The data structure could be a sorted map, such as TreeMap:

(1) If the price level does not exist in the current depth, it means a new price level should be added. (Add)

(2) If the quantity corresponding to the price is 0, the price level should be removed from the current depth. (Delete)

(3) If the quantity corresponding to the price is different from the current value, replace it with the quantity returned by the incremental depth. (Update)

(4) After traversing, you will obtain the latest depth, update the depth cache, and remember to update the lastUpdateId.

Subscription Type

dataType is <symbol>@incrDepth, for example, BTC-USDT@incrDepth

Subscription Example

{"id":"975f7385-7f28-4ef1-93af-df01cb9ebb53","reqType": "sub","dataType":"BTC-USDT@incrDepth"}

Subscription Parameters

 
RequestResponse
id
string
yes
Subscription ID
reqType
string
yes
Request type: Subscribe - sub; Unsubscribe - unsub
dataType
string
yes
There must be a hyphen/ "-" in the trading pair symbol. eg: BTC-USD
PythonNodeJSGolangJavaC#php

import json
import websocket
import gzip
import io
URL="wss://open-api-swap.bingx.com/swap-market" 
CHANNEL= {"id":"e745cd6d-d0f6-4a70-8d5a-043e4c741b40","reqType": "sub","dataType":"BTC-USDT@incrDepth"}
class Test(object):

    def __init__(self):
        self.url = URL 
        self.ws = None

    def on_open(self, ws):
        print('WebSocket connected')
        subStr = json.dumps(CHANNEL)
        ws.send(subStr)
        print("Subscribed to :",subStr)

    def on_data(self, ws, string, type, continue_flag):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(string), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')
        print(utf8_data)

    def on_message(self, ws, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()
        utf8_data = decompressed_data.decode('utf-8')