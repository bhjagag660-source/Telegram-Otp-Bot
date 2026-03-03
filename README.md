import asyncio
import time
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- AYARLAR ---
API_ID = 35411044
API_HASH = '9fa8ebe0ccbf7ae2cdbf3841976efbbf'
BOT_TOKEN = '8610100612:AAGDf9ikV2bORW8ry1KSqGH2Oh_MMW53u-Q'

TARGET_BOT = "Allnumbersultra_Bot"
OTP_CHANNEL = "TechUniverseotp"

# Session dosyaları VDS'de kalıcı olur
user_app = Client("user_session", api_id=API_ID, api_hash=API_HASH)
bot_app = Client("main_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

active_users = [] 
delivered_numbers = {} 
last_user_index = 0

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇦🇿 Manuel Sorgula", callback_data="fetch")],
        [InlineKeyboardButton("📢 Kanalı Aç", url=f"https://t.me/{OTP_CHANNEL}")]
    ])

@bot_app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.chat.id
    if user_id not in active_users:
        active_users.append(user_id)
    await message.reply_text(
        "🚀 **VDS Üzerinde Sistem Aktif!**\n\nNumaralar sırayla dağıtılır. Size özel numara gelince mesaj alacaksınız.",
        reply_markup=get_main_menu()
    )

async def do_fetch():
    try:
        await user_app.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(10) 
        async for msg in user_app.get_chat_history(TARGET_BOT, limit=1):
            if msg.reply_markup:
                for row in msg.reply_markup.inline_keyboard:
                    for btn in row:
                        if "Azerbaijan" in btn.text:
                            await msg.click(btn.text)
                            return
    except Exception as e:
        print(f"Hata: {e}")

@bot_app.on_callback_query(filters.regex("fetch"))
async def manual_fetch(client, query):
    await query.answer("VDS Sorgu Başlattı...")
    await do_fetch()

@user_app.on_message(filters.chat(OTP_CHANNEL))
async def on_new_otp(client, message):
    global last_user_index
    if message.text and "+994" in message.text:
        num_text = message.text
        now = time.time()
        
        if num_text in delivered_numbers:
            if now - delivered_numbers[num_text] < 1200: return

        if not active_users: return

        user_id = active_users[last_user_index % len(active_users)]
        last_user_index += 1

        try:
            await bot_app.send_message(user_id, f"🔐 **SİZE ÖZEL NUMARA:**\n\n`{num_text}`\n\n👆 **Dokun kopyala.**")
            delivered_numbers[num_text] = now
        except:
            active_users.remove(user_id)

async def loop():
    while True:
        # Temizlik
        now = time.time()
        expired = [n for n, t in delivered_numbers.items() if now - t > 1200]
        for n in expired: del delivered_numbers[n]

        await do_fetch()
        await asyncio.sleep(1200)

async def main():
    await user_app.start()
    await bot_app.start()
    asyncio.create_task(loop())
    print("✅ Bot VDS üzerinde 7/24 çalışmaya hazır!")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
    
