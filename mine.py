import telebot
from telebot import types

# ---------------------------------------------------------
# 1. التكوين الأساسي
# ---------------------------------------------------------
BOT_TOKEN = "8940117200:AAEruJBr6mRLuXxdZPEFD8SHuj_FpNc6Lt4"
ADMIN_ID = 8744592769
ANONYMOUS_LINK = "https://sayat.me/your_account"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------------------------------------------------
# 2. القوائم الرئيسية ولوحات الأزرار
# ---------------------------------------------------------
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🎙️ تسجِيلات صَوتِيّة")
    btn2 = types.KeyboardButton("📝 تسجِيلات مَكتُوبَة")
    btn3 = types.KeyboardButton("📌 مُلَخَّصِي")
    btn4 = types.KeyboardButton("📚 امتِحانات سابِقَة")
    btn5 = types.KeyboardButton("💬 تَواصَل مَعِي (مَجْهُول)")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def subjects_keyboard(prefix):
    markup = types.InlineKeyboardMarkup(row_width=2)
    subjects = ["رياضيات", "فيزياء", "كيمياء", "إنجليزي"]
    buttons = [types.InlineKeyboardButton(sub, callback_data=f"{prefix}_sub_{sub}") for sub in subjects]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="go_main"))
    return markup

def lectures_keyboard(prefix, subject):
    markup = types.InlineKeyboardMarkup(row_width=2)
    lectures = ["محاضرة 1", "محاضرة 2", "محاضرة 3", "محاضرة 4"]
    buttons = [types.InlineKeyboardButton(lec, callback_data=f"{prefix}_lec_{subject}_{lec}") for lec in lectures]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 العودة للمواد", callback_data=f"back_to_{prefix}"))
    return markup

def summary_keyboard(subject):
    markup = types.InlineKeyboardMarkup(row_width=2)
    summaries = ["ملخص 1", "ملخص 2", "ملخص 3", "ملخص الشامل"]
    buttons = [types.InlineKeyboardButton(sm, callback_data=f"sum_item_{subject}_{sm}") for sm in summaries]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 العودة للمواد", callback_data="back_to_sum"))
    return markup

def years_keyboard(subject):
    markup = types.InlineKeyboardMarkup(row_width=2)
    years = ["2023", "2024", "2025", "2026"]
    buttons = [types.InlineKeyboardButton(yr, callback_data=f"ex_yr_{subject}_{yr}") for yr in years]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 العودة للمواد", callback_data="back_to_ex"))
    return markup

# ---------------------------------------------------------
# 3. الأوامر والتفاعل الأساسي
# ---------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "✨ **أهْلاً وَسَهْلاً بِكَ فِي بُوتِ المَكْتَبَةِ الدِّرَاسِيَّةِ** 🎓\n\n"
        "«طَرِيقُ النَّجَاحِ يَبْدَأُ بِخَطْوَة، وَنَحْنُ هُنَا لِنَكُونَ مَعَكَ فِي كُلِّ خَطْوَةٍ» 📖⚡️\n\n"
        "يرجى اختيار القسم الذي تودّ الاطلاع عليه أدناه 👇"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_menu_click(message):
    if message.text == "🎙️ تسجِيلات صَوتِيّة":
        bot.send_message(message.chat.id, "🎙️ **قسم التسجيلات الصوتية**\nاختر المادة المطلوبة:", parse_mode="Markdown", reply_markup=subjects_keyboard("aud"))
    elif message.text == "📝 تسجِيلات مَكتُوبَة":
        bot.send_message(message.chat.id, "📝 **قسم التسجيلات المكتوبة**\nاختر المادة المطلوبة:", parse_mode="Markdown", reply_markup=subjects_keyboard("wrt"))
    elif message.text == "📌 مُلَخَّصِي":
        bot.send_message(message.chat.id, "📌 **قسم ملخصي الخاص**\nاختر المادة المطلوبة:", parse_mode="Markdown", reply_markup=subjects_keyboard("sum"))
    elif message.text == "📚 امتِحانات سابِقَة":
        bot.send_message(message.chat.id, "📚 **قسم الامتحانات السابقة**\nاختر المادة المطلوبة:", parse_mode="Markdown", reply_markup=subjects_keyboard("ex"))
    elif message.text == "💬 تَواصَل مَعِي (مَجْهُول)":
        msg = f"💬 **تواصل مجهول:**\n\nإذا كان لديك أي سؤال أو استفسار، يمكنك إرساله بحرية عبر الرابط أدناه:\n\n🔗 [اضغط هنا لإرسال رسالتك]({ANONYMOUS_LINK})"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown", disable_web_page_preview=True)

# ---------------------------------------------------------
# 4. معالجة الضغط على الأزرار الفرعية
# ---------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id

    if call.data == "go_main":
        bot.edit_message_text("تمت العودة للقائمة الرئيسية.", chat_id, call.message.message_id)
    
    # 🎙️ التسجيلات الصوتية
    elif call.data.startswith("aud_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"🎧 **مادة {subject}** - اختر المحاضرة الصوتية:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=lectures_keyboard("aud", subject))
    elif call.data.startswith("aud_lec_"):
        _, _, subject, lec = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب {lec} لمادة {subject}...")

    # 📝 التسجيلات المكتوبة
    elif call.data.startswith("wrt_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"📝 **مادة {subject}** - اختر المحاضرة المكتوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=lectures_keyboard("wrt", subject))
    elif call.data.startswith("wrt_lec_"):
        _, _, subject, lec = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب صور {lec} لمادة {subject}...")

    # 📌 قسم ملخصي
    elif call.data.startswith("sum_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"📌 **ملخصات مادة {subject}** - اختر الملخص المطلوب:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=summary_keyboard(subject))
    elif call.data.startswith("sum_item_"):
        _, _, subject, item = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب {item} لمادة {subject}...")

    # 📚 الامتحانات السابقة
    elif call.data.startswith("ex_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"📚 **مادة {subject}** - اختر السنة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=years_keyboard(subject))
    elif call.data.startswith("ex_yr_"):
        _, _, subject, year = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب امتحان {subject} لسنة {year}...")

    # أزرار الرجوع
    elif call.data == "back_to_aud":
        bot.edit_message_text("🎙️ **قسم التسجيلات الصوتية**\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("aud"))
    elif call.data == "back_to_wrt":
        bot.edit_message_text("📝 **قسم التسجيلات المكتوبة**\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("wrt"))
    elif call.data == "back_to_sum":
        bot.edit_message_text("📌 **قسم ملخصي الخاص**\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("sum"))
    elif call.data == "back_to_ex":
        bot.edit_message_text("📚 **قسم الامتحانات السابقة**\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("ex"))

# ---------------------------------------------------------
# 5. تشغيل البوت
# ---------------------------------------------------------
if __name__ == "__main__":
    print("🤖 البوت يعمل بنجاح...")
    bot.infinity_polling()
