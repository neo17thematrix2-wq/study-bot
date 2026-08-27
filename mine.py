import telebot
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8940117200:AAEA2wM-TAegbSPj9sy6wPY-u54qgi_hplQ"
ADMIN_ID = 8744592769

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lecture_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section TEXT,
            subject TEXT,
            lecture_num INTEGER,
            file_id TEXT,
            file_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

SUBJECTS = ["مدخل قانون", "قانون دستوري", "قانون جنائي", "قانون مدني", "قانون إداري", "قانون دولي"]

# الأزرار الرئيسية (تظهر لوحة التحكم للأدمن فقط)
def main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("تسجيلات مكتوبة"),
        KeyboardButton("تسجيلات صوتية"),
        KeyboardButton("ملخصي"),
        KeyboardButton("امتحانات سابقة"),
        KeyboardButton("تواصل معي (مجهول)")
    )
    if user_id == ADMIN_ID:
        markup.add(KeyboardButton("لوحة التحكم ⚙️"))
    return markup

def subjects_keyboard(section_prefix):
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(sub, callback_data=f"sub_{section_prefix}_{i}") for i, sub in enumerate(SUBJECTS)]
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.row(buttons[i], buttons[i+1])
        else:
            markup.row(buttons[i])
    return markup

def lectures_keyboard(section, subject_index):
    subject_name = SUBJECTS[subject_index]
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT lecture_num FROM lecture_files WHERE section=? AND subject=? ORDER BY lecture_num ASC", (section, subject_name))
    rows = cursor.fetchall()
    conn.close()

    markup = InlineKeyboardMarkup(row_width=2)
    if not rows:
        markup.add(InlineKeyboardButton("❌ لا توجد محاضرات مرفوعة حالياً", callback_data="empty"))
    else:
        buttons = [InlineKeyboardButton(f"محاضرة {r[0]}", callback_data=f"lec_{section}_{subject_index}_{r[0]}") for r in rows]
        for i in range(0, len(buttons), 2):
            if i + 1 < len(buttons):
                markup.row(buttons[i], buttons[i+1])
            else:
                markup.row(buttons[i])
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "أهلا وسهلا بك في بوت المكتبة الدراسية 🎓\n\n"
        "طريق النجاح يبدأ بخطوة، ونحن هنا لنكون معك في كل خطوة 📚⚡\n\n"
        "يرجى اختيار القسم الذي تود الاطلاع عليه أدناه 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_keyboard(message.from_user.id))

@bot.message_handler(commands=['add'])
def add_lecture(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.split(maxsplit=3)
        section = parts[1]
        subject = parts[2]
        lec_num = int(parts[3])

        file_id = None
        file_type = None

        if message.reply_to_message:
            target = message.reply_to_message
            if target.document:
                file_id = target.document.file_id
                file_type = "doc"
            elif target.audio or target.voice:
                file_id = (target.audio or target.voice).file_id
                file_type = "audio"
            elif target.photo:
                file_id = target.photo[-1].file_id
                file_type = "photo"

        if file_id:
            conn = sqlite3.connect("bot_data.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO lecture_files (section, subject, lecture_num, file_id, file_type) VALUES (?, ?, ?, ?, ?)",
                           (section, subject, lec_num, file_id, file_type))
            conn.commit()
            conn.close()
            bot.reply_to(message, f"✅ تم حفظ المحاضرة {lec_num} لمادة {subject} بنجاح!")
        else:
            bot.reply_to(message, "❌ يرجى الرد على ملف، تسجيل صوتي، أو صورة مع الأمر.")
    except Exception as e:
        bot.reply_to(message, "⚠️ صيغة الأمر خطأ!\nدير رد على الملف/الصورة واكتب:\n`/add wrt مدخل قانون 1`", parse_mode="Markdown")

@bot.message_handler(commands=['delete'])
def delete_lecture(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.split(maxsplit=3)
        section = parts[1]
        subject = parts[2]
        lec_num = int(parts[3])

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lecture_files WHERE section=? AND subject=? AND lecture_num=?", (section, subject, lec_num))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            bot.reply_to(message, f"🗑️ تم حذف المحاضرة {lec_num} لمادة {subject} بنجاح!")
        else:
            bot.reply_to(message, "❌ لم يتم العثور على هذه المحاضرة.")
    except Exception as e:
        bot.reply_to(message, "⚠️ صيغة الأمر خطأ!\nاكتب الأمر بهذا الشكل:\n`/delete wrt مدخل قانون 1`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    if "تسجيلات مكتوبة" in text:
        bot.send_message(message.chat.id, "📚 اختر المادة:", reply_markup=subjects_keyboard("wrt"))
    elif "تسجيلات صوتية" in text:
        bot.send_message(message.chat.id, "🎙️ اختر المادة:", reply_markup=subjects_keyboard("aud"))
    elif "ملخصي" in text:
        bot.send_message(message.chat.id, "📌 اختر المادة:", reply_markup=subjects_keyboard("sum"))
    elif "امتحانات سابقة" in text:
        bot.send_message(message.chat.id, "📝 اختر المادة:", reply_markup=subjects_keyboard("ex"))
    elif "مجهول" in text:
        bot.send_message(message.chat.id, "https://t.me/majho1bot")
    elif "لوحة التحكم" in text and message.from_user.id == ADMIN_ID:
        admin_text = (
            "🛠️ **دليل أوامر لوحة التحكم (للأدمن فقط)**\n\n"
            "📥 **إضافة محتوى:** (دير رد Reply على الملف/الصورة واكتب):\n"
            "`/add [القسم] [اسم المادة] [رقم المحاضرة]`\n\n"
            "🗑️ **حذف محتوى:** (اكتب مباشرة):\n"
            "`/delete [القسم] [اسم المادة] [رقم المحاضرة]`\n\n"
            "🏷️ **اختصارات الأقسام:**\n"
            "• `wrt` = تسجيلات مكتوبة\n"
            "• `aud` = تسجيلات صوتية\n"
            "• `sum` = ملخصي\n"
            "• `ex` = امتحانات سابقة\n\n"
            "📋 **أمثلة جاهزة للنسخ:**\n"
            "📜 `/add wrt مدخل قانون 1`\n"
            "🎙️ `/add aud مدخل قانون 1`\n"
            "📌 `/add sum مدخل قانون 1`\n"
            "📝 `/add ex مدخل قانون 1`"
        )
        bot.send_message(message.chat.id, admin_text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == "empty":
        bot.answer_callback_query(call.id, text="لم يتم رفع محاضرات لهذه المادة بعد.")
        return

    data = call.data.split("_")
    
    if data[0] == "sub":
        section = data[1]
        sub_idx = int(data[2])
        bot.edit_message_text(f"📖 مادة **{SUBJECTS[sub_idx]}**\nاختر المحاضرة:", 
                              call.message.chat.id, call.message.message_id, 
                              parse_mode="Markdown", reply_markup=lectures_keyboard(section, sub_idx))

    elif data[0] == "lec":
        section = data[1]
        sub_idx = int(data[2])
        lec_num = int(data[3])
        subject_name = SUBJECTS[sub_idx]

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type FROM lecture_files WHERE section=? AND subject=? AND lecture_num=?", (section, subject_name, lec_num))
        files = cursor.fetchall()
        conn.close()

        for f_id, f_type in files:
            if f_type == "doc":
                bot.send_document(call.message.chat.id, f_id)
            elif f_type == "audio":
                bot.send_audio(call.message.chat.id, f_id)
            elif f_type == "photo":
                bot.send_photo(call.message.chat.id, f_id)
        
        bot.answer_callback_query(call.id, text=f"تم إرسال المحاضرة {lec_num}")

if __name__ == "__main__":
    bot.infinity_polling()
