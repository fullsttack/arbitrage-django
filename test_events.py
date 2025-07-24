#!/usr/bin/env python3
"""
Test event handling
"""
import asyncio
from centrifuge import Client

async def test_events():
    """Test event handling"""
    
    client = Client(
        address='wss://websocket.ramzinex.com/websocket',
        name="test-events"
    )
    
    await client.connect()
    await asyncio.sleep(1)
    
    # Create subscription
    sub = client.new_subscription('orderbook:432')
    print(f"Events: {sub.events}")
    
    # Set up event listeners
    async def handle_published(ctx):
        print(f"📊 Published data: {ctx.data}")
    
    async def handle_subscribed(ctx):
        print(f"✅ Subscribed: {ctx}")
    
    async def handle_error(ctx):
        print(f"❌ Error: {ctx}")
    
    # Subscribe to events
    sub.events.published.add_listener(handle_published)
    sub.events.subscribed.add_listener(handle_subscribed)
    sub.events.error.add_listener(handle_error)
    
    await sub.subscribe()
    print("Waiting for events...")
    await asyncio.sleep(10)
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_events())