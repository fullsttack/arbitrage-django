#!/usr/bin/env python3
"""
Test subscription API
"""
import asyncio
from centrifuge import Client

async def test_subscription():
    """Test subscription methods"""
    
    client = Client(
        address='wss://websocket.ramzinex.com/websocket',
        name="test-sub"
    )
    
    def on_connect(event):
        print(f"Connected: {event}")
    
    client.on_connect = on_connect
    
    try:
        await client.connect()
        await asyncio.sleep(1)
        
        # Create subscription
        sub = client.new_subscription('orderbook:432')
        print(f"Subscription created: {sub}")
        print(f"Subscription dir: {[x for x in dir(sub) if not x.startswith('_')]}")
        
        # Check available methods
        print(f"Has subscribe: {hasattr(sub, 'subscribe')}")
        print(f"Has on_publish: {hasattr(sub, 'on_publish')}")
        
        def on_publish(event):
            print(f"Data: {event}")
        
        # Set handler
        sub.on_publish = on_publish
        
        await sub.subscribe()
        print("Subscribed successfully")
        
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_subscription())