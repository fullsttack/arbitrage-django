#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

print("Testing imports...")

try:
    from centrifuge import Client, SubscribeErrorEvent, SubscribeSuccessEvent, PublishEvent
    print("✅ Centrifuge import successful")
    CENTRIFUGE_AVAILABLE = True
except ImportError as e:
    print(f"❌ Centrifuge import failed: {e}")
    CENTRIFUGE_AVAILABLE = False

print(f"CENTRIFUGE_AVAILABLE = {CENTRIFUGE_AVAILABLE}")

# Test the service import
try:
    from core.services.ramzinex import RamzinexService, CENTRIFUGE_AVAILABLE as SERVICE_CENTRIFUGE
    print(f"✅ Service import successful. SERVICE_CENTRIFUGE_AVAILABLE = {SERVICE_CENTRIFUGE}")
except Exception as e:
    print(f"❌ Service import failed: {e}")
    import traceback
    traceback.print_exc()