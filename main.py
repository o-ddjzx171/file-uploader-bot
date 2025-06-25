import os
import requests
import time
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# استخدم متغير بيئة لحماية التوكن
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHUNK_SIZE_MB = 25  # حجم كل جزء

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 أرسل لي رابط ملف وسأقسمه وأرسله لك على شكل أجزاء.")

def split_file(file_path, chunk_size_mb):
    parts = []
    chunk_size = chunk_size_mb * 1024 * 1024
    with open(file_path, 'rb') as f:
        i = 1
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_file = f"{file_path}.part{i:02d}"
            with open(part_file, 'wb') as pf:
                pf.write(chunk)
            parts.append(part_file)
            i += 1
    return parts

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("📎 أرسل رابط يبدأ بـ http.")
        return

    file_name = url.split("/")[-1].split("?")[0]
    progress_msg = await update.message.reply_text("⏳ جاري تحميل الملف...")

    try:
        # تحميل الملف
        r = requests.get(url, stream=True)
        total = int(r.headers.get('content-length', 0))
        with open(file_name, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        await progress_msg.edit_text("✅ تم تحميل الملف. جاري التقسيم...")

        # تقسيم الملف
        parts = split_file(file_name, CHUNK_SIZE_MB)

        await progress_msg.edit_text(f"📤 جاري إرسال {len(parts)} جزء...")

        for i, part in enumerate(parts, start=1):
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(part, 'rb'),
                filename=os.path.basename(part),
                caption=f"📦 الجزء {i}/{len(parts)}"
            )
            os.remove(part)

        os.remove(file_name)
        await progress_msg.edit_text("🎉 تم إرسال كل الأجزاء بنجاح!")

    except Exception as e:
        await progress_msg.edit_text(f"❌ حصل خطأ: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
