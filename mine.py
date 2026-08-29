import os
import threading
import sqlite3
import telebot
from flask import Flask
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from google import genai

TOKEN = "8940117200:AAEA2wM-TAegbSPj9sy6wPY-u54qgi_hplQ"
ADMIN_ID = 8744592769

bot = telebot.TeleBot(TOKEN)

# تهيئة عميل Gemini API
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# قاموس لتخزين جلسات الاختبار الحالية للطلاب
user_quiz_sessions = {}

# --- خادم Flask لإبقاء UptimeRobot شغال ومنع خطأ 503 على Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- قاعدة البيانات ---
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

def main_keyboard(user_id):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton("تسجيلات مكتوبة"),
        KeyboardButton("تسجيلات صوتية"),
        KeyboardButton("ملخصي"),
        KeyboardButton("امتحانات سابقة"),
        KeyboardButton("تواصل معي (مجهول)")
    )
    if int(user_id) == ADMIN_ID:
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

@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if int(message.from_user.id) == ADMIN_ID:
        send_admin_panel(message.chat.id)

def send_admin_panel(chat_id):
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
    bot.send_message(chat_id, admin_text, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_lecture(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    
    try:
        # قراءة النص كاملاً بعد الأمر /add
        text_without_cmd = message.text.strip().split(maxsplit=1)[1]
        parts = text_without_cmd.split()
        
        section = parts[0]           # wrt, aud, sum, ex
        lec_num = int(parts[-1])      # الكلمة الأخيرة هي دائماً رقم المحاضرة
        subject = " ".join(parts[1:-1]) # الكلمات التي في الوسط هي اسم المادة (سواء كلمة أو كلمتين)

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
            bot.reply_to(message, f"✅ تم حفظ المحاضرة {lec_num} لمادة [{subject}] بنجاح!")
        else:
            bot.reply_to(message, "❌ يرجى الرد على ملف، تسجيل صوتي، أو صورة مع الأمر.")
    except Exception as e:
        bot.reply_to(message, "⚠️ صيغة الأمر خطأ!\nدير رد على الملف/الصورة واكتب:\n`/add wrt مدخل قانون 1`", parse_mode="Markdown")

@bot.message_handler(commands=['delete'])
def delete_lecture(message):
    if int(message.from_user.id) != ADMIN_ID:
        return
    
    try:
        text_without_cmd = message.text.strip().split(maxsplit=1)[1]
        parts = text_without_cmd.split()
        
        section = parts[0]
        lec_num = int(parts[-1])
        subject = " ".join(parts[1:-1])

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lecture_files WHERE section=? AND subject=? AND lecture_num=?", (section, subject, lec_num))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            bot.reply_to(message, f"🗑️ تم حذف المحاضرة {lec_num} لمادة [{subject}] بنجاح!")
        else:
            bot.reply_to(message, "❌ لم يتم العثور على هذه المحاضرة.")
    except Exception as e:
        bot.reply_to(message, "⚠️ صيغة الأمر خطأ!\nاكتب الأمر بهذا الشكل:\n`/delete wrt مدخل قانون 1`", parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = int(message.from_user.id)

    if user_id in user_quiz_sessions:
        handle_quiz_answer(message)
        return

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
    elif "لوحة التحكم" in text and user_id == ADMIN_ID:
        send_admin_panel(message.chat.id)

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
        
        quiz_markup = InlineKeyboardMarkup()
        quiz_btn = InlineKeyboardButton("🧠 اختبر نفسك في هذه المحاضرة (AI)", callback_data=f"quiz_{section}_{sub_idx}_{lec_num}")
        quiz_markup.add(quiz_btn)

        bot.send_message(
            call.message.chat.id, 
            f"✅ تم إرسال محتوى المحاضرة {lec_num}.\nتريد تراجع فهمك؟ اضغط على الزر أسفله للبدء في امتحان تحليلي ذكي!",
            reply_markup=quiz_markup
        )
        bot.answer_callback_query(call.id, text=f"تم إرسال المحاضرة {lec_num}")

    elif data[0] == "quiz":
        section = data[1]
        sub_idx = int(data[2])
        lec_num = int(data[3])
        subject_name = SUBJECTS[sub_idx]
        user_id = call.from_user.id

        bot.send_message(call.message.chat.id, "⏳ جاري تحميل المحاضرة وتوليد الأسئلة الذكية عبر Gemini... يرجى الانتظار لحظات.")

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type FROM lecture_files WHERE section=? AND subject=? AND lecture_num=? LIMIT 1", (section, subject_name, lec_num))
        row = cursor.fetchone()
        conn.close()

        if not row:
            bot.send_message(call.message.chat.id, "❌ لم يتم العثور على ملفات لهذا القسم لبدء الاختبار.")
            return

        file_id, file_type = row

        try:
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            ext = ".pdf" if file_type == "doc" else ".ogg" if file_type == "audio" else ".jpg"
            local_filename = f"temp_{user_id}{ext}"
            
            with open(local_filename, 'wb') as new_file:
                new_file.write(downloaded_file)

            uploaded_file = gemini_client.files.upload(file=local_filename)

            prompt = """
            أنت أستاذ قانون ومتمكن. قم بتحليل هذا المستند/التسجيل واستخرج منه 5 أسئلة مقالية تحليليّة متوسطة إلى صعبة تقيس فهم طالب القانون.
            أخرج النتائج فقط كقائمة مفصولة برقم كل سؤال، دون مقدمات أو إجابات.
            """

            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[uploaded_file, prompt]
            )

            raw_questions = response.text.strip().split("\n")
            questions = [q.strip() for q in raw_questions if q.strip()]

            if os.path.exists(local_filename):
                os.remove(local_filename)

            if not questions:
                bot.send_message(call.message.chat.id, "⚠️ تعذر استخراج أسئلة من هذا الملف.")
                return

            user_quiz_sessions[user_id] = {
                "questions": questions,
                "current_step": 0,
                "gemini_file": uploaded_file
            }

            bot.send_message(
                call.message.chat.id,
                f"🎯 **بدء الاختبار الذكي لمادة {subject_name} - محاضرة {lec_num}**\n\n"
                f"📌 **السؤال (1/{len(questions)}):**\n{questions[0]}\n\n"
                "✍️ اكتب إجابتك بأسلوبك ورسّلها في محادثة البوت فوراً:",
                parse_mode="Markdown"
            )

        except Exception as e:
            bot.send_message(call.message.chat.id, f"⚠️ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {str(e)}")


def handle_quiz_answer(message):
    user_id = message.from_user.id
    session = user_quiz_sessions[user_id]

    current_idx = session["current_step"]
    questions = session["questions"]
    current_question = questions[current_idx]
    student_answer = message.text

    bot.send_message(message.chat.id, "🔍 جاري تقييم إجابتك وقراءتها بواسطة الذكاء الاصطناعي...")

    try:
        eval_prompt = f"""
        السؤال القانوني: {current_question}
        إجابة الطالب: {student_answer}

        قم بتقييم إجابة الطالب بأسلوب أستاذ قانون مشجع ومحترف:
        1. حدد التقييم (مثلاً: صحيحة، صحيحة جزئياً، أو خاطئة مع نسبة تقريبية).
        2. وضح الأخطاء أو التكييفات القانونية التي فاتته.
        3. قدم الإجابة النموذجية القانونية المختصرة.
        """

        eval_response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[session["gemini_file"], eval_prompt]
        )

        bot.send_message(message.chat.id, f"📝 **نتيجة التقييم:**\n\n{eval_response.text}", parse_mode="Markdown")

        session["current_step"] += 1

        if session["current_step"] < len(questions):
            next_idx = session["current_step"]
            next_q = questions[next_idx]
            bot.send_message(
                message.chat.id,
                f"📌 **السؤال ({next_idx + 1}/{len(questions)}):**\n{next_q}\n\n"
                "✍️ اكتب إجابتك أدناه:",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(message.chat.id, "🎉 **أحسنت! أكملت جميع أسئلة هذا الاختبار.**\nيمكنك العودة للمكتبة وتصفح بقية المواد الآن.")
            del user_quiz_sessions[user_id]

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ حدث خطأ أثناء التقييم: {str(e)}")


if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.infinity_polling()
