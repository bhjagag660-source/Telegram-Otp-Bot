import asyncio
import random
import time
from pyrogram import Client, errors, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- [ AYARLAR ] ---
API_ID = 35411044
API_HASH = '9fa8ebe0ccbf7ae2cdbf3841976efbbf'
BOT_TOKEN = '8625332216:AAHB3PxXhF64uiyvXU6XMvqKI4ZnzGFgFCA'
TARGET_CHANNEL = "cantagkanal" 
ADMIN_ID = 8434939976 

user_app = Client("sniper_user_session", api_id=API_ID, api_hash=API_HASH)
bot_app = Client("sniper_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- [ HAFIZA VE VERİ ] ---
user_credits = {} 
all_users = set()
vip_users = [ADMIN_ID]
waiting_for_tag = []
DEFAULT_CREDIT = 3 
REF_REWARD = 5 

# --- [ ÜRETİCİ: KÜFÜRLÜ, OTORİTER VE HAVALI ] ---

def generate_elite_name():
    # 1. Sanayi/Sert Otorite Grubu
    boss_prefix = ["Sanayi", "Cadde", "Sokak", "Mahalle", "Semt", "Alem", "Gece", "Zifiri", "Yeralti", "Mezar", "Kaos"]
    boss_suffix = ["Sahibi", "Reisi", "Agasi", "Piri", "Krali", "Lideri", "Baskani", "Vip", "Sefi", "Babasi"]
    
    # 2. Sert/Argo/Küfürlü Grup
    slang_roots = ["Sik", "Pic", "Am", "Got", "Yarrak", "Dalyarak", "Kancik", "Gavat", "Serefsiz", "Kevase", "Orospu"]
    slang_ends = ["ici", "perest", "log", "izm", "matik", "zade", "han", "can", "bey", "istan", "of"]
    
    # 3. Modern/Elit/Havalı Grup
    cool_prefix = ["Must", "Dark", "Lord", "Azar", "Turk", "Marlboro", "Work", "Zex", "Rex", "Sky", "Mega", "Alpha", "Zero", "Ghost", "Nitro"]
    cool_suffix = ["ox", "enzy", "touch", "ly", "ix", "31", "69", "hub", "net", "star", "pro", "shot", "vibe"]

    choice = random.randint(1, 4)
    if choice == 1: return (random.choice(boss_prefix) + random.choice(boss_suffix)).lower()
    elif choice == 2: return (random.choice(slang_roots) + random.choice(slang_ends)).lower()
    elif choice == 3: return (random.choice(cool_prefix) + random.choice(cool_suffix)).lower()
    else: return (random.choice(boss_prefix) + random.choice(cool_suffix)).lower()

# --- [ TAKİP VE TEMİZLİK SİSTEMİ ] ---

async def monitor_and_clean(username, channel_msg_id, user_id=None, user_msg_id=None):
    start_time = time.time()
    is_taken = False
    while True:
        try:
            if not is_taken:
                try:
                    await user_app.get_chat(username)
                    # ALINDI! Mesajı güncelle
                    is_taken = True
                    text = f"❌ **BU TAG ALINDI!**\n\n👤 Tag: @{username}\n⚠️ Artık müsait değil. Yeni isimler taranıyor..."
                    await bot_app.edit_message_text(f"@{TARGET_CHANNEL}", channel_msg_id, text)
                    if user_id and user_msg_id:
                        try: await bot_app.edit_message_text(user_id, user_msg_id, f"❌ @{username} kapıldı!")
                        except: pass
                except errors.UsernameNotOccupied: pass

            # 24 Saat dolunca sil (86400 saniye)
            if time.time() - start_time > 86400:
                try: await bot_app.delete_messages(f"@{TARGET_CHANNEL}", channel_msg_id)
                except: pass
                break
            await asyncio.sleep(20)
        except Exception: break

# --- [ YAYIN FONKSİYONU ] ---

async def broadcast(username):
    tag_md = f"`@{username}`"
    text = (
        "💎 **YENİ TAG BULUNDU!**\n\n"
        f"👤 İsim: {tag_md}\n"
        "👆 (Kopyalamak için üzerine dokun)\n\n"
        "🔥 **DURUM:** Boşta! Hemen kap!\n\n"
        "⬇️ **HIZLI ALMA TALİMATI:**\n"
        "1. Yukarıdaki isme dokunup kopyala.\n"
        "2. Alttaki 'Hemen Al / Profile Git' butonuna bas.\n"
        "3. Açılan yerde kullanıcı adını yapıştır ve kaydet!"
    )
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Hemen Al / Profile Git", url="tg://settings/username")],
        [InlineKeyboardButton("📢 Kanalı Görüntüle", url=f"https://t.me/{TARGET_CHANNEL}")]
    ])

    sent_channel_msg = await bot_app.send_message(f"@{TARGET_CHANNEL}", text, reply_markup=btn)
    
    u_uid, u_msg_id = None, None
    if waiting_for_tag:
        u_uid = waiting_for_tag.pop(0)
        try:
            u_msg = await bot_app.send_message(u_uid, "🎁 **Senin İçin Bulundu!**\n" + text, reply_markup=btn)
            u_msg_id = u_msg.id
        except: pass

    asyncio.create_task(monitor_and_clean(username, sent_channel_msg.id, u_uid, u_msg_id))

# --- [ BOT KOMUTLARI ] ---

@bot_app.on_message(filters.command("start"))
async def start_handler(client, message):
    user_id = message.from_user.id
    all_users.add(user_id)
    
    if len(message.command) > 1 and message.command[1].startswith("ref_"):
        inviter_id = int(message.command[1].split("_")[1])
        if inviter_id != user_id:
            user_credits[inviter_id] = user_credits.get(inviter_id, DEFAULT_CREDIT) + REF_REWARD
            try: await bot_app.send_message(inviter_id, f"🎉 Arkadaşın katıldı! **+{REF_REWARD} Hak** kazandın.")
            except: pass

    if user_id not in user_credits: user_credits[user_id] = DEFAULT_CREDIT

    try:
        await bot_app.get_chat_member(TARGET_CHANNEL, user_id)
    except:
        return await message.reply_text(
            "⚠️ **DUR! Botu kullanmak için kanala katıl.**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{TARGET_CHANNEL}")]])
        )

    invite_link = f"https://t.me/{(await bot_app.get_me()).username}?start=ref_{user_id}"
    await message.reply_text(
        f"🚀 **Elite Sniper Bot (VDS)**\n\n"
        f"👤 **Hesabın:** {'Admin' if user_id == ADMIN_ID else f'{user_credits[user_id]} Hak'}\n"
        f"🎁 **Davet Linkin:** `{invite_link}`\n"
        "(Davet başına +5 hak!)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Bana Tag Bul", callback_data="find_tag")]])
    )

@bot_app.on_callback_query(filters.regex("find_tag"))
async def find_tag_cb(client, query):
    u_id = query.from_user.id
    if u_id != ADMIN_ID and user_credits.get(u_id, 0) <= 0:
        return await query.answer("❌ Hakkın bitti! Arkadaşlarını davet et.", show_alert=True)
    if u_id not in waiting_for_tag:
        if u_id != ADMIN_ID: user_credits[u_id] -= 1
        waiting_for_tag.append(u_id)
        await query.answer("Pusuya yatıldı! Boşta isim çıkınca ilk sana haber vereceğim.", show_alert=True)
    else: await query.answer("Zaten sıradadasın.", show_alert=True)

# --- [ ANA ÇALIŞTIRICI ] ---

async def hunting():
    while True:
        target = generate_elite_name()
        try:
            await user_app.get_chat(target)
        except errors.UsernameNotOccupied:
            await broadcast(target)
            await asyncio.sleep(25)
        except Exception: pass
        await asyncio.sleep(4)

async def main():
    await user_app.start()
    await bot_app.start()
    asyncio.create_task(hunting())
    print("🔥 Sert & Küfürlü Tag Sniper VDS'de Yayında!")
    from pyrogram import idle
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
