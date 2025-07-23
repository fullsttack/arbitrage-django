مثال برای گرفتن قیمت بازار
https://api.wallex.ir/v1/depth?symbol=XRPUSDT
خروجی زیر رو میده اولی قیمت دومی حجم برای خرید و فروش

{
    "result": {
        "ask": [
            {
                "price": 3.51436,
                "quantity": 262.3,
                "sum": "921.816628"
            },
            {
                "price": 3.51437,
                "quantity": 149.4,
                "sum": "525.046878"
            },
            {
                "price": 3.51769,
                "quantity": 262.1,
                "sum": "921.986549"
            },
            
        ],
        "bid": [
            {
                "price": 3.5003,
                "quantity": 381.2,
                "sum": "1334.31436"
            },
            {
                "price": 3.50011,
                "quantity": 263.4,
                "sum": "921.928974"
            },
            {
                "price": 3.5001,
                "quantity": 142.8,
                "sum": "499.81428"
            },
            
        ]
    },
    "message": "عملیات موفقیت‌آمیز بود.",
    "success": true
}

عمق بازارها
جهت دریافت سفارش‌های اوردر بوک و عمق بازارها، میتوانید از API زیر استفاده کنید.
توجه داشته باشید استفاده از API به طور مکرر جهت دریافت عمق بازار ها توصیه نمیشود و ممکن هست با Rate-Limit مواجه شوید.
جهت دریافت عمق بازار خرید ، میتوانید به آموزش سوکت عمق بازار خرید مراجعه کنید.
همچنین جهت دریافت عمق بازار فروش ، میتوانید به آموزش سوکت عمق بازارفروش مراجعه کنید.


get
/v1/depth
curl


curl -i -X GET \
  'https://api.wallex.ir/v1/depth?symbol=USDCUSDT' \
  -H 'x-api-key: YOUR_API_KEY_HERE'
Response
200
application/json




{
  "result": {
    "ask": [ … ],
    "bid": [ … ]
  },
  "message": "عملیات موفقیت‌آمیز بود.",
  "success": true
}
توضیحات Response-Body
توجه داشته باشید که result.ask مربوط به لیست فروشندگان میباشد و result.bid مربوط به لیست خریداران میباشد



{
    "result": {
        "ask": [
            {
                "price": "قیمت واحد",
                "quantity": "حجم سفارش",
                "sum": "مجموع کل که شامل ضریب قیمت در حجم میباشد"
            }
        ],
        "bid": [
            {
                "price": "قیمت واحد",
                "quantity": "حجم سفارش",
                "sum": "مجموع کل که شامل ضریب قیمت در حجم میباشد"
            }

        ]
    },
    "message": "وضعیت موفقیت آمیز بودن درخواست",
    "success": true
}

دریافت عمق بازار خرید (buyDepth)
از طریق این کانال می‌توانید سفارش‌های خرید موجود در Order Book یک بازار خاص را به‌صورت لحظه‌ای دریافت کنید.
این داده‌ها برای نمایش لیست سفارش‌های خرید، تحلیل عمق بازار، و طراحی ابزارهای معاملاتی بسیار کاربردی هستند.

آدرس اتصال WebSocket
برای اتصال باید از آدرس زیر استفاده کنید.



wss://api.wallex.ir/ws
فرمت پیام Subscribe
برای دریافت عمق بازار باید پیام خود را با فرمت زیر ارسال کنید و میتوانید هر مارکتی را جایگزین MARKET قرار دهید



["subscribe", { "channel": "MARKET@buyDepth" }]
مثال



["subscribe", { "channel": "َUSDTTMN@buyDepth" }]
["subscribe", { "channel": "َBTCUSDT@buyDepth" }]
نمونه Response-Body
پس از ارسال پیام در سوکت ، فرمت جواب هایی که دریافت میکنید به‌صورت زیر میباشد که هر آبجکت بیانگر یک اوردر در اوردربوک میباشد.

فیلد	توضیحات
quantity	مقدار سفارش
price	قیمت هر واحد
sum	مجموع مقدار سفارش


  [
    "USDTTMN@buyDepth",
    [
      { "quantity": 255.75, "price": 82131, "sum": 21005003.25 },
      { "quantity": 103.07, "price": 82083, "sum": 8460294.81 },
      { "quantity": 139.05, "price": 82066, "sum": 11411277.3 }
    ]
  ]
نمونه کد در زبان های مختلف
JavaScript
Python
GOLang
cURL (websocat)



  const socket = new WebSocket("wss://api.wallex.ir/ws");

  socket.addEventListener("open", () => {
    socket.send(JSON.stringify(["subscribe", { channel: "USDTTMN@buyDepth" }]));
  });

  socket.addEventListener("message", event => {
    console.log("Message from server:", event.data);
  });

  دریافت عمق بازار فروش (sellDepth)
از طریق این کانال می‌توانید سفارش‌های فروش موجود در Order Book یک بازار خاص را به‌صورت لحظه‌ای دریافت کنید.
این داده‌ها برای نمایش لیست سفارش‌های فروش ، تحلیل عمق بازار، و طراحی ابزارهای معاملاتی بسیار کاربردی هستند.

آدرس اتصال WebSocket
برای اتصال باید از آدرس زیر استفاده کنید



wss://api.wallex.ir/ws
فرمت پیام Subscribe
برای دریافت عمق بازار باید پیام خود را با فرمت زیر ارسال کنید و میتوانید هر مارکتی را جایگزین MARKET قرار دهید



["subscribe", { "channel": "MARKET@sellDepth" }]
مثال



["subscribe", { "channel": "َUSDTTMN@sellDepth" }]
["subscribe", { "channel": "َBTCUSDT@sellDepth" }]
نمونه Response-Body
پس از ارسال پیام در سوکت ، فرمت جواب هایی که دریافت میکنید به‌صورت زیر میباشد که هر آبجکت بیانگر یک اوردر در اوردربوک میباشد.

فیلد	توضیحات
quantity	مقدار سفارش
price	قیمت هر واحد
sum	مجموع مقدار سفارش


  [
    "USDTTMN@sellDepth",
    [
      { "quantity": 255.75, "price": 82131, "sum": 21005003.25 },
      { "quantity": 103.07, "price": 82083, "sum": 8460294.81 },
      { "quantity": 139.05, "price": 82066, "sum": 11411277.3 }
      
    ]
  ]
نمونه کد در زبان های مختلف
JavaScript
Python
GOLang
cURL (websocat)



  const socket = new WebSocket("wss://api.wallex.ir/ws");

  socket.addEventListener("open", () => {
    socket.send(JSON.stringify(["subscribe", { channel: "USDTTMN@sellDepth" }]));
  });

  socket.addEventListener("message", event => {
    console.log("Message from server:", event.data);
  });