اطلاعات بازار (عمومی)
این مجموعه برای دسترسی به اطلاعات عمومی بازار می‌باشد و برای درخواست های این مجموعه نیاز به احراز هویت و استفاده از کلید خصوصی نیست.

لیست سفارش های باز ( اردربوک) یک بازار مشخص
برای دریافت لیست سفارشات خرید و فروش موجود در بازار از این نوع درخواست استفاده نمایید:

path Parameters
pairId	
integer
Example: 11
شناسه بازار می‌باشد و مقدار آن عدد است

Responses
200 موفق

get
/orderbooks/{pair_id}/buys_sells
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/11/buys_sells' --header 'Content-Type: application/json'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"data": {
"buys": [],
"sells": []
},
"status": 0
}
لیست سفارش های باز ( اردربوک) بازارها
برای دریافت لیست سفارشات خرید و فروش موجود در بازار از این نوع درخواست استفاده نمایید:

Responses
200 موفق

get
/orderbooks/buys_sells
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/buys_sells' --header 'Content-Type: application/json'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"10": {
"buys": [],
"sells": []
},
"101": {
"buys": [],
"sells": []
}
}


وب‌سوکت
رمزینکس برای ارائه اطلاعات لحظه‌ای از وب‌سوکت استفاده می‌کند. این سرویس با استفاده از سرور Centrifugo پیاده‌سازی شده و برای زبان‌های مختلف، SDKهای رسمی متعددی ارائه شده است که فرآیند اتصال را ساده‌تر می‌کنند.
لیست SDKهای قابل استفاده برای اتصال به وب‌سوکت رمزینکس :
ماژول SDK
توضیح
centrifuge-js
برای مرورگر، NodeJS

centrifuge-python
برای استفاده در پایتون

centrifuge-java
برای استفاده در جاوا

centrifuge-golang
برای استفاده در گولنگ

اتصال به وب‌سوکت
برای اتصال به وب‌سوکت رمزینکس از آدرس زیر استفاده کنید:
آدرس وب سوکت:

wss://websocket.ramzinex.com/websocket
پس از اتصال به وب سوکت رمزینکس، سرور Centrifuge به صورت دوره‌ای پیام‌های ping ارسال می‌کند. در صورت استفاده از SDKهای رسمی، این ابزارها خودکار به پیام‌های ping پاسخ pong می‌دهند. توجه داشته باشید که اگر در زمان ۲۵ ثانیه به پیام‌های ping پاسخ داده نشود، سرور (به دلیل مدیریت بهینه منابع) اتصال را قطع خواهد کرد. در نتیجه اگر از SDK رسمی استفاده نمی‌کنید، از ارسال پیام PONG قبل از زمان ذکر شده اطمینان حاصل فرمایید.
نکته: مکانیزم PingPong به این شکل است که پیام خالی با محتوای {} به کلاینت ارسال شده و پیام Pong نیز با همان محتوای {} است.

نمونه اتصال با Postman
به بخش WebSocket در Postman بروید.
آدرس wss://websocket.ramzinex.com/websocket را وارد کنید.
روی Connect کلیک کنید.
پیام زیر را برای اتصال ارسال کنید:
{
'connect': {'name': 'js'},
'id': 1
}
برای دریافت آخرین تراکنش‌ها و لیست سفارشات، پیام‌های زیر را ارسال کنید:
{'subscribe':{'channel':'last-trades:11', 'recover':true, 'delta': 'fossil'}, 'id':2}

{'subscribe':{'channel':'orderbook:11', 'recover':true, 'delta': 'fossil'}, 'id':3}
نمونه اتصال با NodeJs
npm install centrifuge
import { Centrifuge } from 'centrifuge';
const client = new Centrifuge('wss://websocket.ramzinex.com/websocket', {});
client.on('connected', (ctx) => { console.log('connected', ctx);
});
client.connect();
اتصال به چند کانال با استفاده از یک کلاینت:
const channels = ['public:orderbook:46', 'orderbook:2', 'orderbook:11']
const subs = channels.map(channel => {
const sub = client.newSubscription(channel, { delta: 'fossil' })
sub.subscribe()
sub.on('publication', (ctx) => {
console.log(channel, ctx.data);
})
return sub
});
استریم لیست سفارش‌ها (اردربوک)
کانال‌ با پیشوند زیر شامل اطلاعات اردربوک است و با هر تغییری در اردربوک، پیامی ارسال می‌کند:

الگوی کانال‌های اردربوک: orderbook:{pair_id}

مثال: برای دریافت تغییرات اردربوک بیت‌کوین به ریال، کافیست به کانال orderbook:2 متصل شوید.

توجه داشته باشید که استفاده از فلگ { delta: 'fossil' } در تابع newSubscription اختیاری است. با استفاده از این فلگ، اطلاعات اردربوک به صورت diff به کلاینت ارسال می‌شود.
در صورتی که از SDK استفاده نمی‌کنید پیام زیر را ارسال نمایید:
{
'id': 2,
'subscribe': { 'channel': 'orderbook:2' }
}
پارامترهای پاسخ
پارامترهای پاسخ وب‌سوکت همانند پاسخ اندپوینت buys_sells/ شامل دو آرایه sells و buys بوده که در هر یک قیمت و مقدار سفارش‌های بازار وجود دارد. سفارش‌های خرید در buys و سفارش‌های فروش در sells بازگردانده می‌شوند..
{
'sells': [ [ 640000, 6789.5199, 4345292736, false, null, 87, 1727945621848 ], [ 635000, 8051.66, 5112804100, false, null, 102, 1727945044697 ] ],
'buys': [ [ 631000, 365.84, 230845039.99999997, false, null, 5, 1727945696541 ], [ 630604, 23.91, 15077741.64, false, null, 0, 1727945561696 ] ],
}

همچنین اگر از SDK رسمی استفاده نمی‌کنید، در صورت اتصال و اشتراک صحیح، پیام‌های دریافتی از کانال به شکل زیر خواهد بود:
{
'push': {
'channel': 'orderbook:11',
'pub': {
'data': '{"buys": [["35077909990", "0.009433"], ["35078000000", "0.000274"], ["35078009660", "0.00057"]], "sells": [["35020080080", "0.185784"], ["35020070060", "0.086916"], ["35020030010", "0.000071"]], "lastTradePrice": "35077909990", "lastUpdate": 1726581829816}',
'offset': 49890
} } }
استریم لیست آخرین تراکنش‌ها (lastTrades)
الگوی کانال‌های آخرین تراکنش: last-trades:{pair_id}

مثال: برای دریافت تغییرات اردربوک تتر به ریال، کافیست به کانال last-trades:11 متصل شوید.

در صورتی که از SDK استفاده نمی‌کنید پیام زیر را ارسال نمایید:
{
'id': 3,
'subscribe': { 'channel': 'last-trades:11' }
}
پارامترهای پاسخ
{
'push': {
'channel': 'last-trades:11',
'pub': {
'data': '16E B:[[923501,15K@WG,1:5J@3G,q:140,"d451e9f4872f920fe78126e173c3d5f1"],[923500,0.029H@Jl,14K@V,1:]2oTULX;',
'offset': 111384
'delta': true
}
}
}