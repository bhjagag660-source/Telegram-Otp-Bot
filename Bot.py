import asyncio
import time
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- [ YAPILANDIRMA ] ---
API_ID = 35411044
API_HASH = '9fa8ebe0ccbf7ae2cdbf3841976efbbf'
BOT_TOKEN = '8610100612:AAGDf9ikV2bORW8ry1KSqGH2Oh_MMW53u-Q'

TARGET_BOT = "Allnumbersultra_Bot"
OTP_CHANNEL = "TechUniverseotp"

# VDS'de session dosyaları kalıcıdır, bir kez giriş yeterlidir.
user_app = Client("user_session", api_id=API_ID, api_hash=API_HASH)
bot_app = Client("main_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- [ HAFIZA VE SIRALAMA ] ---
active_users = []       # Botu başlatan kullanıcılar listesi
delivered_numbers = {}  # Dağıtılan numaralar ve zamanları {numara: zaman}
last_user_index = 0     # Sıradaki kullanıcıyı takip eden sayaç

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇦🇿 Manuel Sorgula (+994)", callback_data="fetch")],
        [InlineKeyboardButton("📢 Kanalı Görüntüle", url=f"https://t.me/{OTP_CHANNEL}")]
    ])

# /start komutu - Herkes kullanabilir
@bot_app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.chat.id
    if user_id not in active_users:
        active_users.append(user_id)
    
    await message.reply_text(
        "🚀 **VDS Üzerinde OTP Botu Aktif!**\n\n"
        "✅ Numaralar kanala düştükçe **sırayla** dağıtılır.\n"
        "🔐 Her numara sadece **1 kişiye özel** iletilir.\n"
        "⏳ Dağıtılan numaralar 20 dakika boyunca korunur.",
        reply_markup=get_main_menu()
    )

# Otomatik Sorgu Fonksiyonu
async def do_fetch():
    try:
        await user_app.send_message(TARGET_BOT, "/start")
        await asyncio.sleep(10) # Botun yanıt vermesi için bekleme
        async for msg in user_app.get_chat_history(TARGET_BOT, limit=1):
            if msg.reply_markup:
                for row in msg.reply_markup.inline_keyboard:
                    for btn in row:
                        if "Azerbaijan" in btn.text:
                            await msg.click(btn.text)
                            return
    except Exception as e:
        print(f"Sorgu Hatası: {e}")

# Buton Sorgusu
@bot_app.on_callback_query(filters.regex("fetch"))
async def manual_fetch(client, query):
    await query.answer("VDS Sorgu Başlattı...")
    await do_fetch()

# --- [ KANAL DİNLEME VE SIRALI DAĞITIM ] ---
@user_app.on_message(filters.chat(OTP_CHANNEL))
async def on_new_otp(client, message):
    global last_user_index
    if message.text and "+994" in message.text:
        num_text = message.text
        now = time.time()
        
        # 1. 20 Dakika Koruması (Aynı numara tekrar gelirse kimseye verme)
        if num_text in delivered_numbers:
            if now - delivered_numbers[num_text] < 1200:
                return 

        # 2. Kullanıcı Kontrolü
        if not active_users:
            return

        # 3. Sıradaki Kullanıcıyı Seç (Kuyruk Sistemi)
        user_id = active_users[last_user_index % len(active_users)]
        last_user_index += 1

        # 4. Sadece O Kişiye İlet
        clean_msg = (
            "🎯 **SİZE ÖZEL NUMARA GELDİ!**\n\n"
            f"`{num_text}`\n\n"
            "👆 **Dokun ve Kopyala.**\n"
            "⚠️ Bu numara sadece size özel iletilmiştir."
        )
        
        try:
            await bot_app.send_message(user_id, clean_msg)
            delivered_numbers[num_text] = now # Verilme zamanını kaydet
        except:
            # Botu engelleyen kullanıcıyı listeden temizle
            if user_id in active_users:
                active_users.remove(user_id)

# --- [ OTOMATİK DÖNGÜ VE TEMİZLİK ] ---
async def maintenance_loop():
    while True:
        # Eski numaraları (20 dk dolanlar) hafızadan sil
        now = time.time()
        expired = [n for n, t in delivered_numbers.items() if now - t > 1200]
        for n in expired:
            del delivered_numbers[n]

        # Her 20 dakikada bir otomatik sorgu at
        await do_fetch()
        await asyncio.sleep(1200)

async def main():
    print("🚀 Sistem VDS için başlatılıyor...")
    await user_app.start()
    await bot_app.start()
    asyncio.create_task(maintenance_loop())
    print("✅ Botlar hazır ve kanal dinleniyor!")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
    
