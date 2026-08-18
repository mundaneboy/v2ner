from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os

api_id = input("Enter API ID: ")
api_hash = input("Enter API HASH: ")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nYour SESSION_STRING is:\n")
    print(client.session.save())
    print("\nCopy this string and save it as a GitHub Secret named TELEGRAM_SESSION.")
