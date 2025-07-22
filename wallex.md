مارکت های والکس
با استفاده از API زیر میتوانید لیست کاملی از مارکت های فعال در والکس را دریافت کنید.
همچنین در هر نوع معامله ی والکس نحوه ی دریافت مارکت های فعال در آن معامله به طور کامل آموزش داده شده است.


get
/hector/web/v1/markets
curl


curl -i -X GET \
  https://api.wallex.ir/hector/web/v1/markets \
  -H 'x-api-key: YOUR_API_KEY_HERE'
Response
200
application/json




{
  "success": true,
  "message": "The operation was successful",
  "result": {
    "markets": [
      {
        "symbol": "string",
        "base_asset": "string",
        "quote_asset": "string",
        "fa_base_asset": "string",
        "fa_quote_asset": "string",
        "en_base_asset": "string",
        "en_quote_asset": "string",
        "categories": [ … ],
        "price": "string",
        "change_24h": 0.1,
        "volume_24h": 0.1,
        "change_7D": 0.1,
        "quote_volume_24h": 0.1,
        "spot_is_new": true,
        "otc_is_new": true,
        "is_new": true,
        "is_spot": true,
        "is_otc": true,
        "is_margin": true,
        "is_tmn_based": true,
        "is_usdt_based": true,
        "is_zero_fee": true,
        "leverage_step": 0.1,
        "max_leverage": 0,
        "created_at": "2019-08-24T14:15:22Z",
        "amount_precision": 0,
        "price_precision": 0,
        "flags": [ … ]
      }
    ]
  }
}
توضیحات Response-Body


{
  "result": {
    "markets": [
      {
        "symbol": "بازار معامله",
        "base_asset": "رمزارز معامله شونده",
        "quote_asset": "ارز قیمت گذار",
        "fa_base_asset": "نماد ارز معامله شونده",
        "fa_quote_asset": "نماد ارز قیمت گذار",
        "en_base_asset": "نماد ارز معامله شونده",
        "en_quote_asset": "نماد ارز قیمت گذار",
        "categories": [
          "number"
        ],
        "price": "قیمت در لحظه فراخوانی ای پی آي",
        "change_24h": "تغییرات 24 ساعته",
        "volume_24h": "حجم 24 ساعته",
        "change_7D": "تغییرات هفت روزه",
        "quote_volume_24h": "حجم تغییرات 24 ساعته",
        "spot_is_new": "آیا به تازگی در بازار اسپات اضافه شده هست",
        "otc_is_new": "آیا به تازگی در بازار خریدفروش آنی اضافه شده هست",
        "is_new": "آیا ارز جدید هست",
        "is_spot": "وضعیت فعال بودن در بازار اسپات",
        "is_otc": "وضعیت فعال بودن در بازار خرید فروش آنی",
        "is_margin": "وضعیت فعال بودن در بازار تعهدی",
        "is_tmn_based": "وضعیت فعال بودن در پایه بازار تومان",
        "is_usdt_based": "وضعیت فعال بودن در پایه بازار تتر",
        "is_zero_fee": "وضعیت رایگان بودن کارمزد در این بازار",
        "leverage_step": "-",
        "max_leverage": "-",
        "created_at": "زمان اضافه شدن رمز ارز",
        "amount_precision": "-",
        "price_precision": "-",
        "flags": ["-"]
      }
    ],
    "message": "The operation was successful",
    "success": true
  }
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