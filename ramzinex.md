مستندات API رمزینکس
پیش گفتار
مستندات API رمزینکس راهنمایی‌ست برای معامله‌گرهای حرفه‌ای و توسعه‌دهندگان تا با استفاده از APIهای فراهم‌ شده، بیشترین بهره را از حساب کاربری رمزینکس خود ببرند. با استفاده از API رمزینکس قادر خواهید بود به روش خودکار و مبتنی بر کد، علاوه بر اطلاع از آخرین قیمت‌ها و وضعیت بازار رمزارزها در ایران، اقدام به مدیریت حساب رمزینکس خود نمایید. این راهنما مستندی رسمی‌ست و متناسب با آخرین تغییرات APIهای رمزینکس بروز می‌شود. جهت آگاهی از تغییرات احتمالی در بستر رمزینکس یا ساختار و جزئیات APIها، همواره به اطلاعیه‌های کانال رسمی تلگرام رمزینکس دقت کنید. برای آشنایی با چگونگی استفاده از API رمزینکس در زبان‌های برنامه‌نویسی مختلف، این مجموعه حاوی چند نمونه از اندپوینت‌های رمزینکس فراهم شده است. برای اطلاع از همه اندپوینت‌های منتشر شده رمزینکس از مرجع رسمی مستندات رمزینکس استفاده نمایید. شما با استفاده API های رمزینکس قوانین و مقررات موجود در سایت رمزینکس را پذیرفته‌اید.
پیش نیاز
راهنمای ساخت و مدیریت کلیدهای API
برای ساخت و مدیریت کلیدهای API باید به بخش مدیریت API سایت رمزینکس مراجعه کنید. برای ساخت کلید جدید بر روی دکمهٔ «ساخت کلید API» کلیک کنید.

API Management
در بخش ساخت API، لازم است که برای کلید جدید نامی منحصربه‌فرد و دلخواه انتخاب کنید. در ادامه دسترسی‌های لازم برای این کلید API از بین خواندن، برداشت، لغو سفارش و معامله انتخاب کنید. برای امنیت بیشتر در انتخاب مجوزهای دسترسی دقت کافی داشته باشید و در صورت امکان فهرستی از IPهای مجاز که با استفاده از کلید می‌توانند به اندپوینت‌های شخصی دسترسی داشته باشند را وارد کنید. در صورتی که گزینه بدون محدودیت را انتخاب کنید به معنای اعطای مجوز به تمام IPها است. توجه داشته باشید برای کلیدهایی که دسترسی «برداشت» دارند، مشخص کردن حداقل یک IP الزامی‌ست. همچنین حتما در حفاظت از کلیدهای API خود دقت کافی داشته و آن را با دیگران به اشتراک نگذارید. اگر به طور ناخواسته دیگران به کلید API شما دسترسی یافتند، از طریق بخش مدیریت API در سایت رمزینکس اقدام به حذف کلید افشاشده نمایید.
راهنمای استفاده از کلید‌ API
برای دسترسی به‌ API های خصوصی، نیاز به کلید خصوصی و توکن خصوصی است. برای دریافت کلید خصوصی طبق توضیحات قسمت قبل عمل کنید. برای دریافت توکن خصوصی نیز از API گرفتن توکن خصوصی در بخش احراز هویت استفاده کنید. ‫برای دسترسی به APIهای خصوصی نیاز به قرار گرفتن کلید خصوصی و توکن خصوصی در هدر درخواست HTTP به صورت زیر است:
Authorization2: Bearer 'Your-Token'

x-api-key: Your-Api-Key

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
لیست آخرین معاملات بازار
برای دریافت لیست معاملات انجام شده در بازار از این نوع درخواست استفاده نمایید:

path Parameters
pairId	
integer
Example: 11
شناسه بازار می‌باشد و مقدار آن عدد است

Responses
200 موفق

get
/orderbooks/{pair_id}/trades
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/11/trades' --header 'Content-Type: application/json'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"data": [
[],
[]
],
"status": 0
}
ارزهای رمزینکس
مشخصات ارزهایی که در رمزینکس خرید و فروش می‌شوند

Responses
200 موفق

get
/currencies
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v2.0/exchange/currencies'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"currencies": [
{
"id": 1,
"name": {},
"precision": 5,
"symbol": "btc",
"logo": "https://public-assets.ramzinex.com/public/currencies/logo/btc.png",
"color": "FF8C00",
"related_pairs": [],
"rial_related_pair": 2,
"withdraw": 1,
"deposit": 1,
"slug": "bitcoin-btc"
},
{
"id": 2,
"name": {},
"precision": 0,
"symbol": "irr",
"logo": "https://public-assets.ramzinex.com/public/currencies/logo/irr.png",
"color": "f8bbd0",
"related_pairs": [ ],
"rial_related_pair": null,
"withdraw": 1,
"deposit": 1,
"slug": null
}
]
}
}
مشخصات یک ارز مشخص
برای دریافت اطلاعات یک ارز رمزینکس از این نوع درخواست استفاده نمایید

path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Responses
200 موفق

get
/currencies/9
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v2.0/exchange/currencies/9'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"currency": {}
}
}
بازارهای رمزینکس
دریافت مشخصات وضعیت بازارهای رمزینکس

Responses
200 موفق

get
/pairs
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v2.0/exchange/pairs'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"pairs": []
}
}
مشخصات یک بازار مشخص
برای دریافت مشخصات یک بازار مشخص از این نوع درخواست استفاده نمایید

path Parameters
pairId	
integer
Example: 11
شناسه بازار می‌باشد و مقدار آن عدد است

Responses
200 موفق

get
/pairs/{pair_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v2.0/exchange/pairs/2'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"pair": {}
}
}
قیمت تمام شده خرید یک ارز
قیمت تمام شده خرید یک ارز با مقدار مشخص شده در بازار رمزینکس

path Parameters
pairId	
integer
Example: 11
شناسه بازار می‌باشد و مقدار آن عدد است

Responses
200 موفق

get
/orderbooks/{pair_id}/market_buy_price
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/11/market_buy_price'
Response samples
200
Content type
application/json

Copy
{
"data": 695572,
"status": 0
}
قیمت تمام شده فروش یک ارز
قیمت تمام شده فروش یک ارز با مقدار مشخص شده در بازار رمزینکس

path Parameters
pairId	
integer
Example: 11
شناسه بازار می‌باشد و مقدار آن عدد است

Responses
200 موفق

get
/orderbooks/{pair_id}/market_sell_price
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/11/market_sell_price'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"price": 9310000000
}
}
آمار 24 ساعته بازارها
برای دریافت آخرین آمار بازارهای رمزینکس در 24 ساعت گذشته از این درخواست استفاده نمایید.

Responses
200 موفق

get
/chart/statistics-24
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/chart/statistics-24'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"data": {
"10": {},
"106": {}
},
"status": 0
}
کندل ها (آمار OHLC بازارها)
با این درخواست می‌توانید کندل‌های بازارهای رمزینکس را در بازهٔ زمانی مشخص دریافت کنید.

query Parameters
symbol	
رشته
Example: symbol=GOLDIRR
نماد انگلیسی بازار

resolution	
string
Enum: 1 60 180 360 720 "1D"
Example: resolution=60
تعیین بازه زمانی کندل‌ها(برحسب دقیقه)

from	
timestamp
Example: from=1724576847
زمان شروع بازه زمانی کندل‌ها

to	
timestamp
Example: to=1729760907
زمان پایان بازه زمانی کندل‌ها

Responses
200 موفق

get
/chart/tv/history
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/chart/tv/history?symbol=GOLDIRR&resolution=60&from=1724576847&to=1729760907'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"c": [
40792,
40973,
40394,
40804
],
"h": [
41200,
41200,
41118,
41000
],
"l": [
40791,
40792,
40394,
40394
],
"o": [
40792,
40792,
40973,
40394
],
"s": "ok",
"t": [
1728389453,
1728392561,
1728396005,
1728399681
],
"v": [
24159.9025,
8416.6203,
4739.7176,
14744.8487
]
}
احراز هویت
برای دسترسی به API ‌های خصوصی، داشتن توکن خصوصی الزامیست. برای دریافت توکن و کلید خصوصی به بخش مدیریت API مراجعه کنید.
برای دسترسی به این API ها نیاز به ارسال HTTP Header ها و ارسال کلید خصوصی و توکن خصوصی به صورت زیر است :
Authorization2: Bearer Your-Token

x-api-key: Your-Api-Key

دریافت مشخصات کلید خصوصی
Request Body schema: application/json
required
Schema not provided
Responses
200 موفق
500 ارسال توکن اشتباه و یا آیدی نامعتبر

post
/auth/api_key/apiKeyDetail
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"api_key_id": 2579
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"id": 2759,
"api_key": "****",
"name": "apiKeyName",
"withdraw": 0,
"trade": 0,
"cancel_order": 0,
"excel_output": 1,
"ip_free": 1,
"2fa": 1,
"agree": 0,
"address_free": 0,
"alert": 1,
"ips": [ ],
"created_at_ms": 1735389656,
"updated_at_ms": 1735389656
}
}
لیست تمام کلیدهای خصوصی
Responses
200 موفق

get
/auth/api_key/apiKeyList
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/auth/api_key/apiKeyList' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"count": 1,
"data": [
{}
]
}
بروزرسانی دسترسی‌های عمومی
Request Body schema: application/json
required
addressFree
required
number (addressFree)
دسترسی به برداشت

alert
required
number (alert)
دسترسی به ثبت سفارش

Responses
200 موفق

post
/auth/api_key/editGeneralAccess
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"addressFree": 0,
"alert": 1
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": [ ],
"description": {
"fa": "دسترسی ها با موفقیت آپدیت شد",
"en": "Accesses were successfully updated"
}
}
گرفتن توکن خصوصی
برای گرفتن API Key ابتدا به بخش مدیریت API مراجعه کنید. بعد از ساخت API Key کلید محرمانه و API Key خود را در HTTP Body Request خود ارسال کنید.

Request Body schema: application/json
required
api_key
required
string (api_key)
کلید API

secret
required
string (secret)
کلید محرمانه

Responses
200 موفق

post
/auth/api_key/getToken
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"api_key": "ApiKeyAzi6AZw:0fdebee3ebc78abccddcc4b2c53db609b60e070ba83412c1540d8b7f952b277d1",
"secret": "8abc111qsad11111c1222716306bf29807f7c7"
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"token": "abc2eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ8.eyJwcml2YXRlIjoie1wid1wiOjAsXCJ0XCI6MCxcINcIjowLFwiZVwiOjEsXCJpZlwiOjF9IiwiZ2VuZXJhbCI6IntcImFmXCI6MCxcImFsZXJ0XCI6MX0iLCJleHAiOjE2NTcxMTA5MzcsImlwIjoiW10iLCJzaWQiOiJBeWkyQVp3In0.WcEWBQjFH13WRTXMNRq55YxgvKI-5E5NdiJmktYsBpNfeLzyd7L9I-2RZJUfWruSUe7ef76QlP_iSr7udD3fmiPDqlY39FkBkE34lnAjF6xj6xv5CV573JlXjtg78JLba3-h4ga4DwlGiXL1TSPJRWAgglZknSQ4jzu6JO2KXjjie7dWKVvvbR5_Ps3Tja5QGsoIJa_UQDmqMVUZ0ucZ1MbrNSI_jZu9XXWPhEV3xQpVVTXIr5JkGuM7hNzogwel4wITdSbUtl2oiFc441JesnQpqmGibQwzlimFAe_DircKHIi3O4rSBaW873hEBPgvhphoo-mMiUNkGSEc2IkO3A"
}
}
کیف پول
جمع میزان دارایی در دسترس و درحال معامله باید معادل مقدار کل دارایی باشد.

سرمایه در دسترس کاربر برای یک ارز

نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

get
/funds/available/currency/{currency_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/available/currency/9' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
{
"status": 0,
"data": 6.28
}
سرمایه کل کاربر برای یک ارز

نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

get
/funds/total/currency/{currency_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/total/currency/9' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
{
"status": 0,
"data": 6.28
}
میزان سرمایه در حال معامله کاربر

نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

get
/funds/in_orders/currency/{currency_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/in_orders/currency/9' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
{
"status": 0,
"data": 6.28
}
شبکه‌های موجود برای واریز و برداشت یک ارز
برای دریافت لیست شبکه‌های موجود برای واریز یا برداشت از این نوع درخواست استفاده کنید:

query Parameters
currency_id	
integer
Example: currency_id=9
شناسه ارز می‌باشد و مقدار آن عدد است

withdraw	
integer
Example: withdraw=1
وجود یا عدم وجود شبکه‌های برداشت در لیست پاسخ

deposit	
integer
Example: deposit=0
وجود یا عدم وجود شبکه‌های واریز در لیست پاسخ

Responses
200 موفق

get
/networks
Request samples
cURLPHPPython

Copy
curl --location 'https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/networks?currency_id=46&deposit=1&withdraw=1'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"data": [
{},
{},
{}
],
"status": 0
}
آدرس‌های کاربر
برای دریافت آدرس‌های موجود برای یک ارز از این نوع درخواست استفاده کنید


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
networks
required
list (networks)
لیست شناسه‌ی نتورک‌ها

Responses
200 موفق
401 ارسال توکن اشتباه
500 ارسال آیدی نتورک اشتباه

post
/users/me/addresses
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
Expand allCollapse all
{
"networks": [
116
]
}
Response samples
200
Content type
application/json
Example

پاسخ صحیح
پاسخ صحیح

Copy
Expand allCollapse all
{
"status": 0,
"count": 1,
"data": [
{}
]
}
دارایی
برای دریافت میزان کل دارایی‌های یک کاربر از این درخواست استفاده کنید.


نکته:

.این درخواست نیازمند ارسال توکن است
Responses
200 موفق

get
/users/me/funds/summaryDesktop
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/summaryDesktop' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": [
{},
{},
{},
{},
{}
]
}
بروز رسانی کیف پول
برای بروزرسانی کیف پول خود از این درخواست استفاده کنید


نکته:

.این درخواست نیازمند ارسال توکن است
Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/refresh
Request samples
cURLPHPPython

Copy
curl --location --request POST 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/refresh' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
{
"status": 0
}
تخصیص آدرس به کیف پول کاربر
برای تخصیص آدرس ارز برای کاربر از این درخواست استفاده کنید


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
network_id
required
number (network_id)
شناسه شبکه

currency_id
required
number (currency_id)
شناسه رمزارز

Responses
200 موفق
401 ارسال توکن اشتباه
422 ارسال ناقص بدنه‌ی درخواست

post
/users/me/create_address
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"currency_id": 9,
"network_id": 1
}
Response samples
200422
Content type
application/json
Example

CreateAddressRes
CreateAddressRes

Copy
{
"status": 0
}
واریزها و برداشت‌ها
مشخصات واریزهای انجام شده کاربر برای یک ارز مشخص

نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

get
/funds/deposits/currency/{currency_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/deposits/currency/9' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****' --data ''
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": [
{},
{},
{},
{},
{},
{}
]
}
مشاهده واریزهای کاربر برای ارزهای مشخص شده
مشخصات واریزهای انجام شده کاربر برای ارزهای مشخص


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
optional
currencies	
list (currencies)
لیست شناسه رمزارزها

limit	
number (limit)
تعداد آبجکت‌های هر ریکوئست

offset	
number (offset)
از آبجکت چند به بعد نشان داده شود

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/deposits
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
Expand allCollapse all
{
"limit": 5,
"offset": 1,
"currencies": [
2,
9,
46
]
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"count": 20,
"data": [
{},
{},
{}
]
}
مشخصات یک واریز مشخص

نکته:

.این درخواست نیازمند ارسال توکن است
query Parameters
deposit_id	
integer
Example: deposit_id=45238401
شناسه یک واریز خاص می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 موفق

get
/users/me/funds/deposits/{deposit_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/deposits/10412179' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"id": 10412179,
"amount": "2.00",
"amount_nr": 2,
"address": "0x06a7730b6a119e4ca2F709BC7458B18C1a16A38d",
"currency_id": 9,
"txid": "club_60_9057",
"link": "https://etherscan.io/tx/club_60_9057",
"confirm": 1,
"created_at": "03-04-08 02:34",
"created_at_ms": 1719529446
}
}
مشخصات برداشت‌ها
برای دریافت مشخصات برداشت‌های یک ارز کاربر از این درخواست استفاده کنید


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
optional
currencies	
list (currencies)
لیست شناسه رمزارزها

limit	
number (limit)
تعداد آبجکت‌های هر ریکوئست

offset	
number (offset)
از آبجکت چند به بعد نشان داده شود

Responses
200 موفق
401 ارسال توکن اشتباه

get
/users/me/funds/withdraws
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
Expand allCollapse all
{
"currencies": [
9
]
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"count": 317,
"data": [
{}
]
}
مشخصات یک برداشت خاص

نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
withdraw_id	
integer
Example: 72385076
شناسه یک برداشت خاص می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

get
/users/me/funds/withdraws/{withdraw_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/withdraws/8389403' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"count": 2,
"data": [
{},
{}
]
}
درخواست برداشت ارز
درخواست برداشت ارز به یک آدرس مشخص


نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Request Body schema: application/json
required
amount
required
number (amount)
مقدار خرید با واحد ریال یا مقدار فروش با واحد ارز

address
required
string (address)
آدرس

network_id
required
number (network_id)
شناسه شبکه

currency_id
required
number (currency_id)
شناسه رمزارز

tag	
string (tag)
تگ

no_tag	
boolean (no_tag)
Enum: true false
تعیین تگ داشتن یا نداشتن

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/withdraws/currency/{currency_id}
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"amount": 0.5,
"address": "0x484E993a8B4b731E8e1801777722109f3953b6bF",
"network_id": 303,
"currency_id": 166,
"tag": "1234",
"no_tag": false
}
Response samples
200
Content type
application/json
Example

پاسخ موفق
پاسخ موفق

Copy
Expand allCollapse all
{
"status": 0,
"count": 727,
"data": [
{},
{}
]
}
تایید یک برداشت
برای تایید یک برداشت، کد ارسال شده در پیامک و کد Google Authenticator (در صورت فعالسازی) را به این درخواست ارسال کنید.


نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
withdraw_id	
integer
Example: 72385076
شناسه یک برداشت خاص می‌باشد و مقدار آن عدد است

Request Body schema: application/json
required
code	
string (code)
gaCode	
string (gaCode)
Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/withdraws/{withdraw_id}/verify
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"code": "557018",
"gaCode": "394570"
}
Response samples
200
Content type
application/json
Example

پاسخ موفق
پاسخ موفق

Copy
Expand allCollapse all
{
"status": 0,
"count": 727,
"data": [
{},
{}
]
}
لغو یک برداشت
برای کنسل کردن یک برداشت مشخص از این درخواست استفاده کنید.

در نظر داشته باشید که هنگام ثبت یک برداشت موجودی از حساب شما کم می‌شود و تا قبل زمان لغو یک برداشت این موجودی به حساب شما بر نمی‌گردد.


نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
withdraw_id	
integer
Example: 72385076
شناسه یک برداشت خاص می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/withdraws/{withdraw_id}/cancel
Request samples
cURLPHPPython

Copy
curl --location --request POST 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/withdraws/8849988/cancel' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****' --data ''
Response samples
200
Content type
application/json
Example

برداشت با موفقیت لغو شد.
برداشت با موفقیت لغو شد.

Copy
{
"status": 0
}
به‌روز رسانی واریزها
به‌روز رسانی واریزهای یک ارز کاربر


نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
currency_id	
integer
Example: 9
شناسه ارز می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/deposits/refresh/currency/{currency_id}
Request samples
cURLPHPPython

Copy
curl --location --request POST 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/deposits/refresh/currency/11' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
{
"status": 0
}
پاداش و کمیسیون
جزئیات ریزپاداش‌های کاربر
جمع تمام پاداش‌های دریافتی به تفکیک ارز


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
offset	
number (offset)
از آبجکت چند به بعد نشان داده شود

limit	
number (limit)
تعداد آبجکت‌های هر ریکوئست

pairs	
list (pairs)
لیست بازارها

states	
number (states)
Enum: 1 2 3 4
مقدار ۱: سفارشات باز / مقدار ۲: سفارشات لغو شده / مقدار ۳: سفارشات انجام شده / مقدار ۴: سفارشات بخشی انجام شده

isbuy	
boolean (isbuy)
Enum: true false
سفارش ها از نوع خرید باشند یا خیر

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/funds/bonuses
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
Expand allCollapse all
{
"offset": 2,
"limit": 10,
"pairs": [
11,
46
],
"states": 1,
"isbuy": "True"
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"count": 41,
"data": [
{}
]
}
کمیسیون مربوط به تراکنش‌های انجام شده
میزان کمیسیون مربوط به تراکنش‌های انجام شده توسط کاربر


نکته:

.این درخواست نیازمند ارسال توکن است
Responses
200 موفق
401 ارسال توکن اشتباه

get
/users/me/funds/commissions
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/commissions' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": [
{},
{},
{},
{},
{},
{},
{},
{},
{},
{}
],
"count": 742
}
کمیسیون کاربر در بازارهای مختلف

نکته:

.این درخواست نیازمند ارسال توکن است
Responses
200 موفق
401 ارسال توکن اشتباه

get
/user/fee
Request samples
curlPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v2.0/exchange/user/fee' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"quotes": {},
"special_markets": {}
}
}
کل پاداش‌های کاربر
مشاهده کل پاداش‌های کاربر


نکته:

.این درخواست نیازمند ارسال توکن است
Responses
200 موفق
401 ارسال توکن اشتباه

get
/users/me/funds/bonuses/total
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/funds/bonuses/total' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"more_info_url": "string",
"referral_code": "string",
"referrals": [],
"ref_count": 0
}
}
سفارشات و معاملات
دریافت سفارش‌های کاربر
دریافت سفارش‌های کاربر با مشخصات خاص


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
offset	
number (offset)
از آبجکت چند به بعد نشان داده شود

limit	
number (limit)
تعداد آبجکت‌های هر ریکوئست

pairs	
list (pairs)
لیست بازارها

isBuy	
boolean (isbuy)
Enum: true false
سفارش ها از نوع خرید باشند یا خیر

states	
number (states)
Enum: 1 2 3 4
مقدار ۱: سفارشات باز / مقدار ۲: سفارشات لغو شده / مقدار ۳: سفارشات انجام شده / مقدار ۴: سفارشات بخشی انجام شده

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/orders3
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
Expand allCollapse all
{
"offset": 2,
"limit": 10,
"pairs": [
11,
46
],
"isBuy": "True",
"states": 1
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"count": 729,
"data": [
{},
{}
]
}
مشخصات یک سفارش
مشخصات یک سفارش مشخص


نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
order_id	
integer
Example: 12492304507
شناسه یک سفارش خاص می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه
404 ارسال شناسه اشتباه

get
/users/me/orders2/{order_id}
Request samples
cURLPHPPython

Copy
curl --location 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/orders2/781742310' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"id": 593992781,
"pair": "silly dragon/rial",
"pair_obj": {},
"pair_name": {},
"pair_id": 411,
"type_id": 1,
"type_id_v2": 11,
"type_v2_all_lang": {},
"type": "فروش",
"type_en": "sell",
"amount": "1,452.36 silly",
"stop_price": null,
"limit_price": null,
"stop_limit_price": null,
"amount_nr": 1452.35,
"total_quote_amount_nr": 42116987,
"amount_quote_nr": 42116987,
"average_price": "28,999 irr",
"average_price_nr": 28999.001996681403,
"order_price": 28999,
"order_price_nr": 28999,
"total_payment": "0.00 silly",
"total_payment_nr": 0,
"net_received": "0 irr",
"net_received_nr": 0,
"commission_currency_id": 2,
"commission_nr": 0,
"commission_percentage_nr": 0,
"filled_nr": 0,
"created_at": "03-01-06 15:09",
"created_at_ms": 1711363189,
"status": {},
"status_id": 1,
"account_id": null,
"reference_id": null,
"percent": "0 %",
"percent_num": 0,
"cancel_route": "https://ramzinex.com/exchange/order/cancelOrder/593992781"
}
}
ارسال سفارش محدود
سفارش برای یک بازار مشخص (مانند بازار بیت کوین/ریال)، با قیمت و مقدار مشخص شده از نوع خرید یا فروش ارسال می شود.


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
pair_id	
number (pair_id)
شناسه بازار

amount	
float (limitAmount)
مقدار خرید یا مقدار فروش با واحد ارز

price	
number (price)
قیمت واحد

type	
string (type)
Enum: "buy" "sell"
تعیین جهت سفارش (خرید یا فروش)

Responses
200 موفق
401 ارسال توکن اشتباه
500 اشتباه وارد کردن بدنه‌ی درخواست

post
/users/me/orders/limit
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"pair_id": 12,
"amount": 0.046,
"price": 12000,
"type": "buy"
}
Response samples
200
Content type
application/json
Example

success
success

Copy
Expand allCollapse all
{
"data": {
"order_id": 811235995
},
"status": 0
}
ارسال سفارش بازار
سفارش برای یک بازار مشخص (مانند بازار بیت کوین/ریال)، با بهترین قیمت بازار صورت می گیرد. برای خرید مقدار ریالی و برای فروش نیز مقدار رمز ارز مدنظرتان را ارسال کنید.


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
pair_id	
number (pair_id)
شناسه بازار

amount	
number (amount)
مقدار خرید با واحد ریال یا مقدار فروش با واحد ارز

type	
string (type)
Enum: "buy" "sell"
تعیین جهت سفارش (خرید یا فروش)

Responses
200 موفق
401 ارسال توکن اشتباه
500 اشتباه وارد کردن بدنه‌ی درخواست

post
/users/me/orders/market
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"pair_id": 11,
"amount": 2,
"type": "sell"
}
Response samples
200
Content type
application/json
Example

سفارش موفقیت آمیز
سفارش موفقیت آمیز

Copy
Expand allCollapse all
{
"data": {
"order_id": 811289310
},
"status": 0
}
کنسل کردن سفارش
کنسل کردن سفارش


نکته:

.این درخواست نیازمند ارسال توکن است
path Parameters
order_id	
integer
Example: 12492304507
شناسه یک سفارش خاص می‌باشد و مقدار آن عدد است

Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/orders/{order_id}/cancel
Request samples
cURLPHPPython

Copy
curl --location --request POST 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/orders/811235995/cancel' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json
Example

لغو موفق سفارش
لغو موفق سفارش

Copy
Expand allCollapse all
{
"description": "ok",
"status": 0,
"data": [ ]
}
کنسل کردن تمامی سفارشات باز
کنسل کردن سفارشات باز

توجه داشته باشید که این درخواست تمامی سفارشات باز از جمله سفارشات باز مارجین و ربات ها را نیز لغو خواهد کرد.


نکته:

.این درخواست نیازمند ارسال توکن است
Responses
200 موفق
401 ارسال توکن اشتباه

post
/users/me/cancelAllOpenOrders
Request samples
cURLPHPPython

Copy
curl --location --request POST 'https://api.ramzinex.com/exchange/api/v1.0/exchange/users/me/cancelAllOpenOrders' --header 'Authorization2: Bearer ****' --header 'x-api-key: ****'
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": [ ],
"count": 0
}
 حجم معاملات در یک بازه زمانی مشخص
حجم معاملات سی روزه


نکته:

.این درخواست نیازمند ارسال توکن است
Request Body schema: application/json
required
days	
integer
عدد ۳۰ برای دوره‌ی یکماهه

Responses
200 موفق
401 ارسال توکن اشتباه
422 ارسال بدون پارامتر

get
/users/me/orders/turnover
Request samples
PayloadcURLPHPPython
Content type
application/json

Copy
{
"days": 30
}
Response samples
200
Content type
application/json

Copy
Expand allCollapse all
{
"status": 0,
"data": {
"ninetyDayTurnover": "1,799,243,575",
"nextLevelTurnover": "5,000,000,000",
"volume": "1,799,243,575"
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
خطاها
کدهای وضعیت HTTP
توضیحات
کد وضعیت
موفقیت آمیز	200
ساخته شد	201
درخواست نامعتبر	400
عدم احراز هویت	401
درخواست شما یافت نشد.	404
ارسال بدون پارامتر	422
خطای داخلی سرور	500
سرویس در دسترس نمی‌باشد	503
