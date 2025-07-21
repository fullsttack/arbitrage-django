Introduction
Welcome to the LBANK API! You can use our API to access all market data, trading, and account management endpoints.The version of the document is V2,and it will continuously update.

LBANK offers powerful APIs for you to integrate into your applications. They are divided into three categories: account, trading, and market trends.

The account and trading APIs require authentication with an API key which allows you to create order、cancel order、query order and account info.

The market data API is publicly accessible and provides market data such as:historical price of trading pairs.

Process
To access the API, create an API key via this link API Key. Follow the instructions in setting up access.

Please remember below information after creation:

API Key is used in API request
Secret Key is used to generate the signature(only visible once after creation)
LBank support both RSA and HmacSHA256 signature.

RSA scheme is a digital signature scheme based on hardness of problem in math. It is a asymmetric cryptographic scheme. Sender obtains the signature data after encoding and computation of message and private key. Receiver checks the role of sender and the integrity of message according to the signature and the public key registered. Relatively, it is no need of private key in the validation of RSA scheme. It is ensured that only the user can send the valid message
HMAC is message authentication scheme based on hash function. It is a symmetric cryptographic scheme. Sender obtains the message authentication codes (MAC) after encoding and computation of message and shared key. Receiver checks the role of sender and the integrity of message. The scheme is effective and of high level security due to the security of hash function
 The API Key without boundled IP address will expire in 30 days.
 These two keys are important to your account safety, please don't share both of them together to anyone else. If you find your API Key is disposed, please remove it immediately.
SDK
Developers can use the LBank API in a way that suits them based on their preferences and usage scenarios. We currently provide in different language versions. Each SDK include full function interface in example file for directly using or testing. If you want to implement the SDK based on other language such as C#, the existing SDKs could be your best reference.

Python https://github.com/LBank-exchange/lbank-connector-python
Node.js https://github.com/LBank-exchange/lbank-connector-nodejs
Java https://github.com/LBank-exchange/lbank-connector-java
Go https://github.com/LBank-exchange/lbank-connector-go
Endpoints Configurations
We offers REST and WebSocket APIs. Both support market data, trading, and withdrawals.

REST API
REST (Representational State Transfer) is the most popular internet software architecture nowadays. It is clear in structure, easy to understand, and convenient to expand. More and more companies therefore apply the structures in their websites. It has following advantages:

1.In a RESTful architecture, each URL represents a resource
2.Between the client and the server, a certain presentation layer of such resources passed
3.The client uses the four HTTP commands to operate on the server-side resources to achieve “state transition of the presentation layer.”

We suggested that user should use the REST API for trading and/or asset operations (such as deposite and withdrawals)

WebSocket API
WebSocket protocol which achieves full-duplex communications over a single TCP connection between client and server is based on a new network protocol of the TCP. Server sends information to client, reducing unnecessary overhead such as frequent authentication. It greatest advantage includes that：

1.Request header is small in size (2 Bytes) .
2. The server no longer passively responses after receiving the client's request, but actively pushes the new data to the client.
3. There is no need to establish and close TCP connection repeatedly, so it saves bandwidth and server resources.

Changelog
Live Date Time(UTC+8)	API	Type	Description
2019.10.24 19:00			Init new version
2019.11.30 19:00	API	Add	Add /v2/cancel_clientOrders.do
2019.12.09 19:00	API	Add	Add HmacSHA256
2019.12.16 19:00	Echostr	Update	Update echostr param
2020.2.24 19:00	/v2/batch_create_order.do	Add	Add new API
2020.3.04 19:00	WebSocket	Add	Asset & Order add customerID return message
2020.06.10 19:00	/v2/create_order.do	Update	type add buy_maker, sell_maker, buy_ioc, sell_ioc, buy_fok, sell_fok
2020.07.07 19:00	/v2/get_deposit_address.do	Add	add get_deposit_address endpoint
2020.07.07 19:00	/v2/deposit_history.do	Add	add deposit_history endpoint
2021.06.28 19:00	WebSocket	Add	orderUpdate add orderPrice,orderAmt,avgPrice,accAmt,remainAmt
2021.07.13 19:00	API	Add	Added GET /v2/ticker/24hr.do currency market interface, it is recommended to replace GET /v2/ticker.do
2021.07.27 19:00	WebSocket	Add	Add assetUpdate
2022.02.14 19:00	/v2/supplement/system_status.do	Added	Get system status.
2022.02.14 19:00	/v2/supplement/user_info.do	Added	Get all the currency information for users (LBK supports deposit and withdrawal operations).
2022.02.14 19:00	/v2/supplement/withdraw.do	Added	User withdrawal (multi-chain support)
2022.02.14 19:00	/v2/supplement/deposit_history.do	Added	User gets deposit history Optimize return field
2022.02.14 19:00	/v2/supplement/withdraws.do	Added	User acquisition history optimization
2022.02.14 19:00	/v2/supplement/get_deposit_address.do	Added	User gets deposit address (supports multiple chains)
2022.02.14 19:00	/v2/supplement/asset_detail.do	Added	Asset details listed
2022.02.14 19:00	/v2/supplement/customer_trade_fee.do	Added	User transaction fee rate query
2022.02.14 19:00	/v2/supplement/api_Restrictions.do	Added	Query user API Key permissions
2022.02.14 19:00	/v2/supplement/system_ping.do	Added	Test server connectivity
2022.02.14 19:00	/v2/supplement/trades.do	Added	List of recent deals Optimize fields
2022.02.14 19:00	/v2/supplement/ticker/price.do	Addition	Get latest price of trading pair
2022.02.14 19:00	/v2/supplement/ticker/bookTicker.do	Add	Current optimal pending order
2022.02.14 19:00	/v2/supplement/create_order_test.do	Add	Test order
2022.02.14 19:00	/v2/supplement/create_order.do	Add	Order Optimization field
2022.02.14 19:00	/v2/supplement/cancel_order.do	Add	Cancel order Optimize fields
2022.02.14 19:00	/v2/supplement/cancel_order_by_symbol.do	Add	Cancel all pending orders for a single trading pair
2022.02.14 19:00	/v2/supplement/orders_info.do	Add	Query order optimization field
2022.02.14 19:00	/v2/supplement/orders_info_no_deal.do	Add	Current pending orders Optimization field
2022.02.14 19:00	/v2/supplement/orders_info_history.do	Add	Query all orders Optimize fields
2022.02.14 19:00	/v2/supplement/user_info_account.do	Add	Account Information
2022.02.14 19:00	/v2/supplement/transaction_history.do	Added	Historical transaction details
2022.11.03 18:00	/v2/create_order.do	Update	Increase the order expiration time
2022.11.03 18:00	/v2/batch_create_order.do	Update	Increase the order expiration time
2022.11.03 18:00	/v2/supplement/create_order.do	Update	Increase the order expiration time
2022.11.03 18:00	/v2/ticker/24hr.do	Update	Exclude ETF trading data
2022.11.03 18:00	/v2/ticker.do	Update	Exclude ETF trading data
2022.11.03 18:00	/v2/etfTicker/24hr.do	Added	Obtain ETF trading performance data
2022.12.16 18:00	/v2/transaction_history.do	Update	The query time is in seconds
2022.12.16 18:00	/v2/supplement/transaction_history.do	Update	The query time is in seconds
2023.02.23 18:00	/v2/order_transaction_detail.do	Update	New return field isMaker whether to mount unilateral
2024.06.06 18:00	REST API	Update	New global return field msg (detailed description of error code)
Interaction Introduction
URL
 Please initiate API calls with non-China IP. You can compare the delay of different domain names and choose the one with low delay.
REST API
https://www.lbkex.net/

https://api.lbkex.com/

https://api.lbank.info/

Websocket
wss://www.lbkex.net/ws/V2/

Endpoint Rate Limit
Create order and cancel order Request 500/10s

The other Request 200/10s

 To protect API communication from unauthorized change, all non-public API calls are required to be signed.
Authentication
To protect API communication from unauthorized change, all non-public API calls are required to be signed.

Request Header Setting
You should put the following parameters in every http requests

contentType:'application/x-www-form-urlencoded'

timestamp: millisecond of current time (1567833674095). It's strongly recommended that you get it from /v2/timestamp.do

signature_method: RSA/HmacSHA256.

echostr: the param is digit or letter，length is from 30 to 40. You can directly use echostr of SDK, it's safe.

Signature Process (how to generate the 'sign' parameter)
1. Get parameter String(need to be signed):

Each required parameter of API, exclude sign, add three additional parameters(signature_method, timestamp, echostr) , then we get the parameter string which need to be signed. The parameter string should be ordered according to the parameter name (first compares the first letter of all parameter names, in alphabet order, if you encounter the same first letter, then look at the second letter, and so on). For example, if we use user_info API, the parameter string is like

string parameters="api_key=c821db84-6fbd-11e4-a9e3-c86000d26d7c&echostr=P3LHfw6tUIYWc8R2VQNy0ilKmdg5pjhbxC7&signature_method=RSA&timestamp=1585119477235"

2. Turn parameters into MD5 digest：

The MD5 digest should be Hex encoded and all letters are uppercase.

string preparedStr = DigestUtils.md5Hex(parameters).toUpperCase()

3. Signature:

Users could use their secret key to perform a signature operation (Base64 coded) by RSA or HmacSHA256.

RSA method(signature_method = RSA):

use secret key of your api_key，sign the preparedStr(Base64 encode)，then we get the parameter sign.

RSA example:

    public static String RSA_Sign(String preparedStr, String secretKey) {
        try {
            PrivateKey priKey = getPrivateKey(secretKey);
            Signature signature = Signature.getInstance("SHA256WithRSA");
            signature.initSign(priKey);
            signature.update(content.getBytes(CharEncoding.UTF_8));
            byte[] signed = signature.sign();
            return new String(Base64.getEncoder().encode(signed));
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private static PrivateKey getPrivateKey(String key) {
        PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(Base64.getDecoder().decode(key));
        PrivateKey privateKey = null;
        try {
            KeyFactory keyFactory = KeyFactory.getInstance(RSA);
            privateKey = keyFactory.generatePrivate(keySpec);
        } catch (NoSuchAlgorithmException | InvalidKeySpecException e) {
            e.printStackTrace();
        }
        return privateKey;
    }
HmacSHA256 method(signature_method = HmacSHA256):

use secret key of your api_key，make the hash operation of preparedStr，then we get the parameter sign.

HmacSHA256 example:

    public static String HmacSHA256_Sign(String preparedStr, String secretKey) {
        String hash = "";
        try {
            Mac sha256_HMAC = Mac.getInstance("HmacSHA256");
            SecretKeySpec secret_key = new SecretKeySpec(secretKey.getBytes(), "HmacSHA256");
            sha256_HMAC.init(secret_key);
            byte[] bytes = sha256_HMAC.doFinal(message.getBytes());
            hash = byteArrayToHexString(bytes);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return hash;
    }
Submit：
After we get the parameter 'sign', put it together with all required parameters of endpoint, then submit as 'application/x-www-form-urlencoded'. As user_info endpoint, we should summit the following parameters:

api_key=6a8d4f1a-b040-4ac4-9bda-534d71f4cb28

sign=e73f3b77895d3df27c79481d878a517edd674e8496ed3051b6e70b6d0b1e47bc

Request Format
All request are GET or POST.

Content-Type:application/x-www-form-urlencoded、timestamp:1567427936729、signature_method:RSA、echostr:3d47056c0bf0429c81afc8c3de7b0f94。

Response Format
Parameter	Type	Description
result	boolean	API return，true/false
error_code	string	return error_code
ts	long	return timestamp
data	object	return body
Error code
REST API code
Error code	Description
00000	return success
10000	Internal error
10001	The required parameters can not be empty
10002	Validation Failed
10003	Invalid parameter
10004	Request too frequent
10005	Secret key does not exist
10006	User does not exist
10007	Invalid signature
10008	Invalid Trading Pair
10009	Price and/or Amount are required for limit order
10010	Price and/or Amount must less than minimum require
10011	Buy at market price, price must be passed
10012	Sell at market price, amount must be passed
10013	Order quantity lower than minimum transaction quantity
10014	Insufficient amount of money in account
10015	Invalid order type
10016	Insufficient account balance
10017	Server Error
10018	Page size should be between 1 and 50
10019	Cancel NO more than 3 orders in one request
10020	Volume < 0.001
10021	Price < 0.01
10022	API Key permission denied, Invalid IP or permissions
10023	Market Order is not supported yet
10024	User cannot trade on this pair
10025	Order has been filled
10026	Order has been cancelld
10027	Order is cancelling
10028	Wrong query time
10029	'from' is not in the query time
10030	'from' do not match the transaction type of inqury
10031	echostr length must be valid and length must be from 30 to 40
10032	The order number does not exist
10033	Failed to create order
10036	customID duplicated
10037	Order has been cancelled or completed
10039	Order timeout cancellation
10066	Please check the chain name
10100	Has no privilege to withdraw
10101	Invalid fee rate to withdraw
10102	Too little to withdraw
10103	Exceed daily limitation of withdraw
10104	Cancel was rejected
10105	Request has been cancelled
10106	None trade time
10107	Start price exception
10108	can not create order
10109	wallet address is not mapping
10110	transfer fee is not mapping
10111	mount > 0
10112	fee is too lower
10113	transfer fee is 0
10114	Incorrect precision of withdrawal quantity
10116	Upgrading in progress, please try again later
10117	Station withdrawal not enabled
10119	Interface upgrade, please use /v2/supplement/withdraw.do
10120	Less than the minimum transaction limit
10121	The order amount exceeds the maximum transaction limit for a single transaction
10122	Price exceeds the upper limit
10123	Price below the lower limit
10600	intercepted by replay attacks filter, check timestamp
10601	Interface closed unavailable
10701	invalid asset code
10702	not allowed deposit
10801	Withdrawal address whitelist verify failed
Common Endpoints
Available trading pairs
curl "https://api.lbkex.com/v2/currencyPairs.do"
Example:

[
  "bcc_eth","etc_btc","dbc_neo","eth_btc",
  "zec_btc","qtum_btc","sc_btc","ven_btc",
  "ven_eth","sc_eth","zec_eth"
]
HTTP Request
GET /v2/currencyPairs.do

Paramters
none

Returns
Parameter	Type	Required	Note
data	object	Yes	pair info
Trading pairs
Acquiring the basic information of all trading pairs

curl "https://api.lbkex.com/v2/accuracy.do"
Example:

   [
        {
          "priceAccuracy": "2",
          "quantityAccuracy": "4",
          "symbol": "pch_usdt"
        }
    ]
HTTP Request
GET /v2/accuracy.do

Parameters
none

Returns
Parameter	Type	Required	Note
minTranQua	string	Yes	Min TranQua
symbol	string	Yes	Trading Pair，eth_btc：Ethereum， zec_btc：ZCash
quantityAccuracy	string	Yes	Quantity Accuracy
priceAccuracy	string	Yes	Price Accuracy
Withdrawal configurations
Not recommended for use, it will be taken down later

Recommended use: Coin information (GET /v2/assetConfigs.do)

curl "https://api.lbkex.com/v2/withdrawConfigs.do"
Example:

    { 
        "amountScale":4,
        "transferAmtScale":4,
        "assetCode":"eth", 
        "canWithDraw":"true", 
        "fee":0.01,
        "type":1, 
        "min":0.01,
        "minTransfer":0.01,
        "chain":1
       }
HTTP Request
GET /v2/withdrawConfigs.do

Parameters
Parameter	Type	Required	Note
assetCode	String	No	Code of the asset
Returns
Parameter	Type	Required	Note
assetCode	string	Yes	Code of token
min	double	Yes	Minimum amount to withdraw for out-exchange
minTransfer	double	Yes	Minimum amount to withdraw for in-exchange
canWithDraw	boolean	Yes	Whether the currency can be withdrawn
fee	double	Yes	Charged fee for withdrawal（amount)
amountScale	int	Yes	amount scale for out-exchange
transferAmtScale	int	Yes	amount scale for in-exchange
type	int	Yes	1:fixed fee，2:rate fee
chain	string	no	chain for usdt:OMNI or ERC20
Coin information
Get coin information (deposit and withdrawal).

curl "https://api.lbkex.com/v2/assetConfigs.do"
Example:

  {
  "result": "true",
  "data": [
    {
      "assetCode": "btc",
      "chainName": "btc",
      "canDraw": true,
      "canStationDraw": true,
      "canDeposit": true,
      "hasMemo": false,
      "assetFee": {
        "type": 1,
        "feeCode": "btc",
        "scale": 4,
        "minAmt": "0.001",
        "feeAmt": "0.0002",
        "feeRate": "0",
        "stationFeeAmt": "0",
        "stationScale": 4,
        "stationMinAmt": "0.0001",
        "minDepositAmt": "0.00001",
        "depositFee": "0"
      }
    },
    {
      "assetCode": "btc",
      "chainName": "trc20",
      "canDraw": true,
      "canStationDraw": true,
      "canDeposit": true,
      "hasMemo": false,
      "assetFee": {
        "type": 1,
        "feeCode": "btc",
        "scale": 4,
        "minAmt": "0.001",
        "feeAmt": "0.0001",
        "feeRate": "0",
        "stationFeeAmt": "0",
        "stationScale": 4,
        "stationMinAmt": "0.0001",
        "minDepositAmt": "0.0001",
        "depositFee": "0"
      }
    }
  ]
}
HTTP Request
GET /v2/assetConfigs.do

Parameters
Parameter	Type	Required	Note
assetCode	string	Yes	Code of token
Returns
Parameter	Type	Required	Note
assetCode	string	Yes	Code of token
chainName	string	Yes	Chain name
canDraw	boolean	Yes	Can withdraw
canStationDraw	boolean	Yes	Can transfer
canDeposit	boolean	Yes	Can Deposit
hasMemo	boolean	Yes	has memo
type	int	Yes	1:fixed fee, 2:rate fee, 3: fixed fee + rate fee
feeCode	string	Yes	fee Code
scale	int	Yes	Withdrawal quantity accuracy
minAmt	string	Yes	Minimum withdrawal quantity
feeAmt	string	Yes	Number of fees
feeRate	string	Yes	fee rate
stationFeeAmt	string	Yes	Number of transfer fees
stationScale	int	Yes	Transfer quantity accuracy
stationMinAmt	string	Yes	Minimum transfer quantity
minDepositAmt	string	Yes	Minimum deposit quantity
depositFee	string	Yes	Number of deposit fees
Get timestamp
curl "https://api.lbkex.com/v2/timestamp.do"
Example:

  {"timestamp":1568269063244}
HTTP Request
GET /v2/timestamp.do

Parameters
none

Returns
Parameter	Type	Required	Note
data	long	Yes	timestamp
Wallet Endpoints
System status
Get system status.

return example:

  {"status":"1"}
HTTP request
POST /v2/supplement/system_status.do

request parameters
This interface does not accept any parameters

Return parameters
parameter name	parameter type	required	description
status	string	yes	system status: 0 system maintenance, 1 normal
Get all coins information
Get all the currency information for the user (LBK supports deposit and withdrawal operations).

return example:

[{
    "usableAmt": "110.00869",
    "assetAmt": "110.02869",
    "networkList": [
      {
        "isDefault": true,
        "withdrawFeeRate": "10",
        "name": "btc",
        "withdrawMin": 0.01,
        "minLimit": 0.0001,
        "minDeposit": 0.001,
        "feeAssetCode": "usdt",
        "withdrawFee": "1",
        "type": 3,
        "coin": "btc",
        "network": "btc"
      },
      {
        "isDefault": false,
        "withdrawFeeRate": "",
        "name": "btctron",
        "withdrawMin": 0.0001,
        "minLimit": 0.02,
        "minDeposit": 0.0124,
        "feeAssetCode": "btc",
        "withdrawFee": "0.01",
        "type": 1,
        "coin": "btc",
        "network": "trx"
      }
    ],
    "freezeAmt": "0.02",
    "coin": "btc"
}]
HTTP request
POST /v2/supplement/user_info.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
Return parameters
Parameter name	Parameter type	Required	Description
coin	string	is	asset name
assetAmt	string	is	asset balance
usableAmt	string	is	usableAmt
freezeAmt	string	Yes	FreezeAsset
networkList	[]	is	Multi-chain information
isDefault	boolean	is	default chain
withdrawFeeRate	string	yes	withdrawal rate
name	string	is	chain name
withdrawMin	BigDecimal	Yes	Single Minimum Withdrawal
minLimit	BigDecimal	Yes	Minimum single transfer in the station
minDeposit	BigDecimal	Yes	Minimum Deposit
feeAssetCode	string	Yes	Delisted currency withdrawal fee currency
withdrawFee	string	Yes	Withdrawal Fee
type	int	is	fee type, 1 fixed, 2 percent, 3 fixed plus percent
coin	string	is	currency
network	string	is	mainnet
Withdrawal
User withdrawal

return example:

{
  "fee": 2,
  "withdrawId": 93182
}
HTTP request
POST /v2/supplement/withdraw.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
address	string	is	withdrawal address, when type=1, it is the transfer account
networkName	string	No	Chain name, get it through the Get All Coin Information interface
coin	string	is	currency
amount	string	is	withdrawal amount
memo	string	No	memo: memo word of bts and dct
mark	string	No	Withdrawal Notes
fee	string	is	fee
name	string	No	Remarks of the address. After filling in this parameter, it will be added to the withdrawal address book of the currency.
withdrawOrderId	string	No	Custom withdrawal id
type	string	No	type=1 is for intra-site transfer
Return parameters
Parameter name	Parameter type	Required	Description
fee	BigDecimal	Yes	Fees
withdrawId	int	is	withdrawal id
Get recharge history
User access to recharge history

return example:

[
  {
    "insertTime": 1644378926000,
    "amount": 443,
    "address": "QiEik5W3szxqtjJnzp14apfrY7McUdX9sa",
    "networkName": "lbk20",
    "txId": "0x4baf730c242fe6d85559edb40399daaf8dca16255382a5ce36934f0ff964a776",
    "coin": "lbk",
    "status": "2"
  }
]
HTTP request
POST /v2/supplement/deposit_history.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
status	string	No	Recharge status: ("1","Applying"),("2","Recharge successful"),("3","Recharge failed"),("4","Already Cancel"), ("5", "Transfer")
coin	string	no	currency
startTime	string	No	Start time, timestamp in milliseconds, default 90 days ago
endTime	string	no	end time, timestamp in milliseconds, default day
Return parameters
Parameter name	Parameter type	Required	Description
insertTime	timestamp	Yes	InsertTime
amount	BigDecimal	Yes	Amount of deposit
address	String	is	quantity
networkName	string	no	chain name
txId	string	is	transaction hash
coin	string	is	currency
status	string	is	status
Get withdrawal history
User's coin withdrawal history

return example:

 [
  {
    "amount": 234,//amount
    "coid": "lbk",//currency
    "address": "34252342",//Withdrawal address
    "withdrawOrderId": "werqwerq123425353",//Withdraw customer custom id
    "fee": 2,//fee
    "networkName": "lbk30",//chain name
    "transferType": "Digital Asset Withdrawal",//Withdrawal type
    "txId": "",
    "feeAssetCode": "",//The currency of the fee, the currency of the delisting will be displayed
    "id": 93182,//Reminder id
    "applyTime": 1644476930000,//time
    "status": "1"//("1","Applying"),("2","Cancelled"),("3","Withdrawal failed"),("4","Withdrawal completed ")
  }
]
HTTP request
POST /v2/supplement/withdraws.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
status	string	No	status: ("1","Applying"),("2","Cancelled"),("3","Withdrawal failed"),("4","Withdrawal complete")
coin	string	no	currency
withdrawOrderId	string	No	Custom withdrawal id
startTime	string	No	Start time, timestamp in milliseconds, default 90 days ago
endTime	string	no	end time, timestamp in milliseconds, default day
The user obtains the deposit address
The user obtains the recharge address

return example:

{
  "address": "0x1ccbf66250c9a665710e56e00b3a1502495dd269", //address
  "memo": null,
  "coin": "lbk" //currency
}
HTTP request
POST /v2/supplement/get_deposit_address.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
networkName	string	no	chain name
coin	string	is	currency
List asset details
Listing Asset Details

return example:

{
  "htmoon": {
    "minWithdrawAmount": 0,
    "stationDrawStatus": true, //Whether it can be transferred within the station
    "depositStatus": false, //Whether it can be recharged
    "withdrawFee": 0, //withdrawal fee
    "withdrawStatus": false //Whether it can be withdrawn
  },
  "phx": {
    "minWithdrawAmount": 0,
    "stationDrawStatus": true,
    "depositStatus": true,
    "withdrawFee": 0,
    "withdrawStatus": true
  }
}
HTTP request
POST /v2/supplement/asset_detail.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
coin	string	no	currency
Transaction fee rate query
User transaction fee rate query

return example:

[
  {
    "symbol": "lbk_usdt",
    "makerCommission": "0.10",
    "takerCommission": "10.00"
  }
]
HTTP request
POST /v2/supplement/customer_trade_fee.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
category	string	No	Trading pair, eg: lbk_usdt
Query user API Key permissions
Query user API Key permissions

return example:

{
  "enableSpotTrading": true, //trading
  "createTime": 1643091005000,
  "enableReading": true, //read only
  "ipRestrict": true, //whether to restrict ip
  "enableWithdrawals": true //Withdrawal
}
HTTP request
POST /v2/supplement/api_Restrictions.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	string	is	The api_key applied by the user
sign	string	is	signature of request parameter
Market Data Endpoints
Test server connectivity
Test whether the Rest API can be connected.

return example:

{}
HTTP request
POST /v2/supplement/system_ping.do

request parameters
This interface does not accept any parameters

Depth information
Get depth information

return example:

{
  "asks":[
    [5370.4, 0.32],
    [5369.5, 0.28],
    [5369.24, 0.05],
    [5368.2, 0.079],
    [5367.9, 0.023]
  ],
  "bids":[
    [5367.24, 0.32],
    [5367.16, 1.31],
    [5366.18, 0.56],
    [5366.03, 1.42],
    [5365.77, 2.64]
  ]
}
HTTP request
GET /v2/depth.do

request parameters
Parameter name	Parameter type	Required	Description
symbol	String	Yes	Trading Pair.
size	Integer	Yes	The count of returned items.(1-200)
returns
Parameter name	Description
asks	Depth of asks (Sellers')
bids	Depth of bids (Buyers')
Get the latest price of the trading pair
Get the latest price of a trading pair

return example:

[
  {
    "symbol": "ht_usdt",
    "price": "97.0000"
  },
  {
    "symbol": "mcc_usdt",
    "price": "10.00"
  },
  {
    "symbol": "un_eth",
    "price": "0.02"
  }
]
HTTP request
GET /v2/supplement/ticker/price.do

request parameters
Parameter name	Parameter type	Required	Description
symbol	string	No	Pair
Symbol Order Book Ticker
The current optimal pending order

return example:

{
  "symbol": "lbk_usdt",
  "askPrice": "0.011",
  "askQty": "8",
  "bidQty": "1659",
  "bidPrice": "0.01"
}
HTTP request
GET /v2/supplement/ticker/bookTicker.do

request parameters
Parameter name	Parameter type	Required	Description
symbol	string	is	coin pair
24hr Ticker
GET the LBank coin quote data, excluding Leveraged Tokens trading pairs (get Leveraged Tokens trading pairs GET /v2/etfTicker/24hr.do)

   curl "https://api.lbkex.com/v2/ticker/24hr.do?symbol=btc_usdt"
Example:

[
  {
    "symbol": "btc_usdt",
    "ticker": {
      "high": "34161.64",
      "vol": "8925.492",
      "low": "32659.88",
      "change": "-2.67",
      "turnover": "296494557.82",
      "latest": "33220.36"
    },
    "timestamp": 1626170107873
  }
]
HTTP Request
GET /v2/ticker/24hr.do

Parameters
Parameter	Type	Required	Note
symbol	String	Yes	Pair
Such as: eth_btc、zec_btc、 all
Returns
Parameter	Note
vol	24 hr trading volume
high	24 hr highest price
low	24 hr lowest price
change	Fluctuation (%) in 24 hr
turnover	Total Turn over in 24 hr
latest	Latest Price
timestamp	Timestamp of latest transaction
Leveraged Tokens 24hr Ticker
Get LBank Leveraged Tokens market data

   curl "https://api.lbkex.com/v2/etfTicker/24hr.do?symbol=btc3l_usdt"
Example:

[
  {
    symbol: "btc3l_usdt",
    ticker: {
      high: "0.111848",
      vol: "4460664.1434",
      low: "0.098938",
      change: "-3.11",
      turnover: "463226.2868",
      latest: "0.104219"
    },
    timestamp: 1668648723813
  }
]
HTTP Request
GET /v2/etfTicker/24hr.do

Parameters
Parameter	Type	Required	Note
symbol	String	Yes	Pair
Such as: btc3l_usdt、all
Returns
Parameter	Note
vol	24 hr trading volume
high	24 hr highest price
low	24 hr lowest price
change	Fluctuation (%) in 24 hr
turnover	Total Turn over in 24 hr
latest	Latest Price
timestamp	Timestamp of latest transaction
Recent transactions list
List of recent transactions

return example:

[
  {
    "quoteQty": 0.022,
    "price": 0.011,
    "qty": 2,
    "id": "10e71fd6-99ab-425e-939d-1447dfbe594e",
    "time": 1644396172793,
    "isBuyerMaker": true
  },
  {
    "quoteQty": 0.67315789,
    "price": 0.67315789473,
    "qty": 1,
    "id": "46a1e423-be95-4ded-8887-a489d38577a8",
    "time": 1644386190138,
    "isBuyerMaker": true
  }
]
HTTP request
GET /v2/supplement/trades.do

request parameters
Parameter name	Parameter type	Required	Description
symbol	string	is	coin pair
size	string	is	Returns size
time	string	No	Returns size pieces of data after the timestamp, if empty, returns the latest size pieces of data
Query K Bar Data
   curl "https://api.lbkex.com/v2/kline.do"
Example:

[
  [
    1482311500,
    5423.23,
    5472.80,
    5516.09,
    5462,
    234.3250
  ],
  [
    1482311400,
    5432.52,
    5459.87,
    5414.30,
    5428.23,
    213.7329
  ]
]
HTTP Request
GET /v2/kline.do

Parameters
Name	Type	Required	Description
symbol	String	Yes	Trading Pair eth_btc
size	Integer	Yes	Count of the bars (1-2000)
type	String	Yes	minute1：1 minute
minute5：5 minutes
minute15：15minutes
minute30：30 minutes
hour1：1 hour
hour4：4 hours
hour8：8 hours
hour12：12 hours
day1：1 day
week1：1 week
month1：1 month
time	String	Yes	Timestamp (of Seconds)
Returns
Parameter	Note
1482311500	Timestamp
5423.23	Open Price
5472.80	Highest Price
5516.09	Lowest Price
5462	Close Price
234.3250	Trading Volume
Spot Trading Endpoints
Test order
test order

return example:

{
  "order_id":"12074652-d827-4f8d-8f52-92a005c6ce53",
  "symbol": "lbk_usdt",
  "custom_id": "12074652-d827"
}
HTTP request
POST /v2/supplement/create_order_test.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	String	is	the api_key applied by the user
symbol	String	Yes	Transaction pair eth_btc: Ethereum; zec_btc: Zerocoin
type	String	yes	The type of the order, including buy, sell, buy_market, sell_market, buy_maker, sell_maker, buy_ioc, sell_ioc, buy_fok, sell_fok
price	String	Reference description	Order price Buy and sell orders: greater than or equal to 0
amount	String	Reference description	Amount of transactions Sell order and sell order: BTC amount is greater than or equal to 0.001
sign	String	is	signature of request parameter
custom_id	String	No	User-defined ID, do not repeat by yourself
window	Long	No	Expiration time of order, milliseconds, automatic cancellation of order after timeout (considering the public network time, it is recommended not to exceed 5s)
Place an order
place an order

return example:

{
  "order_id":"12074652-d827-4f8d-8f52-92a005c6ce53",
  "symbol": "lbk_usdt",
  "custom_id": "12074652-d827"
}
HTTP request
POST /v2/supplement/create_order.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	String	is	the api_key applied by the user
symbol	String	Yes	Transaction pair eth_btc: Ethereum; zec_btc: Zerocoin
type	String	yes	The type of the order, including buy, sell, buy_market, sell_market, buy_maker, sell_maker, buy_ioc, sell_ioc, buy_fok, sell_fok
price	String	Reference description	Order price Buy and sell orders: greater than or equal to 0
amount	String	Reference description	Amount of transactions Sell order and sell order: BTC amount is greater than or equal to 0.001
sign	String	is	signature of request parameter
custom_id	String	No	User-defined ID, do not repeat by yourself
window	Long	No	Expiration time of order, milliseconds, automatic cancellation of order after timeout (considering the public network time, it is recommended not to exceed 5s)
buy, sell

limit order

buy_market, sell_market

market order
buy_market: price must be passed, quoted asset quantity;
sell_market: amount must be passed, basic asset quantity;

buy_maker

If the order price is greater than or equal to the lowest selling price in the market, the order will be rejected;
If the order price is less than the lowest selling price in the market, the order will be accepted.

sell_maker

If the order price is less than or equal to the highest buy price in the market, the order will be rejected;
If the order price is greater than the highest buy price in the market, the order will be accepted.

buy_ioc, sell_ioc

Immediate or Cancel order, IOC is an order to buy or sell that attempts to execute all or part immediately and then cancels any unfilled portion of the order

buy_fok, sell_fok

Fill or Kill order, FOK is a type of time-in-force designation used in trading that instructs a brokerage to execute a transaction immediately and completely or not at all.

window

Time synchronization security All signature interfaces need to pass timestamp parameters. When receiving a request, the server will determine the timestamp in the request. If the request is sent earlier than 5000 ms, the request will be considered invalid. This time window value can be customized by sending the optional parameter window. In addition, if the server calculates that the client timestamp is more than one second in the 'future' of the server's time, the request will also be rejected. The state of the Internet is not 100% reliable and cannot be completely relied upon, so the delay between your application and the LBank server will be jitter. This is the purpose of setting the window. If you are engaged in high-frequency trading and have high requirements on the trading timeliness, you can flexibly set the window to meet your requirements.

Cancel order
Cancel order

return example:

{
  "symbol": "lbk_usdt",
  "origClientOrderId": "10e71fd6-99ab-425e-939d-1447dfbe594e",
  "orderId": "46a1e423-be95-4ded-8887-a489d38577a8",
  "price": "2.00000000",
  "origQty": "1.00000000",
  "executedQty": "0.00000000",
  "status": 3,
  "timeInForce": "GTC",
  "tradeType": "buy"
}
HTTP request
POST /v2/supplement/cancel_order.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	String	is	the api_key applied by the user
sign	String	is	signature of request parameter
symbol	string	is	coin pair
orderId	string	no	orderid, User-defined id and order id must be passed
origClientOrderId	string	No	User-defined id and order id must be passed
Cancel all pending orders for a single trading pair
Cancel all pending orders for a single trading pair

return example:

[
  {
    "symbol": "lbk_usdt",
    "origClientOrderId": "10e71fd6-99ab-425e-939d-1447dfbe594e",
    "orderId": "12074652-d827-4f8d-8f52-92a005c6ce53",
    "price": "2.00000000",
    "origQty": "1.00000000",
    "executedQty": "0.00000000",
    "status": 3,
    "tradeType": "buy"
  },
  {
    "symbol": "lbk_usdt",
    "origClientOrderId": "5ca3ced8-74ea-46eb-9365-ad78c2c6f606",
    "orderId": "46a1e423-be95-4ded-8887-a489d38577a8",
    "price": "2.00000000",
    "origQty": "1.00000000",
    "executedQty": "0.00000000",
    "status": 3,
    "tradeType": "buy"
  }
]
HTTP request
POST /v2/supplement/cancel_order_by_symbol.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	String	is	the api_key applied by the user
sign	String	is	signature of request parameter
symbol	string	is	coin pair
Query order
checking order

return example:

{
  "symbol": "lbk_usdt", // trading pair
  "orderId": "10e71fd6-99ab-425e-939d-1447dfbe594e", // order ID of the system
  "clientOrderId": "46a1e423-be95-4ded-8887-a489d38577a8", // ID set by the client
  "price": "0.1", // order price
  "origQty": "1.0", // The original order quantity set by the user
  "executedQty": "0.0", // number of orders to trade
  "cummulativeQuoteQty": "0.0", // Cumulative transaction amount
  "status": "3", // Order status -1: Cancelled 0: Unfilled 1: Partially filled 2: Completely filled 3: Partially filled has been cancelled 4: Cancellation is being processed
  "type": "buy", // order type, such as market order, spot order, etc.
  "time": 1499827319559, // order time
  "updateTime": 1499827319559, // last update time
  "origQuoteOrderQty": "0.000000" // original transaction amount
}
HTTP request
POST /v2/supplement/orders_info.do

request parameters
Parameter name	Parameter type	Required	Description
api_key	String	is	the api_key applied by the user
sign	String	is	signature of request parameter
symbol	string	is	coin pair
orderId	string	no	orderid, User-defined id and order id must be passed
origClientOrderId	string	No	User-defined id and order id must be passed
Current pending order
current pending order

return example:

[
  {
    "symbol": "lbk_usdt", // trading pair
    "orderId": "10e71fd6-99ab-425e-939d-1447dfbe594e", // order ID of the system
    "clientOrderId": "46a1e423-be95-4ded-8887-a489d38577a8", // ID set by the client
    "price": "0.1", // order price
    "origQty": "1.0", // The original order quantity set by the user
    "executedQty": "0.0", // number of orders to trade
    "cummulativeQuoteQty": "0.0", // Cumulative transaction amount
    "status": "3", // Order status -1: Cancelled 0: Unfilled 1: Partially filled 2: Completely filled 3: Partially filled has been cancelled 4: Cancellation is being processed
    "type": "buy", // order type, such as market order, spot order, etc.
    "time": 1499827319559, // order time
    "updateTime": 1499827319559, // last update time
    "origQuoteOrderQty": "0.000000" // original transaction amount
  }
]
HTTP request
POST /v2/supplement/orders_info_no_deal.do

request parameters
Parameter name	Parameter type	Required	Description
sign	string	is	signature of request parameter
api_key	string	is	The api_key applied by the user
symbol	string	Yes	Transaction pair eth_btc: Ethereum; zec_btc: Zerocoin
current_page	string	is	current page number
page_length	string	Yes	Number of data items per page (not less than 1, not more than 200)
Query all orders
Check all orders(The default query is for orders placed within 24 hours. When the status is empty, the default query is for cancelled and completely filled orders)

return example:

[
  {
    "symbol": "lbk_usdt", // trading pair
    "orderId": "5ca3ced8-74ea-46eb-9365-ad78c2c6f606", // order ID of the system
    "clientOrderId": "10e71fd6-99ab-425e-939d-1447dfbe594e", // ID set by the client
    "price": "0.1", // order price
    "origQty": "1.0", // The original order quantity set by the user
    "executedQty": "0.0", // number of orders to trade
    "cummulativeQuoteQty": "0.0", // Cumulative transaction amount
    "status": "3", // Order status -1: Cancelled 0: Unfilled 1: Partially filled 2: Completely filled 3: Partially filled has been cancelled 4: Cancellation is being processed
    "type": "buy", // order type, such as market order, spot order, etc.
    "time": 1499827319559, // order time
    "updateTime": 1499827319559, // last update time
    "origQuoteOrderQty": "0.000000" // original transaction amount
  }
]
HTTP request
POST /v2/supplement/orders_info_history.do

request parameters
Parameter name	Parameter type	Required	Description
sign	string	is	signature of request parameter
api_key	string	is	The api_key applied by the user
symbol	string	Yes	Transaction pair eth_btc: Ethereum; zec_btc: Zerocoin
current_page	string	is	current page number
page_length	string	Yes	Number of data items per page (not less than 1, not more than 200)
status	string	No	Order Status
Account information
account information

return example:

  {
  "canTrade": true,
  "canWithdraw": true,
  "canDeposit": true,
  "balances": [
    {
      "asset": "BTC",
      "free": "4723846.89208129",
      "locked": "0.00000000"
    },
    {
      "asset": "LTC",
      "free": "4763368.68006011",
      "locked": "0.00000000"
    }
  ]
  }
HTTP request
POST /v2/supplement/user_info_account.do

request parameters
Parameter name	Parameter type	Required	Description
sign	string	is	signature of request parameter
api_key	string	is	The api_key applied by the user
Historical transaction details
Historical transaction details

return example:

[
  {
    "symbol": "lbk_usdt", // trading pair
    "id": "46a1e423-be95-4ded-8887-a489d38577a8", // trade ID
    "orderId": "deec9d13-bab3-411d-b68e-98a83c34c570", // order ID
    "price": "4.00000100", // transaction price
    "qty": "12.00000000", // volume
    "quoteQty": "48.000012", // transaction amount
    "commission": "10.10000000", // transaction fee amount
    "time": 1499865549590, // transaction time
    "isBuyer": true, // is the buyer
    "isMaker": false // whether it is a pending order
  }
]
HTTP request
POST /v2/supplement/transaction_history.do

request parameters
Parameter name	Parameter type	Required	Description
sign	string	is	signature of request parameter
api_key	string	is	The api_key applied by the user
symbol	string	Yes	Transaction pair eth_btc, btc_usdt, eth_usdt;
startTime	string	No	Start time yyyy-MM-dd or yyyy-MM-dd HH:mm:ss (UTC+8), the maximum value is today, the default is yesterday
endTime	string	No	End time yyyy-MM-dd or yyyy-MM-dd HH:mm:ss (UTC+8), the maximum value is today, the default is today
The query window for the start and end time is up to 2 days
fromId	string	No	The starting transaction ID of the query
limit	string	No	Number of queries, default 100, [1-100]
WebSocket API (Market Data)
Request & subscription instruction
URL: wss://www.lbkex.net/ws/V2/

Hearbeat（ping/pong）

To prevent botch links and reduce server load, server will send a "Ping" message periodically to client connections. When client recieves the "Ping" message, it should response immediately. If a client responds nothing to macth the "Ping" message in one minute, server will close the connection to the client. Meanwhile client can also send a "Ping" message to server to check whether the connection is working. After server recieves the "Ping" message, it should response with a "Pong" message to match the "Ping". Eg:

 ping { "action":"ping", "ping":"0ca8f854-7ba7-4341-9d86-d3327e52804e" }
pong { "action":"pong", "pong":"0ca8f854-7ba7-4341-9d86-d3327e52804e" }


where the value of the key "pong" in the "Pong" message should equal to the value of the key "ping" in correspond "Ping" message.
Subscription/Unsubscription

Each subscribed data should include one subscribed field at least which specifies the data type of the subscription. Data types that can be subscribed now includes：kbar, tick, depth, trade. Each subscription needs a pair field to specify the trading pair subscribed, which is concatenated with a underline (_). After successful subscription Websocket client receives the updated message sent from server as soon as the subscribed data is updated.

Request data One-time request data is supported by Websocket server.

1.One-time request to get k-line needs extra parameters defined in following

Parameters	Parameters Type	Required	Description
start	String	fasle	Start time. Accept 2 formats, such as 2018-08-03T17:32:00 (beijing time), another timestamp, such as 1533288720 (Accurate to second)
end	String	false	Deadline
size	String	false	Number of kbars
One-time request to get trade records needs extra parameters defined in following
Parameters	Parameters Type	Required	Description
size	String	Y	Number of trades
     # Get k-line data Request
    {
        "action":"request",
        "request":"kbar",
        "kbar":"5min",
        "pair":"eth_btc",
        "start":"2018-08-03T17:32:00",
        "end":"2018-08-05T17:32:00",
        "size":"576"
    }
     # Get depth data Request
    {
        "action":"request",
        "request":"depth",
        "depth":"100",
        "pair":"eth_btc"
    }
     # Get transaction data Request
    {
        "action":"request",
        "request":"trade",
        "pair":"eth_btc",
        "size":"100"
    }
     # Get market data Request
    {
        "action":"request",
        "request":"tick",
        "pair":"eth_btc"
    }
Subscription of K-line Data
    {
        "action":"subscribe",
        "subscribe":"kbar",
        "kbar":"5min",
        "pair":"eth_btc"
    }
Example:

 {
        "kbar":{
            "a":64.32991311,
            "c":0.02590293,
            "t":"2019-06-28T17:45:00.000",
            "v":2481.1912,
            "h":0.02601247,
            "slot":"5min",
            "l":0.02587925,
            "n":272,
            "o":0.02595196
        },
        "type":"kbar",
        "pair":"eth_btc",
        "SERVER":"V2",
        "TS":"2019-06-28T17:49:22.722"
    }
Parameters
Parameter	Parameter Type	Required	Description
action	String	Y	Action requested: subscribe or unsubscribe
subscribe	String	Y	kbar
kbar	String	Y	To subscribe to k-line types
1min: 1 minute
5min: 5 minutes
15min: 15 minutes
30min: 30 minutes
1hr: 1 hour
4hr: 4 hours
day: 1 day
week: 1 week
month: 1 month
year: 1 year
pair	String	Y	Trading pair:eth_btc
Return
Parameters	Parameters Type	Description
t	String	K-line updates the time
o	BigDecimal	Open price
h	BigDecimal	Highest price
l	BigDecimal	Lowest price
c	BigDecimal	Close price
v	BigDecimal	Trading volume
a	BigDecimal	Aggregated turnover (summation of price times volume for each trade)
n	BigDecimal	Number of trades
slot	String	K-line type
Market Depth
    {
        "action":"subscribe",
        "subscribe":"depth",
        "depth":"100",
        "pair":"eth_btc"
    }
Example:

 {
         "depth":{
             "asks":[
                 [
                     0.0252,
                     0.5833
                 ],
                 [
                     0.025215,
                     4.377
                 ],
                 ...
             ],
             "bids":[
                 [
                     0.025135,
                     3.962
                 ],
                 [
                     0.025134,
                     3.46
                 ],
                 ...
             ]
         },
         "count":100,
         "type":"depth",
         "pair":"eth_btc",
         "SERVER":"V2",
         "TS":"2019-06-28T17:49:22.722"
     }
Parameters
Parameters	Parameters Type	Required	Description
action	String	Y	Type of action requested:subscribe,unsubscribe
subscribe	String	Y	depth
depth	String	Y	Pro-choise:10/50/100
pair	String	Y	Trading pair:eth_btc
Return
Parameters	Parameters Type	Description
asks	List	Selling side: list.get(0): delegated price, list.get(1): delegated quantity
bids	List	Buying side
//: # ()

//: # ()

//: # ()

//: # ()

//: # ()

Trade record
    {
        "action":"subscribe",
        "subscribe":"trade",
        "pair":"eth_btc"
    }
Example:

 {
         "trade":{
             "volume":6.3607,
             "amount":77148.9303,
             "price":12129,
             "direction":"sell",
             "TS":"2019-06-28T19:55:49.460"
         },
         "type":"trade",
         "pair":"btc_usdt",
         "SERVER":"V2",
         "TS":"2019-06-28T19:55:49.466"
     }
Parameters
Parameters	Parameters Type	Required	Description
action	String	Y	Action requested: subscribe or unsubscribe
subscribe	String	Y	trade
pair	String	Y	Trading pair:eth_btc
Return
Parameters	Parameters Type	Description
amount	String	Recent trading volume
price	Integer	Trade price
volumePrice	String	Aggregated turnover
direction	String	sell,buy
TS	String	Deal time
Market
    {
        "action":"subscribe",
        "subscribe":"tick",
        "pair":"eth_btc"
    }
Example:

 {
         "tick":{
             "to_cny":76643.5,
             "high":0.02719761,
             "vol":497529.7686,
             "low":0.02603071,
             "change":2.54,
             "usd":299.12,
             "to_usd":11083.66,
             "dir":"sell",
             "turnover":13224.0186,
             "latest":0.02698749,
             "cny":2068.41
         },
         "type":"tick",
         "pair":"eth_btc",
         "SERVER":"V2",
         "TS":"2019-07-01T11:33:55.188"
     }
Parameters
Parameters	Parameters Type	Required	Description
action	String	Y	Action requested:subscribe,unsubscribe
subscribe	String	Y	tick
pair	String	Y	Trading pair:eth_btc
Return
Parameters	Parameters Type	Description
high	BigDecimal	Highest price in last 24 hours
low	BigDecimal	Lowest price in last 24 hours
latest	BigDecimal	Lastest traded price
vol	BigDecimal	Trading volume
turnover	BigDecimal	Aggregated turnover (summation of price times volume for each trade)
to_cny	BigDecimal	Such as eth_btc, convert btc into cny
to_usd	BigDecimal	Such as eth_btc, convert btc into usd
cny	BigDecimal	Such as eth_btc, convert eth into cny
usd	BigDecimal	Such as eth_btc, convert eth into usd
dir	String	sell, buy
change	BigDecimal	Price limit in last 24 hours
WebSocket API（Asset & Order）
Create subscribeKey
The key is valid in 60 minutes from creation.

curl "https://api.lbkex.com/v2/subscribe/get_key.do"
Example:

 {
    "key":"9301ef1ca6cafbef2df4a1430dc8b53879ea68c595a142eac311d8d590fbd60a"
  }
HTTP Request
POST /v2/subscribe/get_key.do

Parameters
Parameter	Type	Required	Note
api_key	string	Yes	User's api_key
sign	string	Yes	signature of the request
Response
Parameter	Type	Required	Note
data	string	Yes	subscribeKey
Extend the validity of subscribeKey
The key is valid in 60 minutes from this call.

curl "https://api.lbkex.com/v2/subscribe/refresh_key.do"
Example:

{"result":"true"}
HTTP Request
POST /v2/subscribe/refresh_key.do

Parameters
Parameter	Type	Required	Description
api_key	String	Y	API key requested by user
sign	String	Y	Signature of parameter in request
subscribeKey	String	Y	subscribeKey
Response
Parameter	Type	Required	Description
result	boolean	Yes	true or false
Close subscribeKey
Close the data stream for an account.

curl "https://api.lbkex.com/v2/subscribe/destroy_key.do"
Example:

{"result":"true"}
HTTP Request
POST /v2/subscribe/destroy_key.do

Parameters
Parameter	Type	Required	Description
api_key	String	Y	API key requested by user
sign	String	Y	Signature of parameter in request
subscribeKey	String	Y	subscribeKey
Response
Parameter	Type	Required	Description
result	boolean	Yes	true or false
Update subscribed orders
Such events will be pushed when there are new orders created, new orders dealed or new status changes of the account.

    {
      "action": "subscribe",
      "subscribe": "orderUpdate",
      "subscribeKey": "24d87a4xxxxxd04b78713f42643xxxxf4b6f6378xxxxx35836260",
      "pair": "all",
    }
Example:

 {
      "orderUpdate":{
          "accAmt": "0.003",
          "amount":"0.003",
          "avgPrice": "0.02455211",
          "symbol":"eth_btc",
          "type":"buy",
          "orderAmt": "0.003",
          "orderStatus":2,
          "orderPrice": "0.02455211",
          "price":"0.02455211",
          "role":"maker",
          "remainAmt":"0",
          "updateTime":1561704577786,
          "uuid":"d0db191d-xxxxx-4418-xxxxx-fbb1xxxx2ea9",
          "txUuid":"da88f354d5xxxxxxa12128aa5bdcb3",
          "volumePrice":"0.00007365633"
      },
      "pair":"eth_btc", 
      "type":"orderUpdate",
      "SERVER":"V2",
      "TS":"2019-06-28T14:49:37.816"
  }
Parameters
Parameters	Parameters Type	Required	Description
action	String	Y	Action requested: subscribe
subscribe	String	Y	orderUpdate
subscribeKey	String	Y	Obtained through the REST interface of the /v2/subscribe/refresh_key.do
pair	String	Y	Trading pair :eth_btc. Support matching all: all
Return
Parameters	Parameters Type	Description
uuid	String	Order ID
customerID	String	Order customer ID
symbol	String	Trading pair
type	String	buy or sell
txUuid	String	Trading record ID
amount	String	Trading volume
volumePrice	String	Aggregated trading value
role	Long	maker,taker
price	String	Last price(When the order status is' 1 'or' 2 ' ，it is the transaction price, and the others are the Delegat price)
orderPrice	String	Order price
orderAmt	String	Order amount
avgPrice	String	Average strike price
accAmt	String	Accumulative amount
remainAmt	String	Remaining amount(sell order it's remaining amount, buy order it's remaining trading value)
orderStatus	Integer	Order status
-1：Withdrawn
0：Unsettled
1： Partial sale
2：Close the deal
4：Withdrawing
updateTime	Long	Updating time of order
Update subscribed asset
Such events will be pushed when the balance of assets under the account changes (increase, deduction, available freeze, freeze release).

    {
      "action": "subscribe",
      "subscribe": "assetUpdate",
      "subscribeKey": "24d87a4xxxxxd04b78713f42643xxxxf4b6f6378xxxxx35836260"
    }
Example:

 {
     "data": {
         "asset": "114548.31881315",
         "assetCode": "usdt",
         "free": "97430.6739041",
         "freeze": "17117.64490905",
         "time": 1627300043270,
         "type": "ORDER_CREATE"
     },
     "SERVER": "V2",
     "type": "assetUpdate",
     "TS": "2021-07-26T19:48:03.548"
 }
Parameters
Parameters	Parameters Type	Required	Description
action	String	Y	Action requested: subscribe
subscribe	String	Y	assetUpdate
subscribeKey	String	Y	Obtained through the REST interface of the /v2/subscribe/refresh_key.do
Return
Parameters	Parameters Type	Description
asset	String	Total balance of the asset
assetCode	String	Asset Code
free	String	Available balance of the asset
freeze	String	Frozen balance of the asset
time	Long	Update time
type	String	Update type
type Update type：

Update type	Description
DEPOSIT	Deposit
WITHDRAW	Withdraw
ORDER_CREATE	Order create
ORDER_DEAL	Order deal
ORDER_CANCEL	Order cancel