#!/usr/bin/env python3
"""
Test centrifuge-python connection directly
"""
import asyncio
from centrifuge import Client

async def test_centrifuge():
    """Test direct centrifuge connection to Ramzinex"""
    print("Testing direct centrifuge connection...")
    
    try:
        client = Client(
            address='wss://websocket.ramzinex.com/websocket',
            name="test-client"
        )
        
        def on_connect(event):
            print(f"✅ Connected: {event}")
        
        def on_disconnect(event):
            print(f"❌ Disconnected: {event}")
        
        def on_error(event):
            print(f"❌ Error: {event}")
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect  
        client.on_error = on_error
        
        print("Attempting connection...")
        await client.connect()
        
        print("Waiting 5 seconds...")
        await asyncio.sleep(5)
        
        # Test subscription
        subscription = client.new_subscription('orderbook:432')
        
        def on_sub_success(event):
            print(f"✅ Subscription success: {event}")
        
        def on_sub_error(event):
            print(f"❌ Subscription error: {event}")
        
        def on_publish(event):
            print(f"📊 Data received: {type(event.data)} - {str(event.data)[:100]}...")
        
        subscription.on_subscribe_success = on_sub_success
        subscription.on_subscribe_error = on_sub_error  
        subscription.on_publish = on_publish
        
        print("Subscribing to orderbook:432...")
        await subscription.subscribe()
        
        print("Waiting for data (10 seconds)...")
        await asyncio.sleep(10)
        
        await client.disconnect()
        print("✅ Test completed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_centrifuge())