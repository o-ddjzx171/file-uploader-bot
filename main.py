import os
import requests
import time
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ["BOT_TOKEN"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 120MB
CHUNK_SIZE_MB = 25

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 أرسل رابط لملف عشان ارسله لك .")

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

async def download_file_with_progress(url, file_path, progress_msg: Message, context: ContextTypes.DEFAULT_TYPE):
    r = requests.get(url, stream=True)
    total = int(r.headers.get('content-length', 0))
    downloaded = 0
    start_time = time.time()
    chunk_size = 1024 * 1024

    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start_time
                speed = downloaded / 1024 / elapsed
                percent = (downloaded / total) * 100 if total else 0
                eta = (total - downloaded) / (downloaded / elapsed) if downloaded > 0 else 0

                text = (
                    f"📥 جاري التحميل...\n"
                    f"🔄 {percent:.2f}% | ⬇️ {downloaded / (1024*1024):.2f}MB / {total / (1024*1024):.2f}MB\n"
                    f"⚡️ سرعة: {speed:.2f} KB/s\n"
                    f"⏱️ الوقت المتبقي: {eta:.1f} ثانية"
                )

                try:
                    await progress_msg.edit_text(text)
                except:
                    pass

    return total

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("📎 أرسل رابط يبدأ بـ http.")
        return

    file_name = url.split("/")[-1].split("?")[0]
    progress_msg = await update.message.reply_text("⏳ جاري بدء التحميل...")

    try:
        # تحميل الملف مع عرض التقدم
        total_size = await download_file_with_progress(url, file_name, progress_msg, context)

        if total_size <= MAX_FILE_SIZE:
            await progress_msg.edit_text("✅ تم التحميل. جاري الإرسال...")
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=open(file_name, "rb"),
                filename=file_name
            )
            os.remove(file_name)
        else:
            await progress_msg.edit_text("📦 الملف كبير. جاري تقسيمه...")
            parts = split_file(file_name, CHUNK_SIZE_MB)

            for i, part in enumerate(parts, start=1):
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=open(part, 'rb'),
                    filename=os.path.basename(part),
                    caption=f"📤 الجزء {i}/{len(parts)}"
                )
                os.remove(part)

            os.remove(file_name)
            await progress_msg.edit_text("🎉 تم إرسال كل الأجزاء!")

    except Exception as e:
        await progress_msg.edit_text(f"❌ خطأ أثناء التحميل أو الإرسال: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling()
