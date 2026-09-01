import os
import sqlite3
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from google import genai

API_ID = 39769241
API_HASH = "7006f661e91dfbee21acce80eb57935e"
BOT_TOKEN = "8940117200:AAHJYREfLAYdDPtBf9aNWYffNpM5qyZZz48"
ADMIN_ID = 8744592769

app_bot = Client("law_library_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

user_quiz_sessions = {}

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
SECTION_MAP = {"شيت": "sheet", "شيتات": "sheet", "صوت": "aud", "صوتي": "aud", "تسجيل": "aud", "تسجيلات": "aud", "ملخص": "summary", "ملخصي": "summary", "امتحان": "ex", "امتحانات": "ex"}

def normalize_text(text):
    words = text.strip().split()
    clean_words = [w[2:] if w.startswith("ال") and len(w) > 2 else w for w in words]
    return " ".join(sorted(clean_words))

def parse_arabic_command(text):
    parts = text.strip().split()
    if len(parts) < 4: return None, None, None
    section = SECTION_MAP.get(parts[1])
    if not section: return None, None, None
    lec_num, subject_words = None, []
    for part in parts[2:]:
        if part.isdigit() and lec_num is None: lec_num = int(part)
        else: subject_words.append(part)
    return section, " ".join(subject_words), lec_num

def main_keyboard(user_id):
    buttons = [[KeyboardButton("تسجيلات صوتية"), KeyboardButton("شيتات")], [KeyboardButton("ملخصي"), KeyboardButton("امتحانات سابقة")], [KeyboardButton("تواصل معي (مجهول)")]]
    if int(user_id) == ADMIN_ID: buttons.append([KeyboardButton("لوحة التحكم ⚙️")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def subjects_keyboard(section_prefix):
    buttons = []
    for i in range(0, len(SUBJECTS), 2):
        row = [InlineKeyboardButton(SUBJECTS[i], callback_data=f"sub_{section_prefix}_{i}")]
        if i + 1 < len(SUBJECTS): row.append(InlineKeyboardButton(SUBJECTS[i+1], callback_data=f"sub_{section_prefix}_{i+1}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

def lectures_keyboard(section, subject_index):
    subject_name, norm_subject = SUBJECTS[subject_index], normalize_text(SUBJECTS[subject_index])
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT subject, lecture_num FROM lecture_files WHERE section=?", (section,))
    rows = cursor.fetchall()
    conn.close()
    lecture_nums = sorted(list({lec_num for db_sub, lec_num in rows if normalize_text(db_sub) == norm_subject}))
    if not lecture_nums: return InlineKeyboardMarkup([[InlineKeyboardButton("❌ لا توجد ملفات مرفوعة لهذه المادة حالياً", callback_data="empty")]])
    
    buttons = []
    for i in range(0, len(lecture_nums), 2):
        row = [InlineKeyboardButton(f"محاضرة {lecture_nums[i]}", callback_data=f"lec_{section}_{subject_index}_{lecture_nums[i]}")]
        if i + 1 < len(lecture_nums): row.append(InlineKeyboardButton(f"محاضرة {lecture_nums[i+1]}", callback_data=f"lec_{section}_{subject_index}_{lecture_nums[i+1]}"))
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)

@app_bot.on_message(filters.command("start"))
async def send_welcome(client, message):
    await message.reply_text("أهلاً بك في بوت المكتبة الدراسية لقسم القانون 🎓📚\nاختر القسم المطلوب:", reply_markup=main_keyboard(message.from_user.id))

@app_bot.on_message(filters.text & filters.user(ADMIN_ID) & filters.regex(r"لوحة التحكم ⚙️"))
async def admin_panel(client, message):
    await message.reply_text("🛠️ **لوحة التحكم:**\n`اضف شيت مدخل قانون 1`\n`احذف شيت مدخل قانون 1`", parse_mode="markdown")

@app_bot.on_message(filters.text & filters.user(ADMIN_ID) & filters.regex(r"^اضف"))
async def add_lecture(client, message):
    section, subject, lec_num = parse_arabic_command(message.text)
    if not section or not subject or lec_num is None or not message.reply_to_message:
        await message.reply_text("⚠️ صيغة خاطئة أو لم تقم بالرد على الملف.")
        return
    target = message.reply_to_message
    file_id = target.document.file_id if target.document else (target.audio.file_id if target.audio else (target.voice.file_id if target.voice else (target.photo.file_id if target.photo else None)))
    file_type = "doc" if target.document else ("audio" if (target.audio or target.voice) else ("photo" if target.photo else None))
    if file_id:
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO lecture_files (section, subject, lecture_num, file_id, file_type) VALUES (?, ?, ?, ?, ?)", (section, subject, lec_num, file_id, file_type))
        conn.commit()
        conn.close()
        await message.reply_text(f"✅ تم حفظ المحاضرة {lec_num} لمادة [{subject}] بنجاح!")

@app_bot.on_message(filters.text)
async def handle_menu(client, message):
    user_id = message.from_user.id
    if user_id in user_quiz_sessions:
        await handle_quiz_answer(client, message)
        return
    text = message.text
    if "تسجيلات صوتية" in text: await message.reply_text("🎙️ اختر المادة:", reply_markup=subjects_keyboard("aud"))
    elif "شيتات" in text: await message.reply_text("📚 اختر المادة:", reply_markup=subjects_keyboard("sheet"))
    elif "ملخصي" in text: await message.reply_text("📖 اختر المادة:", reply_markup=subjects_keyboard("summary"))
    elif "امتحانات سابقة" in text: await message.reply_text("📝 اختر المادة:", reply_markup=subjects_keyboard("ex"))
    elif "مجهول" in text: await message.reply_text("https://t.me/majho1bot")

@app_bot.on_callback_query()
async def handle_callbacks(client, callback_query):
    data = callback_query.data.split("_")
    if data[0] == "empty":
        await callback_query.answer("لا توجد ملفات بعد.", show_alert=True)
        return
    if data[0] == "sub":
        await callback_query.edit_message_text(f"📖 مادة **{SUBJECTS[int(data[2])]}**\nاختر رقم المحاضرة:", reply_markup=lectures_keyboard(data[1], int(data[2])))
    elif data[0] == "lec":
        section, sub_idx, lec_num = data[1], int(data[2]), int(data[3])
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type, subject FROM lecture_files WHERE section=? AND lecture_num=?", (section, lec_num))
        rows = cursor.fetchall()
        conn.close()
        for f_id, f_type, db_sub in rows:
            if normalize_text(db_sub) == normalize_text(SUBJECTS[sub_idx]):
                if f_type == "doc": await client.send_document(callback_query.message.chat.id, f_id)
                elif f_type == "audio": await client.send_audio(callback_query.message.chat.id, f_id)
                elif f_type == "photo": await client.send_photo(callback_query.message.chat.id, f_id)
        if section == "sheet":
            quiz_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🧠 اختبر نفسك (AI)", callback_data=f"quiz_{section}_{sub_idx}_{lec_num}")]])
            await callback_query.message.reply_text("✅ تم إرسال الشيت.", reply_markup=quiz_markup)
        else:
            await callback_query.message.reply_text("✅ تم الإرسال.")
    elif data[0] == "quiz":
        section, sub_idx, lec_num = data[1], int(data[2]), int(data[3])
        user_id = callback_query.from_user.id
        await callback_query.message.reply_text("⏳ جاري تحليل الشيت عبر الذكاء الاصطناعي...")
        conn = sqlite3.connect("bot_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, file_type, subject FROM lecture_files WHERE section=? AND lecture_num=?", (section, lec_num))
        rows = cursor.fetchall()
        conn.close()
        matching = [f for f, t, sub in rows if normalize_text(sub) == normalize_text(SUBJECTS[sub_idx])]
        if not matching:
            await callback_query.message.reply_text("❌ لم يتم العثور على الشيت.")
            return
        try:
            local_filename = await client.download_media(matching[0], file_name=f"temp_{user_id}")
            uploaded_file = gemini_client.files.upload(file=local_filename)
            response = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=[uploaded_file, "استخرج 5 أسئلة مقالية من الشيت القانوني برقم السؤال فقط بدون مقدمات."])
            questions = [q.strip() for q in response.text.strip().split("\n") if q.strip()]
            if os.path.exists(local_filename): os.remove(local_filename)
            user_quiz_sessions[user_id] = {"questions": questions, "current_step": 0, "gemini_file": uploaded_file}
            await callback_query.message.reply_text(f"🎯 السؤال الأول:\n{questions[0]}\n\nأرسل إجابتك هنا:")
        except Exception as e:
            await callback_query.message.reply_text(f"⚠️ خطأ: {e}")

async def handle_quiz_answer(client, message):
    user_id = message.from_user.id
    session = user_quiz_sessions[user_id]
    idx = session["current_step"]
    questions = session["questions"]
    await message.reply_text("🔍 جاري التقييم...")
    try:
        res = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=[session["gemini_file"], f"السؤال: {questions[idx]}\nالإجابة: {message.text}\nقيّم الإجابة وأعط الإجابة النموذجية."])
        await message.reply_text(f"📝 النتيجة:\n\n{res.text}")
        session["current_step"] += 1
        if session["current_step"] < len(questions):
            await message.reply_text(f"📌 السؤال التالي:\n{questions[session['current_step']]}")
        else:
            await message.reply_text("🎉 انتهى الاختبار بنجاح!")
            del user_quiz_sessions[user_id]
    except Exception as e:
        await message.reply_text(f"⚠️ خطأ: {e}")

# خادم وهمي بسيط متوافق مع نظام ريندر لكي يظل البوت شغالاً بدون مشاكل
async def handle_web(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    await app_bot.start()
    print("Bot started successfully!")
    await asyncio.gather(*(asyncio.get_event_loop().create_future() for _ in range(1)))

if __name__ == "__main__":
    asyncio.run(main())0
