#!/usr/bin/env python3
"""
Test publication context
"""
import asyncio
from centrifuge import Client

async def test_publication():
    """Test publication context"""
    
    client = Client(
        address='wss://websocket.ramzinex.com/websocket',
        name="test-pub"
    )
    
    await client.connect()
    await asyncio.sleep(1)
    
    # Create subscription
    sub = client.new_subscription('orderbook:432')
    
    def handle_publication(ctx):
        print(f"Publication context: {ctx}")
        print(f"Context dir: {[x for x in dir(ctx) if not x.startswith('_')]}")
        if hasattr(ctx, 'data'):
            print(f"Data: {ctx.data}")
        if hasattr(ctx, 'publication'):
            print(f"Publication: {ctx.publication}")
            if hasattr(ctx.publication, 'data'):
                print(f"Publication data: {ctx.publication.data}")
    
    # Set handler as regular function (not async)
    sub.events.on_publication = handle_publication
    
    await sub.subscribe()
    print("Waiting for publications...")
    await asyncio.sleep(10)
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_publication())