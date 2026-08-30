import os
import threading
import sqlite3
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from google import genai

# --- البيانات الخاصة بالبوت ---
API_ID = 39769241
API_HASH = "7006f661e91dfbee21acce80eb57935e"
BOT_TOKEN = "8940117200:AAEA2wM-TAegbSPj9sy6wPY-u54qgi_hplQ"
ADMIN_ID = 8744592769

app_bot = Client("law_library_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

user_quiz_sessions = {}

# --- خادم Flask ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

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

SECTION_MAP = {
    "مكتوب": "wrt",
    "كتابه": "wrt",
    "تفريغ": "wrt",
    "صوت": "aud",
    "صوتي": "aud",
    "تسجيل": "aud",
    "ملخص": "sum",
    "ملخصي": "sum",
    "امتحان": "ex",
    "امتحانات": "ex"
}

def normalize_text(text):
    words = text.strip().split()
    clean_words = []
    for w in words:
        if w.startswith("ال") and len(w) > 2:
            clean_words.append(w[2:])
        else:
            clean_words.append(w)
    return " ".join(sorted(clean_words))

def parse_arabic_command(text):
    parts = text.strip().split()
    if len(parts) < 4:
        return None, None, None
        
    sec_word = parts[1]
    section = SECTION_MAP.get(sec_word)
    
    if not section:
        return None, None, None
    
    lec_num = None
    subject_words = []
    
    for part in parts[2:]:
        if part.isdigit() and lec_num is None:
            lec_num = int(part)
        else:
            subject_words.append(part)
            
    subject = " ".join(subject_words)
    return section, subject, lec_num

def main_keyboard(user_id):
    buttons = [
        [KeyboardButton("تسجيلات مكتوبة"), KeyboardButton("تسجيلات صوتية")],
        [KeyboardButton("ملخصي"), KeyboardButton("امتحانات سابقة")],
        [KeyboardButton("تواصل معي (مجهول)")]
    ]
    if int(user_id) == ADMIN_ID:
        buttons.append([KeyboardButton("لوحة التحكم ⚙️")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def subjects_keyboard(section_prefix):
    buttons = []
    for i in range(0, len(SUBJECTS), 2):
        row = [InlineKeyboardButton(SUBJECTS[i], callback_data=f"sub_{section_prefix}_{i}")]
        if i + 1 < len(SUBJECTS):
            row.append(InlineKeyboardButton(SUBJECTS[i+1], callback_data=f"sub_{section_prefix}_{i+1}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def lectures_keyboard(section, subject_index):
    subject_name = SUBJECTS[subject_index]
    norm_subject = normalize_text(subject_name)
    
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT subject, lecture_num FROM lecture_files WHERE section=?", (section,))
    rows = cursor.fetchall()
    conn.close()

    lecture_nums = set()
    for db_sub, lec_num in rows:
        if normalize_text(db_sub) == norm_subject:
            lecture_nums.add(lec_num)

    sorted_lecs = sorted(list(lecture_nums))

    if not sorted_lecs:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لا توجد محاضرات مرفوعة حالياً", callback_data="empty")]])
    
    buttons = []
    for i in range(0, len(sorted_lecs), 2):
        row = [InlineKeyboardButton(f"محاضرة {sorted_lecs[i]}", callback_data=f"lec_{section}_{subject_index}_{sorted_lecs[i]}")]
        if i + 1 < len(sorted_lecs):
            row.append(InlineKeyboardButton(f"محاضرة {sorted_lecs[i+1]}", callback_data=f"lec_{section}_{subject_index}_{sorted_lecs[i+1]}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

@app_bot.on_message(filters.command("start"))
async def send_welcome(client, message):
    welcome_text = (
        "أهلا وسهلا بك في بوت المكتبة الدراسية 🎓\n\n"
        "طريق النجاح يبدأ بخطوة، ونحن هنا لنكون معك في كل خطوة 📚⚡\n\n"
        "يرجى اختيار القسم الذي تود الاطلاع عليه أدناه 👇"
    )
    await message.reply_text(welcome_text, reply_markup=main_keyboard(message.from_user.id))

# زر لوحة التحكم للمشرف - إرسال أوانر قابلة للنسخ بنقرة واحدة
@app_bot.on_message(filters.text & filters.user(ADMIN_ID) & filters.regex(r"لوحة التحكم ⚙️"))
async def admin_panel(client, message):
    panel_text = (
        "🛠️ **لوحة التحكم (اضغط على أي أمر لنسخه فوراً):**\n\n"
        "📥 **أوامر الإضافة (دير رد Reply على الملف):**\n"
        "`اضف مكتوب مدخل قانون 1`\n"
        "`اضف صوت مدخل قانون 1`\n"
        "`اضف ملخص مدخل قانون 1`\n"
        "`اضف امتحان مدخل قانون 1`\n\n"
        "🗑️ **أوامر الحذف (ارسلها مباشرة):**\n"
        "`احذف مكتوب مدخل قانون 1`\n"
        "`احذف صوت مدخل قانون 1`\n"
        "`احذف ملخص مدخل قانون 1`\n"
        "`احذف امتحان مدخل قانون 1`"
    )
    await message.reply_text(panel_text, parse_mode="markdown")

# أمر الإضافة بالعربي
@app_bot.on_message(filters.text & filters.user(ADMIN_ID) & filters.regex(r"^اضف"))
async def add_lecture(client, message):
    try:
        section, subject, lec_num = parse_arabic_command(message.text)

        if not section or not subject or lec_num is None:
            await message.reply_text(
                "⚠️ اكتب الأمر بالصيغة الصحيحة:\n`اضف مكتوب مدخل قانون 1`", 
                parse_mode="markdown"
            )
            return

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
                file_id = target.photo.file_id
                file_type = "photo"

        if file_id:
            conn = sqlite3.connect("bot_data.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO lecture_files (section, subject, lecture_num, file_id, file_type) VALUES (?, ?, ?, ?, ?)",
                           (section, subject, lec_num, file_id, file_type))
            conn.commit()
            conn.close()
            await message.reply_text(f"✅ تم حفظ المحاضرة {lec_num} بنجاح لمادة [{subject}]!")
        else:
            await message.reply_text("❌ يرجى الرد (Reply) على الملف أو التسجيل عند كتابة الأمر.")
    except Exception as e:
        await message.reply_text(f"⚠️ حدث خطأ: {str(e)}")

# أمر الحذف بالعربي
@app_bot.on_message(filters.text & filters.user(ADMIN_ID) & filters.regex(r"^احذف"))
async def delete_lecture(client, message):
    try:
        section, subject, lec_num = parse_arabic_command(message.text)

        if not section or not subject or lec_num is None:
            await message.reply_text(
                "⚠️ اكتب أمر الحذف بالصيغة الصحيحة:\n`احذف مكتوب مدخل قانون 1`", 
                parse_mode="markdown"
            )
            return

        norm_subject = normalize_text(subject)

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, subject FROM lecture_files WHERE section=? AND lecture_num=?", (section, lec_num))
        rows = cursor.fetchall()

        deleted_count = 0
        for row_id, db_sub in rows:
            if normalize_text(db_sub) == norm_subject:
                cursor.execute("DELETE FROM lecture_files WHERE id=?", (row_id,))
                deleted_count += 1

        conn.commit()
        conn.close()

        if deleted_count > 0:
            await message.reply_text(f"🗑️ تم حذف المحاضرة {lec_num} لمادة [{subject}] بنجاح.")
        else:
            await message.reply_text("❌ لم يتم العثور على محاضرة بهذا الاسم والرقم لحذفها.")
    except Exception as e:
        await message.reply_text(f"⚠️ حدث خطأ أثناء الحذف: {str(e)}")

@app_bot.on_message(filters.text)
async def handle_menu(client, message):
    user_id = message.from_user.id

    if user_id in user_quiz_sessions:
        await handle_quiz_answer(client, message)
        return

    text = message.text
    if "تسجيلات مكتوبة" in text:
        await message.reply_text("📚 اختر المادة:", reply_markup=subjects_keyboard("wrt"))
    elif "تسجيلات صوتية" in text:
        await message.reply_text("🎙️ اختر المادة:", reply_markup=subjects_keyboard("aud"))
    elif "ملخصي" in text:
        await message.reply_text("📌 اختر المادة:", reply_markup=subjects_keyboard("sum"))
    elif "امتحانات سابقة" in text:
        await message.reply_text("📝 اختر المادة:", reply_markup=subjects_keyboard("ex"))
    elif "مجهول" in text:
        await message.reply_text("https://t.me/majho1bot")

@app_bot.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data.split("_")
    
    if data[0] == "empty":
        await callback_query.answer("لم يتم رفع محاضرات لهذه المادة بعد.", show_alert=True)
        return

    if data[0] == "sub":
        section = data[1]
        sub_idx = int(data[2])
        await callback_query.edit_message_text(
            f"📖 مادة **{SUBJECTS[sub_idx]}**\nاختر المحاضرة:",
            reply_markup=lectures_keyboard(section, sub_idx)
        )

    elif data[0] == "lec":
        section = data[1]
        sub_idx = int(data[2])
        lec_num = int(data[3])
        subject_name = SUBJECTS[sub_idx]
        norm_subject = normalize_text(subject_name)

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type, subject FROM lecture_files WHERE section=? AND lecture_num=?", (section, lec_num))
        rows = cursor.fetchall()
        conn.close()

        files = [(f_id, f_type) for f_id, f_type, db_sub in rows if normalize_text(db_sub) == norm_subject]

        for f_id, f_type in files:
            if f_type == "doc":
                await client.send_document(callback_query.message.chat.id, f_id)
            elif f_type == "audio":
                await client.send_audio(callback_query.message.chat.id, f_id)
            elif f_type == "photo":
                await client.send_photo(callback_query.message.chat.id, f_id)
        
        quiz_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🧠 اختبر نفسك في هذه المحاضرة (AI)", callback_data=f"quiz_{section}_{sub_idx}_{lec_num}")]])
        await callback_query.message.reply_text(
            f"✅ تم إرسال محتوى المحاضرة {lec_num}.\nتريد تراجع فهمك؟ اضغط على الزر أسفله للبدء في امتحان تحليلي ذكي!",
            reply_markup=quiz_markup
        )

    elif data[0] == "quiz":
        section = data[1]
        sub_idx = int(data[2])
        lec_num = int(data[3])
        subject_name = SUBJECTS[sub_idx]
        norm_subject = normalize_text(subject_name)
        user_id = callback_query.from_user.id

        await callback_query.message.reply_text("⏳ جاري تنزيل المحاضرة الصوتية/الملف مهما كان حجمه وتوليد الأسئلة الذكية عبر Gemini... يرجى الانتظار.")

        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type, subject FROM lecture_files WHERE section=? AND lecture_num=?", (section, lec_num))
        rows = cursor.fetchall()
        conn.close()

        matching_files = [(f_id, f_type) for f_id, f_type, db_sub in rows if normalize_text(db_sub) == norm_subject]

        if not matching_files:
            await callback_query.message.reply_text("❌ لم يتم العثور على ملفات لهذا القسم لبدء الاختبار.")
            return

        file_id, file_type = matching_files[0]

        try:
            local_filename = await client.download_media(file_id, file_name=f"temp_{user_id}")
            
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

            user_quiz_sessions[user_id] = {
                "questions": questions,
                "current_step": 0,
                "gemini_file": uploaded_file
            }

            await callback_query.message.reply_text(
                f"🎯 **بدء الاختبار الذكي لمادة {subject_name} - محاضرة {lec_num}**\n\n"
                f"📌 **السؤال (1/{len(questions)}):**\n{questions[0]}\n\n"
                "✍️ اكتب إجابتك بأسلوبك ورسّلها في محادثة البوت فوراً:"
            )

        except Exception as e:
            await callback_query.message.reply_text(f"⚠️ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {str(e)}")

async def handle_quiz_answer(client, message):
    user_id = message.from_user.id
    session = user_quiz_sessions[user_id]

    current_idx = session["current_step"]
    questions = session["questions"]
    current_question = questions[current_idx]
    student_answer = message.text

    await message.reply_text("🔍 جاري تقييم إجابتك وقراءتها بواسطة الذكاء الاصطناعي...")

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

        await message.reply_text(f"📝 **نتيجة التقييم:**\n\n{eval_response.text}")

        session["current_step"] += 1

        if session["current_step"] < len(questions):
            next_idx = session["current_step"]
            next_q = questions[next_idx]
            await message.reply_text(
                f"📌 **السؤال ({next_idx + 1}/{len(questions)}):**\n{next_q}\n\n"
                "✍️ اكتب إجابتك أدناه:"
            )
        else:
            await message.reply_text("🎉 **أحسنت! أكملت جميع أسئلة هذا الاختبار.**\nيمكنك العودة للمكتبة وتصفح بقية المواد الآن.")
            del user_quiz_sessions[user_id]

    except Exception as e:
        await message.reply_text(f"⚠️ حدث خطأ أثناء التقييم: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    app_bot.run()
