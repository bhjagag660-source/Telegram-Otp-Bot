import telebot
from telebot import types
import os
import subprocess

# --- AYARLAR ---
TOKEN = "8732604700:AAFGlCTAUBG7xkouu8ZaXnFmf_3MrdVJc3Y"
ADMIN_ID = 8434939976 
START_PHOTO = "https://img.freepik.com/free-vector/server-room-cloud-storage-concept-datacenter-database-technology-data-center-isometric-composition_39422-542.jpg"

bot = telebot.TeleBot(TOKEN)

# Veri Takibi
running_processes = {}
user_states = {}
pending_files = {} # Onay bekleyen dosyalar: {file_id: {uid, name, content}}

# --- YARDIMCI FONKSİYONLAR ---
def get_user_folder(uid):
    path = f"downloads/{uid}"
    os.makedirs(path, exist_ok=True)
    return path

def get_user_files(uid):
    folder = get_user_folder(uid)
    return [f for f in os.listdir(folder) if f.endswith('.py')]

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📦 Modül Yükle", "📁 Dosya Yükle")
    markup.row("📂 Dosyalarım", "📞 Destek & İletişim")
    return markup

# --- KOMUTLAR ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    files = get_user_files(uid)
    text = (f"👋 Hoş Geldiniz, {message.from_user.first_name}!\n\n"
            f"👤 Durumunuz: 🆓 Ücretsiz Kullanıcı\n"
            f"📁 Dosya Sayınız: {len(files)} / 3\n\n"
            f"🤖 Dosya yüklediğinizde admin onayından sonra aktif olacaktır.")
    
    try:
        bot.send_photo(message.chat.id, START_PHOTO, caption=text, reply_markup=main_menu())
    except:
        bot.send_message(message.chat.id, text, reply_markup=main_menu())

# --- DOSYA YÜKLEME VE ONAY İSTEĞİ ---
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    uid = message.from_user.id
    f_name = message.document.file_name

    if not f_name.endswith(".py"):
        return bot.reply_to(message, "❌ Sadece .py dosyaları gönderebilirsiniz.")

    if len(get_user_files(uid)) >= 3:
        return bot.reply_to(message, "⚠️ Dosya limitiniz dolmuş (3/3).")

    # Dosyayı geçici olarak hafızaya al (Henüz kaydetme)
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Onay kodunu oluştur (file_id üzerinden)
    f_id = message.document.file_id
    pending_files[f_id] = {"uid": uid, "name": f_name, "content": downloaded_file}

    # Kullanıcıya bilgi ver
    bot.reply_to(message, "⏳ Dosyanız admin onayına gönderildi. Onaylandığında bildirim alacaksınız.")

    # Admin'e Onay Butonlu Mesaj Gönder
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Onayla", callback_data=f"approve_{f_id}"),
               types.InlineKeyboardButton("❌ Reddet", callback_data=f"reject_{f_id}"))
    
    bot.send_message(ADMIN_ID, f"🔔 **YENİ DOSYA ONAYI**\n\n👤 **Kullanıcı:** {message.from_user.first_name} ({uid})\n📄 **Dosya:** `{f_name}`", 
                     reply_markup=markup, parse_mode="Markdown")

# --- CALLBACK İŞLEMLERİ (ONAY, ÇALIŞTIRMA, SİLME) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    data = call.data

    # --- ADMİN ONAY İŞLEMLERİ ---
    if data.startswith(("approve_", "reject_")):
        action, f_id = data.split("_", 1)
        
        if f_id not in pending_files:
            return bot.answer_callback_query(call.id, "❌ Dosya verisi bulunamadı veya süre doldu.")

        target_uid = pending_files[f_id]["uid"]
        target_name = pending_files[f_id]["name"]

        if action == "approve":
            # Dosyayı gerçek klasöre kaydet
            path = get_user_folder(target_uid)
            with open(f"{path}/{target_name}", 'wb') as f:
                f.write(pending_files[f_id]["content"])
            
            bot.send_message(target_uid, f"✅ `{target_name}` isimli dosyanız admin tarafından **onaylandı**! Artık çalıştırabilirsiniz.")
            bot.edit_message_text(f"✅ Onaylandı: `{target_name}` (Kullanıcı: {target_uid})", call.message.chat.id, call.message.message_id)
        
        else:
            bot.send_message(target_uid, f"❌ `{target_name}` isimli dosyanız admin tarafından **reddedildi**.")
            bot.edit_message_text(f"❌ Reddedildi: `{target_name}`", call.message.chat.id, call.message.message_id)
        
        del pending_files[f_id]
        return

    # --- DOSYA YÖNETİM İŞLEMLERİ (BAŞLAT, STOP, LOG, DEL) ---
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
            bot.edit_message_text(f"📄 **Dosya:** `{f_name}`\n📌 **Durum:** 🟢 Çalışıyor", 
                                  call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup, parse_mode="Markdown")

    elif action == "stop":
        if p_key in running_processes:
            running_processes[p_key].terminate()
            del running_processes[p_key]
            bot.edit_message_text(f"📄 **Dosya:** `{f_name}`\n📌 **Durum:** 🔴 Durduruldu", 
                                  call.message.chat.id, call.message.message_id, reply_markup=call.message.reply_markup, parse_mode="Markdown")

    elif action == "log":
        log_p = f"{f_path}.log"
        if os.path.exists(log_p):
            with open(log_p, "r") as f: logs = f.read()[-500:]
            bot.send_message(call.message.chat.id, f"📝 **Log:**\n`{logs if logs else 'Çıktı yok.'}`")

    elif action == "del":
        if p_key in running_processes:
            running_processes[p_key].terminate()
            del running_processes[p_key]
        if os.path.exists(f_path): os.remove(f_path)
        bot.delete_message(call.message.chat.id, call.message.message_id)

# --- İLETİŞİM VE DİĞER MESAJLAR ---
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    uid = message.from_user.id
    if message.text == "📂 Dosyalarım":
        files = get_user_files(uid)
        if not files: return bot.send_message(message.chat.id, "🗄️ Dosyanız yok.")
        for f in files:
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("▶️ Başlat", callback_data=f"run_{f}"),
                       types.InlineKeyboardButton("⏹️ Durdur", callback_data=f"stop_{f}"))
            markup.row(types.InlineKeyboardButton("📝 Log", callback_data=f"log_{f}"),
                       types.InlineKeyboardButton("🗑️ Sil", callback_data=f"del_{f}"))
            bot.send_message(message.chat.id, f"📄 `{f}`", reply_markup=markup)
    
    elif message.text == "📞 Destek & İletişim":
        bot.send_message(message.chat.id, "Admin ile iletişime geçmek için mesajınızı yazın (Özelllik aktif).")
    
    elif message.text == "📁 Dosya Yükle":
        bot.send_message(message.chat.id, "📤 Lütfen .py dosyanızı gönderin. Admin onayından sonra yüklenecektir.")

print("✅ Onay Sistemli Bot Aktif!")
bot.infinity_polling()
