#!/usr/bin/env python3
"""
🔍 Wallex Socket.IO Complete Test
تست کامل با Socket.IO protocol
"""

import asyncio
import websockets
import json
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WallexSocketIOTest:
    def __init__(self):
        self.url = "wss://api.wallex.ir/ws"
        self.websocket = None
        self.connected = False
        self.start_time = 0
        self.sid = None
        
        # Counters
        self.total_messages = 0
        self.depth_messages = 0
        self.socketio_messages = 0
        self.ping_received = 0
        self.pong_sent = 0
        
        # Socket.IO message types
        self.SOCKETIO_OPEN = "0"      # Connection open
        self.SOCKETIO_CLOSE = "1"     # Connection close  
        self.SOCKETIO_PING = "2"      # Ping
        self.SOCKETIO_PONG = "3"      # Pong
        self.SOCKETIO_MESSAGE = "4"   # Message
        self.SOCKETIO_UPGRADE = "5"   # Upgrade
        self.SOCKETIO_NOOP = "6"      # No operation
        
        # All messages log
        self.all_messages = []
        
    async def connect_and_test(self):
        """اتصال Socket.IO کامل"""
        logger.info("🚀 شروع تست Socket.IO والکس...")
        logger.info(f"📡 اتصال به: {self.url}")
        
        try:
            # Connect to WebSocket with Socket.IO transport
            self.websocket = await websockets.connect(
                self.url + "/?EIO=4&transport=websocket",  # Socket.IO v4
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10
            )
            
            self.connected = True
            self.start_time = time.time()
            logger.info("✅ WebSocket اتصال برقرار شد!")
            
            # Start listening for handshake
            await self.handle_handshake()
            
            # Subscribe after handshake
            await asyncio.sleep(2)
            await self.subscribe_to_market()
            
            # Start main loop
            await self.listen_loop()
            
        except Exception as e:
            logger.error(f"❌ خطا در اتصال: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()
                logger.info("🔌 اتصال بسته شد")
    
    async def handle_handshake(self):
        """Socket.IO handshake"""
        logger.info("🤝 منتظر Socket.IO handshake...")
        
        try:
            # Wait for initial messages
            for _ in range(3):  # Wait for up to 3 messages during handshake
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=5)
                    await self.process_socketio_message(message, is_handshake=True)
                except asyncio.TimeoutError:
                    break
                    
        except Exception as e:
            logger.error(f"❌ خطا در handshake: {e}")
    
    async def subscribe_to_market(self):
        """Subscribe به بازار با Socket.IO format"""
        try:
            # Send Socket.IO message (type 4 = message)
            buy_subscription = self.SOCKETIO_MESSAGE + json.dumps(["subscribe", {"channel": "USDTTMN@buyDepth"}])
            sell_subscription = self.SOCKETIO_MESSAGE + json.dumps(["subscribe", {"channel": "USDTTMN@sellDepth"}])
            
            await self.websocket.send(buy_subscription)
            logger.info(f"📨 ارسال Socket.IO subscribe buyDepth: {buy_subscription}")
            
            await asyncio.sleep(1)
            
            await self.websocket.send(sell_subscription)
            logger.info(f"📨 ارسال Socket.IO subscribe sellDepth: {sell_subscription}")
            
        except Exception as e:
            logger.error(f"❌ خطا در subscribe: {e}")
    
    async def listen_loop(self):
        """حلقه اصلی گوش دادن"""
        logger.info("👂 شروع گوش دادن به پیام‌های Socket.IO...")
        
        last_stats_time = time.time()
        
        try:
            while self.connected:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=10
                    )
                    
                    await self.process_socketio_message(message)
                    
                    # آمار هر 30 ثانیه
                    current_time = time.time()
                    if current_time - last_stats_time >= 30:
                        await self.print_stats()
                        last_stats_time = current_time
                        
                except asyncio.TimeoutError:
                    logger.debug("⏰ Timeout - هیچ پیامی دریافت نشد")
                    continue
                except Exception as e:
                    logger.error(f"❌ خطا در دریافت پیام: {e}")
                    break
                    
        except KeyboardInterrupt:
            logger.info("⏹️ توقف توسط کاربر")
        except Exception as e:
            logger.error(f"❌ خطا در حلقه گوش دادن: {e}")
        finally:
            await self.print_final_stats()
    
    async def process_socketio_message(self, message, is_handshake=False):
        """پردازش پیام Socket.IO"""
        self.total_messages += 1
        
        # Save all messages
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.all_messages.append({
            'time': timestamp,
            'number': self.total_messages,
            'message': message,
            'is_handshake': is_handshake
        })
        
        if is_handshake:
            logger.info(f"🤝 HANDSHAKE MESSAGE #{self.total_messages}: {message}")
        else:
            logger.debug(f"📩 MESSAGE #{self.total_messages}: {message[:100]}...")
        
        # Parse Socket.IO message type
        if not message:
            return
            
        message_type = message[0] if len(message) > 0 else ""
        message_data = message[1:] if len(message) > 1 else ""
        
        # Handle different Socket.IO message types
        if message_type == self.SOCKETIO_OPEN:
            # Connection open - usually JSON with session info
            self.socketio_messages += 1
            logger.info(f"🔓 Socket.IO OPEN: {message_data}")
            try:
                config = json.loads(message_data)
                self.sid = config.get('sid')
                ping_interval = config.get('pingInterval', 0) / 1000
                logger.info(f"✅ Session ID: {self.sid}")
                logger.info(f"⏰ Ping Interval: {ping_interval}s")
            except:
                pass
                
        elif message_type == self.SOCKETIO_PING:
            # Server ping!
            self.ping_received += 1
            self.socketio_messages += 1
            logger.error(f"🏓🏓🏓 Socket.IO PING #{self.ping_received} RECEIVED!")
            await self.send_socketio_pong()
            
        elif message_type == self.SOCKETIO_PONG:
            # Server pong (response to our ping)
            self.socketio_messages += 1
            logger.info(f"🏓 Socket.IO PONG received")
            
        elif message_type == self.SOCKETIO_MESSAGE:
            # Regular message (probably market data)
            if self.is_depth_data(message_data):
                self.depth_messages += 1
            else:
                self.socketio_messages += 1
                logger.warning(f"🔍 Socket.IO MESSAGE (non-depth): {message_data[:200]}")
                
        elif message_type == self.SOCKETIO_CLOSE:
            self.socketio_messages += 1
            logger.warning(f"🔒 Socket.IO CLOSE: {message_data}")
            
        elif message_type == self.SOCKETIO_UPGRADE:
            self.socketio_messages += 1
            logger.info(f"⬆️ Socket.IO UPGRADE: {message_data}")
            
        elif message_type == self.SOCKETIO_NOOP:
            self.socketio_messages += 1
            logger.debug(f"⭕ Socket.IO NOOP")
            
        else:
            # Unknown or malformed
            self.socketio_messages += 1
            logger.warning(f"❓ UNKNOWN MESSAGE TYPE '{message_type}': {message[:200]}")
    
    def is_depth_data(self, message_data):
        """تشخیص داده‌های depth"""
        try:
            data = json.loads(message_data)
            if isinstance(data, list) and len(data) == 2:
                channel = data[0]
                if isinstance(channel, str) and ('@buyDepth' in channel or '@sellDepth' in channel):
                    return True
        except:
            pass
        return False
    
    async def send_socketio_pong(self):
        """ارسال Socket.IO pong"""
        try:
            pong_message = self.SOCKETIO_PONG
            await self.websocket.send(pong_message)
            self.pong_sent += 1
            logger.error(f"🏓🏓🏓 Socket.IO PONG #{self.pong_sent} SENT!")
        except Exception as e:
            logger.error(f"❌ خطا در ارسال Socket.IO pong: {e}")
    
    async def print_stats(self):
        """چاپ آمار"""
        connection_age = time.time() - self.start_time
        expected_pings = int(connection_age / 20)  # هر 20 ثانیه
        
        logger.error("=" * 60)
        logger.error(f"📊 STATS - Connection Age: {connection_age:.0f}s")
        logger.error(f"📊 Total Messages: {self.total_messages}")
        logger.error(f"📊 Depth Messages: {self.depth_messages}")
        logger.error(f"📊 Socket.IO Messages: {self.socketio_messages}")
        logger.error(f"📊 Socket.IO Pings Received: {self.ping_received}")
        logger.error(f"📊 Socket.IO Pongs Sent: {self.pong_sent}")
        logger.error(f"📊 Expected Pings (20s intervals): {expected_pings}")
        
        if expected_pings > 0 and self.ping_received == 0:
            logger.error("🚨 NO Socket.IO PINGS RECEIVED!")
        
        logger.error("=" * 60)
    
    async def print_final_stats(self):
        """آمار نهایی"""
        logger.info("\n" + "=" * 80)
        logger.info("📋 FINAL Socket.IO REPORT")
        logger.info("=" * 80)
        
        connection_duration = time.time() - self.start_time
        logger.info(f"⏱️  Connection Duration: {connection_duration:.1f} seconds")
        logger.info(f"📨 Total Messages: {self.total_messages}")
        logger.info(f"📊 Depth Messages: {self.depth_messages}")
        logger.info(f"🔌 Socket.IO Control Messages: {self.socketio_messages}")
        logger.info(f"🏓 Socket.IO Pings Received: {self.ping_received}")
        logger.info(f"🏓 Socket.IO Pongs Sent: {self.pong_sent}")
        logger.info(f"🆔 Session ID: {self.sid}")
        
        expected_pings = int(connection_duration / 20)
        logger.info(f"🕐 Expected Pings (every 20s): {expected_pings}")
        
        if self.ping_received == 0:
            logger.error("🚨 MAJOR ISSUE: NO Socket.IO PINGS RECEIVED!")
        else:
            logger.info("✅ Socket.IO Ping/Pong working correctly")
        
        # تمام پیام‌ها
        logger.info("\n📋 ALL MESSAGES:")
        logger.info("-" * 50)
        for i, msg in enumerate(self.all_messages[:30], 1):  # اول 30 تا
            prefix = "[HANDSHAKE]" if msg['is_handshake'] else "[REGULAR]  "
            logger.info(f"{i:2d}. {prefix} [{msg['time']}] {msg['message'][:100]}")
        
        if len(self.all_messages) > 30:
            logger.info(f"... و {len(self.all_messages) - 30} پیام دیگر")
        
        logger.info("=" * 80)


async def main():
    """اجرای تست Socket.IO"""
    print("🔍 Wallex Socket.IO Complete Test")
    print("=" * 50)
    print("این اسکریپت:")
    print("✅ Socket.IO protocol کامل پیاده‌سازی می‌کند")
    print("✅ Handshake صحیح انجام می‌دهد")
    print("✅ Socket.IO ping/pong تشخیص می‌دهد")
    print("✅ همه message type ها را log می‌کند")
    print("\nبرای توقف Ctrl+C بزنید")
    print("=" * 50)
    
    test = WallexSocketIOTest()
    await test.connect_and_test()


if __name__ == "__main__":
    asyncio.run(main())