مثال برای گرفتن قیمت بازار
publicapi.ramzinex.com/exchange/api/v1.0/exchange/orderbooks/643/buys_sells
خروجی زیر رو میده اولی قیمت دومی حجم برای خرید و فروش 
نکته که وجود داره در رمیزنکس کمترین قیمت فروش اخر لیست فروش هست

{
    "data": {
        "buys": [
            [
                3.516,
                0.01,
                
            ],
            [
                3.498,
                131.7,
                
            ],
            [
                3.496,
                257.2,
                
            ],
            
        ],
        "sells": [
            
            
            [
                3.526,
                255,
               
            ],
            [
                3.521,
                78.92,
                
            ],
            [
                3.519,
                130.9,
                
            ]
        ]
    },
    "status": 0
}


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


