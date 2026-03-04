import telebot
from telebot import types
import os
import subprocess
import http.server
import threading
import re

# --- AYARLAR ---
TOKEN = "8732604700:AAFGlCTAUBG7xkouu8ZaXnFmf_3MrdVJc3Y"
ADMIN_ID = 8434939976 
START_PHOTO = "https://img.freepik.com/free-vector/server-room-cloud-storage-concept-datacenter-database-technology-data-center-isometric-composition_39422-542.jpg"

bot = telebot.TeleBot(TOKEN)

# Veri Takibi
running_processes = {}
pending_files = {}
vip_users = {ADMIN_ID} # Başlangıçta sadece admin VIP

# --- RENDER KEEP-ALIVE (Port Hatası Çözümü) ---
def run_keep_alive():
    class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is active!")
    port = int(os.environ.get("PORT", 8080))
    server = http.server.HTTPServer(('', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_keep_alive, daemon=True).start()

# --- YARDIMCI FONKSİYONLAR ---
def get_user_folder(uid):
    path = f"downloads/{uid}"
    os.makedirs(path, exist_ok=True)
    return path

def get_user_files(uid):
    folder = get_user_folder(uid)
    return [f for f in os.listdir(folder) if f.endswith('.py')]

def is_vip(uid):
    return uid in vip_users

# --- ANA MENÜ (ONLINE KEYBOARD) ---
def main_menu_inline():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📁 Dosya Yükle", callback_data="btn_upload"),
        types.InlineKeyboardButton("📂 Dosyalarım", callback_data="btn_files"),
        types.InlineKeyboardButton("📦 Modül Yükle", callback_data="btn_module"),
        types.InlineKeyboardButton("📞 Destek", callback_data="btn_support")
    )
    return markup

# --- OTOMATİK MODÜL YÜKLEYİCİ ---
def install_missing_modules(file_content):
    try:
        decoded = file_content.decode('utf-8')
        modules = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", decoded, re.MULTILINE)
        standard_libs = ["os", "sys", "time", "subprocess", "threading", "http", "re", "json", "random", "telebot", "math"]
        for module in set(modules):
            if module not in standard_libs:
                print(f"📦 Modül kuruluyor: {module}")
                subprocess.run(["pip", "install", module], check=False)
    except Exception as e:
        print(f"❌ Modül kurulum hatası: {e}")

# --- VIP YETKİLENDİRME (/vip / @unvip) ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("@"))
def handle_vip_command(message):
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
        
        if "@vip" in message.text.lower():
            vip_users.add(target_id)
            bot.reply_to(message, f"💎 **{target_name}** artık bir VIP kullanıcı!")
        elif "@unvip" in message.text.lower():
            if target_id in vip_users:
                vip_users.remove(target_id)
                bot.reply_to(message, f"❌ **{target_name}** VIP yetkisi alındı.")
    else:
        bot.reply_to(message, "⚠️ Birini VIP yapmak için mesajını yanıtlayarak (Reply) `@vip` yazın.")

# --- KOMUTLAR ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    status = "💎 VIP" if is_vip(uid) else "🆓 Ücretsiz"
    limit = "Sınırsız" if is_vip(uid) else "3"
    
    text = (f"👋 Merhaba {message.from_user.first_name}!\n\n"
            f"👤 Durum: {status}\n"
            f"📊 Limit: {len(get_user_files(uid))} / {limit}\n\n"
            "İşlem seçmek için butonları kullanın:")
    
    try:
        bot.send_photo(message.chat.id, START_PHOTO, caption=text, reply_markup=main_menu_inline())
    except:
        bot.send_message(message.chat.id, text, reply_markup=main_menu_inline())

# --- CALLBACK İŞLEMLERİ (Buton Tıklamaları) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    data = call.data

    # Menü Butonları
    if data == "btn_upload":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📤 Lütfen çalıştırmak istediğiniz `.py` dosyasını gönderin.")
        
    elif data == "btn_files":
        bot.answer_callback_query(call.id)
        show_my_files(call.message)
        
    elif data == "btn_module":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📦 **Modül Sistemi:** Dosyanız onaylandığında kütüphaneler otomatik kurulur. Manuel kurulum için admin ile görüşün.")
        
    elif data == "btn_support":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📞 **Destek:** Sorunlar için @HollandaBaskan ile iletişime geçebilirsiniz.")

    # Admin Onay/Red İşlemleri
    elif data.startswith(("approve_", "reject_")):
        action, f_id = data.split("_", 1)
        if f_id not in pending_files:
            return bot.answer_callback_query(call.id, "❌ Dosya verisi bulunamadı.")
        
        target_uid = pending_files[f_id]["uid"]
        target_name = pending_files[f_id]["name"]

        if action == "approve":
            install_missing_modules(pending_files[f_id]["content"])
            path = get_user_folder(target_uid)
            with open(f"{path}/{target_name}", 'wb') as f:
                f.write(pending_files[f_id]["content"])
            bot.send_message(target_uid, f"✅ `{target_name}` onaylandı ve modüller yüklendi!")
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        del pending_files[f_id]
        bot.answer_callback_query(call.id, "İşlem Tamam")

    # Dosya Yönetimi (Run/Stop/Log/Del)
    elif "_" in data:
        action, f_name = data.split("_", 1)
        f_path = f"downloads/{uid}/{f_name}"
        p_key = f"{uid}_{f_name}"

        if action == "run":
            if p_key in running_processes:
                bot.answer_callback_query(call.id, "⚠️ Zaten çalışıyor.")
            else:
                log_f = open(f"{f_path}.log", "w")
                proc = subprocess.Popen(["python3", f_path], stdout=log_f, stderr=log_f)
                running_processes[p_key] = proc
                bot.answer_callback_query(call.id, "🚀 Başlatıldı")
        
        elif action == "stop":
            if p_key in running_processes:
                running_processes[p_key].terminate()
                del running_processes[p_key]
                bot.answer_callback_query(call.id, "🛑 Durduruldu")

        elif action == "log":
            bot.answer_callback_query(call.id)
            if os.path.exists(f"{f_path}.log"):
                with open(f"{f_path}.log", "r") as f: logs = f.read()[-500:]
                bot.send_message(call.message.chat.id, f"📝 **Log:**\n`{logs if logs else 'Çıktı yok.'}`")

        elif action == "del":
            if p_key in running_processes: running_processes[p_key].terminate()
            if os.path.exists(f_path): os.remove(f_path)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "Silindi")

# --- DOSYA YÜKLEME ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    uid = message.from_user.id
    f_name = message.document.file_name

    if not f_name.endswith(".py"):
        return bot.reply_to(message, "❌ Sadece .py dosyaları gönderebilirsiniz.")

    if not is_vip(uid) and len(get_user_files(uid)) >= 3:
        return bot.reply_to(message, "⚠️ Ücretsiz limit doldu (3/3). VIP üyelik için admin ile iletişime geçin.")

    file_info = bot.get_file(message.document.file_id)
    content = bot.download_file(file_info.file_path)
    f_id = message.document.file_id
    pending_files[f_id] = {"uid": uid, "name": f_name, "content": content}

    bot.reply_to(message, "⏳ Dosyanız admin onayına gönderildi.")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Onayla", callback_data=f"approve_{f_id}"),
               types.InlineKeyboardButton("❌ Reddet", callback_data=f"reject_{f_id}"))
    
    bot.send_message(ADMIN_ID, f"🔔 **YENİ ONAY TALEBİ**\n👤 {message.from_user.first_name}\n📄 `{f_name}`", 
                     reply_markup=markup, parse_mode="Markdown")

def show_my_files(message):
    uid = message.chat.id
    files = get_user_files(uid)
    if not files: return bot.send_message(uid, "🗄️ Onaylanmış dosyanız bulunmuyor.")
    for f in files:
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("▶️ Başlat", callback_data=f"run_{f}"),
                   types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{f}"))
        markup.row(types.InlineKeyboardButton("📝 Log", callback_data=f"log_{f}"),
                   types.InlineKeyboardButton("🗑️ Sil", callback_data=f"del_{f}"))
        bot.send_message(uid, f"📄 `{f}`", reply_markup=markup)

print("🚀 Bot Yayında (Render Uyumlu)")
bot.infinity_polling()
