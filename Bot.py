import telebot
from telebot import types
import sqlite3
import subprocess
import sys
import os
import threading
import http.server # Render için mecburi

# ================= AYARLAR =================
TOKEN = "8732604700:AAFGlCTAUBG7xkouu8ZaXnFmf_3MrdVJc3Y"
ADMIN_ID = 8434939976 
bot = telebot.TeleBot(TOKEN)

# ================= RENDER KEEP-ALIVE (EKSTRA) =================
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

# ================= DATABASE (DOKUNULMADI) =================
db = sqlite3.connect("data.db", check_same_thread=False)
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    premium INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    bot_name TEXT,
    running INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'
)
""")

sql.execute("PRAGMA table_info(bots)")
columns = [info[1] for info in sql.fetchall()]
if "status" not in columns:
    sql.execute("ALTER TABLE bots ADD COLUMN status TEXT DEFAULT 'pending'")

db.commit()

running_processes = {}
bot_logs = {}
admin_step = {}
support_wait = {}
announce_wait = {}

# ================= MENÜLER (DOKUNULMADI) =================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📦 Modül Yükle")
    kb.add("📂 Dosya Yükle")
    kb.add("📂 Dosyalarım")
    kb.add("📞 Destek & İletişim")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⭐ Premium Ver", "👤 Kullanıcı Yasakla / Aç")
    kb.add("🤖 Aktif Botlar")
    kb.add("⛔ Bot Kapat")
    kb.add("🛑 Tüm Botları Kapat")
    kb.add("📢 Duyuru Gönder")
    kb.add("⬅️ Çıkış")
    return kb

def add_log(bot_id, text):
    if bot_id not in bot_logs:
        bot_logs[bot_id] = []
    bot_logs[bot_id].append(text)

# ================= START (PROFİL FOTOĞRAFI EKLENDİ) =================
@bot.message_handler(commands=["start"])
def start(message):
    u = message.from_user
    uid = u.id

    sql.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    if not sql.fetchone():
        sql.execute("INSERT INTO users (user_id,name) VALUES (?,?)", (uid, u.first_name))
        db.commit()

    sql.execute("SELECT premium,banned FROM users WHERE user_id=?", (uid,))
    res = sql.fetchone()
    premium, banned = res[0], res[1]

    if banned:
        bot.send_message(uid, "🚫 Hesabınız yasaklandı.")
        return

    sql.execute("SELECT COUNT(*) FROM bots WHERE user_id=?", (uid,))
    count = sql.fetchone()[0]

    status = "⭐ Premium Kullanıcı" if premium else "🆓 Ücretsiz Kullanıcı"
    limit = "Sınırsız" if premium else "3"

    text = f"""
〽️ Hoş Geldiniz, {u.first_name}!

👤 Durumunuz: {status}
📁 Dosya Sayınız: {count} / {limit}

🤖 Bu bot Python (.py) betiklerini çalıştırmak için tasarlanmıştır.

👇 Butonları kullanın.
"""
    # Kendi fotosunu çekip gönderme kısmı burada
    try:
        photos = bot.get_user_profile_photos(uid, limit=1)
        if photos.total_count > 0:
            bot.send_photo(uid, photos.photos[0][0].file_id, caption=text, reply_markup=main_menu())
        else:
            bot.send_message(uid, text, reply_markup=main_menu())
    except:
        bot.send_message(uid, text, reply_markup=main_menu())

# ================= ADMIN PANEL VE DUYURU (DOKUNULMADI) =================
@bot.message_handler(commands=["adminpanel"])
def adminpanel(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "👑 Admin Panel", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "📢 Duyuru Gönder" and m.from_user.id == ADMIN_ID)
def announce_prompt(message):
    announce_wait[message.from_user.id] = True
    bot.send_message(message.chat.id, "📢 Duyuruyu yazın:")

@bot.message_handler(func=lambda m: m.from_user.id in announce_wait)
def announce_send(message):
    try: del announce_wait[message.from_user.id]
    except: pass
    duyuru_text = message.text
    sql.execute("SELECT user_id FROM users")
    rows = sql.fetchall()
    sent = 0
    for (uid,) in rows:
        try:
            bot.send_message(uid, f"📢 *Duyuru*\n\n{duyuru_text}", parse_mode="Markdown")
            sent += 1
        except: pass
    bot.send_message(ADMIN_ID, f"📢 Duyuru bitti. {sent} kişiye gitti.")

# ================= DİĞER TÜM ÖZELLİKLER (MODÜL, DOSYA, PREM...) =================
@bot.message_handler(func=lambda m: m.text == "📦 Modül Yükle")
def mod_prompt(message):
    msg = bot.send_message(message.chat.id, "📦 pip modül adı gir:")
    bot.register_next_step_handler(msg, mod_install)

def mod_install(message):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", message.text])
        bot.send_message(message.chat.id, "✅ Modül yüklendi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Hata: {e}")

@bot.message_handler(func=lambda m: m.text == "📂 Dosya Yükle")
def upload_prompt(message):
    bot.send_message(message.chat.id, ".py dosyanızı gönderin")

@bot.message_handler(content_types=["document"])
def upload(message):
    if not message.document.file_name.endswith(".py"):
        return bot.reply_to(message, "❌ Sadece .py kabul edilir")
    uid = message.from_user.id
    sql.execute("SELECT premium FROM users WHERE user_id=?", (uid,))
    premium = sql.fetchone()[0]
    sql.execute("SELECT COUNT(*) FROM bots WHERE user_id=?", (uid,))
    if not premium and sql.fetchone()[0] >= 3:
        return bot.reply_to(message, "❌ Limit dolu.")

    file = bot.get_file(message.document.file_id)
    data = bot.download_file(file.file_path)
    filename = message.document.file_name
    with open(filename, "wb") as f: f.write(data)

    sql.execute("INSERT INTO bots (user_id, bot_name, status) VALUES (?, ?, 'pending')", (uid, filename))
    db.commit()
    bot_id = sql.lastrowid

    bot.reply_to(message, "✅ Admin onayı bekleniyor.")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Onayla", callback_data=f"approve_{bot_id}"),
           types.InlineKeyboardButton("❌ Reddet", callback_data=f"reject_{bot_id}"))
    bot.send_document(ADMIN_ID, data, visible_file_name=filename, caption=f"📂 Yeni Dosya\n👤 {message.from_user.first_name}\n🆔 {uid}", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📂 Dosyalarım")
def files(message):
    uid = message.from_user.id
    sql.execute("SELECT id, bot_name, running, status FROM bots WHERE user_id=?", (uid,))
    rows = sql.fetchall()
    if not rows: return bot.send_message(uid, "📂 Dosya yok.")
    for bot_id, bot_name, running, status in rows:
        durum = "⏳ Onay Bekliyor" if status == 'pending' else ("Çalışıyor ✅" if running else "Duruyor ⏸️")
        kb = types.InlineKeyboardMarkup()
        if status == 'approved':
            kb.row(types.InlineKeyboardButton("▶️ Başlat", callback_data=f"start_{bot_id}"),
                   types.InlineKeyboardButton("⛔ Durdur", callback_data=f"stop_{bot_id}"))
            kb.row(types.InlineKeyboardButton("❌ Sil", callback_data=f"delete_{bot_id}"),
                   types.InlineKeyboardButton("📄 Log", callback_data=f"log_{bot_id}"))
        else: kb.add(types.InlineKeyboardButton("❌ Sil", callback_data=f"delete_{bot_id}"))
        bot.send_message(uid, f"📄 {bot_name}\nDurum: {durum}", reply_markup=kb)

# ================= CALLBACK & LOG (DOKUNULMADI) =================
def run_bot_with_log(bot_id, filename):
    def target():
        try:
            proc = subprocess.Popen([sys.executable, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            running_processes[bot_id] = proc
            sql.execute("UPDATE bots SET running=1 WHERE id=?", (bot_id,))
            db.commit()
            add_log(bot_id, "Bot başlatıldı ✅")
            for line in proc.stdout: add_log(bot_id, line.strip())
            for line in proc.stderr: add_log(bot_id, line.strip())
        except Exception as e: add_log(bot_id, f"Hata: {e}")
    threading.Thread(target=target, daemon=True).start()

@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    try:
        action, b_id = call.data.split("_", 1)
        bot_id = int(b_id)
        uid = call.from_user.id
    except: return

    if action == "approve" and uid == ADMIN_ID:
        sql.execute("UPDATE bots SET status='approved' WHERE id=?", (bot_id,))
        db.commit()
        bot.answer_callback_query(call.id, "Onaylandı")
    elif action == "start":
        sql.execute("SELECT bot_name FROM bots WHERE id=?", (bot_id,))
        run_bot_with_log(bot_id, sql.fetchone()[0])
        bot.answer_callback_query(call.id, "Başlatıldı")
    elif action == "stop":
        if bot_id in running_processes:
            running_processes[bot_id].terminate()
            del running_processes[bot_id]
        sql.execute("UPDATE bots SET running=0 WHERE id=?", (bot_id,))
        db.commit()
        bot.answer_callback_query(call.id, "Durduruldu")
    elif action == "log":
        logs = bot_logs.get(bot_id, ["Henüz log yok"])
        bot.send_message(uid, "📄 Loglar:\n" + "\n".join(logs[-20:]))
    elif action == "delete":
        sql.execute("DELETE FROM bots WHERE id=?", (bot_id,))
        db.commit()
        bot.answer_callback_query(call.id, "Silindi")

@bot.message_handler(func=lambda m: m.text == "📞 Destek & İletişim")
def support(message):
    support_wait[message.from_user.id] = True
    bot.send_message(message.chat.id, "✍️ Mesajınızı yazın:")

@bot.message_handler(func=lambda m: m.from_user.id in support_wait)
def support_msg(message):
    del support_wait[message.from_user.id]
    bot.send_message(ADMIN_ID, f"📩 Destek: {message.from_user.first_name} ({message.from_user.id})\n\n{message.text}")
    bot.send_message(message.chat.id, "✅ İletildi.")

@bot.message_handler(func=lambda m: m.text == "⬅️ Çıkış" and m.from_user.id == ADMIN_ID)
def exit_admin(message):
    bot.send_message(message.chat.id, "Çıkıldı.", reply_markup=main_menu())

print("BOT AKTİF...")
bot.infinity_polling()
