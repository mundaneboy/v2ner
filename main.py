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
# الگوی کلی برای پیدا کردن پروتکل‌ها تا رسیدن به فضای خالی یا خط جدید
CONFIG_REGEX = r'(vmess|vless|trojan|ss|hysteria|hysteria2|tuic)://[^\s\n]+'

def clean_config(config, channel_name):
    """
    لینک را تمیز می‌کند و اگر اسم نداشت، اسم کانال را اضافه می‌کند.
    """
    # حذف کاراکترهای اضافی از انتهای لینک (مثل نقطه، ویرگول، پرانتز که در متن پیام ممکن است باشد)
    config = config.rstrip('.,)]}!:;\'"')
    
    # بررسی پروتکل
    if config.startswith('vmess://'):
        # برای vmess فعلا کاری نمی‌کنیم چون ساختار json base64 دارد و دستکاری آن پیچیده است
        # فقط اگر خیلی کوتاه بود حذفش می‌کنیم
        if len(config) < 15:
            return None
        return config
    
    else:
        # برای سایر پروتکل‌ها (vless, trojan, ...)
        # چک می‌کنیم آیا # (fragment) دارد یا نه
        if '#' not in config:
            # اگر نداشت، اسم کانال را اضافه می‌کنیم
            # کاراکترهای غیرمجاز در اسم کانال را حذف یا جایگزین می‌کنیم
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '', channel_name)
            config += f"#{safe_name}"
        
        return config

async def get_configs_from_messages(messages, channel_name):
    configs = []
    for message in messages:
        if message.text:
            # پیدا کردن تمام لینک‌ها با الگوی جدید
            found = re.findall(CONFIG_REGEX, message.text)
            for conf in found:
                cleaned = clean_config(conf, channel_name)
                if cleaned:
                    configs.append(cleaned)
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
        
        messages = []
        async for message in client.iter_messages(entity, offset_date=now, limit=None):
            if message.date < cutoff_time:
                break
            messages.append(message)
            
        # نام کانال را برای نام‌گذاری کانفیگ‌ها می‌فرستیم
        # از username یا title استفاده می‌کنیم
        display_name = getattr(entity, 'username', None) or getattr(entity, 'title', 'Unknown')
        
        configs = await get_configs_from_messages(messages, display_name)
        
        if configs:
            logger.info(f"Found {len(configs)} configs in last {hours} hours.")
            found_configs = configs
            break 
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
