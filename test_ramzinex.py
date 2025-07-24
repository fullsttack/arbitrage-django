#!/usr/bin/env python3
"""
Simple test script for Ramzinex service using centrifuge-python
"""
import asyncio
import os
import sys
import logging
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import after Django setup
from core.services.ramzinex import RamzinexService

async def test_ramzinex():
    """Test Ramzinex service connection and data reception"""
    print("Starting Ramzinex test...")
    
    # Create service instance
    service = RamzinexService()
    
    try:
        # Test connection
        print("Testing connection...")
        connected = await service.connect()
        
        if not connected:
            print("❌ Connection failed")
            return
            
        print("✅ Connected successfully")
        
        # Test subscription with common pair IDs (you might need to adjust these)
        test_pairs = ['432', '433', '434']  # USDT/TMN, BTC/USDT, ETH/USDT pair IDs
        
        print(f"Testing subscription to pairs: {test_pairs}")
        subscribed = await service.subscribe_to_pairs(test_pairs)
        
        if not subscribed:
            print("❌ Subscription failed")
            return
            
        print("✅ Subscribed successfully")
        
        # Wait for data
        print("Waiting for price data (30 seconds)...")
        for i in range(30):
            await asyncio.sleep(1)
            if service.is_receiving_data:
                print(f"✅ Receiving price data! (after {i+1} seconds)")
                break
            print(f"⏳ Waiting... ({i+1}/30)")
        else:
            print("❌ No price data received after 30 seconds")
        
        # Show connection status
        print(f"Connection healthy: {service.is_connection_healthy()}")
        print(f"Subscribed pairs: {service.subscribed_pairs}")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("Disconnecting...")
        await service.disconnect()
        print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_ramzinex())