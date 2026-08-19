if call.data == "go_main":
        bot.edit_message_text("تمت العودة للقائمة الرئيسية.", chat_id, call.message.message_id)
    
    # 🎙️ التسجيلات الصوتية
    elif call.data.startswith("aud_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"🎧 مادة {subject} - اختر المحاضرة الصوتية:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=lectures_keyboard("aud", subject))
    elif call.data.startswith("aud_lec_"):
        _, _, subject, lec = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب {lec} لمادة {subject}...")

    # 📝 التسجيلات المكتوبة
    elif call.data.startswith("wrt_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"📝 مادة {subject} - اختر المحاضرة المكتوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=lectures_keyboard("wrt", subject))
    elif call.data.startswith("wrt_lec_"):
        _, _, subject, lec = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب صور {lec} لمادة {subject}...")

    # 📚 الامتحانات السابقة
    elif call.data.startswith("ex_sub_"):
        subject = call.data.split("_")[2]
        bot.edit_message_text(f"📚 مادة {subject} - اختر السنة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=years_keyboard(subject))
    elif call.data.startswith("ex_yr_"):
        _, _, subject, year = call.data.split("_")
        bot.answer_callback_query(call.id, f"جارٍ جلب امتحان {subject} لسنة {year}...")

    # أزرار الرجوع
    elif call.data == "back_to_aud":
        bot.edit_message_text("🎙️ قسم التسجيلات الصوتية\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("aud"))
    elif call.data == "back_to_wrt":
        bot.edit_message_text("📝 قسم التسجيلات المكتوبة\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("wrt"))
    elif call.data == "back_to_ex":
        bot.edit_message_text("📚 قسم الامتحانات السابقة\nاختر المادة المطلوبة:", chat_id, call.message.message_id, parse_mode="Markdown", reply_markup=subjects_keyboard("ex"))

# ---------------------------------------------------------
# 5. تشغيل البوت
# ---------------------------------------------------------
if name == "main":
    print("🤖 البوت يعمل بنجاح...")
    bot.infinity_polling()
