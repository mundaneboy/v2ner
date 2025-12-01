import os
import re
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
import logging

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# دریافت متغیرهای محیطی
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_STRING = os.getenv('TELEGRAM_SESSION')

# الگوهای جستجو برای کانفیگ‌ها
CONFIG_PATTERNS = [
    r'vmess://[a-zA-Z0-9+/=]+',
    r'vless://[a-zA-Z0-9\-@:.]+(?:\?[a-zA-Z0-9_=&%\-]*)?(?:#[a-zA-Z0-9%\-_]*)?',
    r'trojan://[a-zA-Z0-9\-@:.]+(?:\?[a-zA-Z0-9_=&%\-]*)?(?:#[a-zA-Z0-9%\-_]*)?',
    r'ss://[a-zA-Z0-9\-@:.]+(?:#[a-zA-Z0-9%\-_]*)?',
    r'hysteria://[a-zA-Z0-9\-@:.]+(?:\?[a-zA-Z0-9_=&%\-]*)?(?:#[a-zA-Z0-9%\-_]*)?',
    r'hysteria2://[a-zA-Z0-9\-@:.]+(?:\?[a-zA-Z0-9_=&%\-]*)?(?:#[a-zA-Z0-9%\-_]*)?',
    r'tuic://[a-zA-Z0-9\-@:.]+(?:\?[a-zA-Z0-9_=&%\-]*)?(?:#[a-zA-Z0-9%\-_]*)?',
]

async def get_configs_from_messages(messages):
    configs = []
    for message in messages:
        if message.text:
            for pattern in CONFIG_PATTERNS:
                found = re.findall(pattern, message.text)
                configs.extend(found)
    return configs

async def process_channel(client, channel_username):
    logger.info(f"Checking channel: {channel_username}")
    
    try:
        entity = await client.get_entity(channel_username)
    except Exception as e:
        logger.error(f"Error getting entity for {channel_username}: {e}")
        return []

    now = datetime.now(timezone.utc)
    
    # بازه‌های زمانی برای بررسی
    time_windows = [24, 48, 72]
    
    found_configs = []
    
    for hours in time_windows:
        logger.info(f"Checking last {hours} hours for {channel_username}...")
        cutoff_time = now - timedelta(hours=hours)
        
        # اگر این اولین بازه نیست (یعنی 48 یا 72)، باید مطمئن شویم که پیام‌های تکراری بازه قبلی را دوباره نگیریم
        # اما ساده‌ترین راه این است که کل بازه را بگیریم و اگر کانفیگ پیدا شد، حلقه را بشکنیم.
        # طبق درخواست شما: "اگه نداشت کد باید ۴۸ ساعت گذشته اون کانال رو فقط بررسی کنه"
        
        messages = []
        async for message in client.iter_messages(entity, offset_date=now, limit=None):
            if message.date < cutoff_time:
                break
            messages.append(message)
            
        configs = await get_configs_from_messages(messages)
        
        if configs:
            logger.info(f"Found {len(configs)} configs in last {hours} hours.")
            found_configs = configs
            break # اگر پیدا کردیم، دیگر بازه‌های زمانی عقب‌تر را چک نمی‌کنیم
        else:
            logger.info(f"No configs found in last {hours} hours. Extending search...")
            
    return found_configs

async def main():
    if not API_ID or not API_HASH or not SESSION_STRING:
        logger.error("Environment variables TELEGRAM_API_ID, TELEGRAM_API_HASH, or TELEGRAM_SESSION are missing.")
        return

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        
        # خواندن لیست کانال‌ها
        try:
            with open('channels.txt', 'r') as f:
                channels = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            logger.error("channels.txt not found.")
            return

        all_configs = []

        for channel in channels:
            configs = await process_channel(client, channel)
            all_configs.extend(configs)
            
        # حذف تکراری‌ها
        unique_configs = list(set(all_configs))
        
        logger.info(f"Total unique configs found: {len(unique_configs)}")
        
        # ذخیره در فایل (فعلا در یک فایل متنی ساده)
        with open('subscribed_configs.txt', 'w') as f:
            for config in unique_configs:
                f.write(config + '\n')

if __name__ == '__main__':
    asyncio.run(main())
