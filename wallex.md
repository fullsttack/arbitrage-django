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

