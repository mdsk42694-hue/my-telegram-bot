import logging
import os
import time
import pytesseract
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from config import (
    BOT_TOKEN,
    FACEBOOK_LINK,
    YOUTUBE_LINK,
    TIKTOK_LINK,
    TELEGRAM_LINK,
    YOUTUBE_KEYWORDS,
    FACEBOOK_KEYWORDS,
    ACCESS_DURATION,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

user_data = {}
SAVED_FILE_ID = None
ADMIN_ID = None

def is_access_valid(user_id):
    if user_id in user_data and "access_until" in user_data[user_id]:
        return time.time() < user_data[user_id]["access_until"]
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    
    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if is_access_valid(user_id):
        remaining = int((user_data[user_id]["access_until"] - time.time()) / 3600)
        await update.message.reply_text(f"✅ আপনি ইতিমধ্যে এক্সেস পেয়েছেন! অবশিষ্ট সময়: {remaining} ঘণ্টা।")
        if SAVED_FILE_ID:
            await update.message.reply_document(document=SAVED_FILE_ID, caption="🎉 এই যে আপনার ফাইল!")
        return

    if user_id not in user_data:
        user_data[user_id] = {"yt_verified": False, "fb_verified": False, "access_until": 0}

    keyboard = [
        [InlineKeyboardButton("📘 FOLLOW ON FB ↗️", url=FACEBOOK_LINK)],
        [InlineKeyboardButton("✈️ JOIN TELEGRAM ↗️", url=TELEGRAM_LINK)],
        [InlineKeyboardButton("📺 SUBSCRIBE YT ↗️", url=YOUTUBE_LINK)],
        [InlineKeyboardButton("🎵 TIKTOK PAGE ↗️", url=TIKTOK_LINK)],
        [
            InlineKeyboardButton("📸 VERIFY FB", callback_data="verify_fb"),
            InlineKeyboardButton("📸 VERIFY YT", callback_data="verify_yt"),
        ],
        [InlineKeyboardButton("✅ VERIFY NOW", callback_data="verify_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    caption_text = (
        "🔒 **সিকিউরিটি লক সিস্টেম**\n\n"
        "বট ব্যবহার করতে নিচের প্ল্যাটফর্মগুলোতে যুক্ত হয়ে ভেরিফাই করুন।\n"
        "ইউটিউব এবং ফেসবুকের ক্ষেত্রে স্ক্রিনশট পাঠিয়ে ভেরিফাই করতে হবে।\n"
        "সব কাজ শেষ হলে **VERIFY NOW** বাটনে ক্লিক করুন।"
    )

    await update.message.reply_text(text=caption_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {"yt_verified": False, "fb_verified": False, "access_until": 0}

    if query.data == "verify_fb":
        user_data[user_id]["expecting"] = "fb"
        await query.message.reply_text("📸 দয়া করে ফেসবুক ফলো দেওয়ার একটি পরিষ্কার স্ক্রিনশট পাঠান:")

    elif query.data == "verify_yt":
        user_data[user_id]["expecting"] = "yt"
        await query.message.reply_text("📸 দয়া করে ইউটিউব সাবস্ক্রিপশনের একটি পরিষ্কার স্ক্রিনশট পাঠান:")

    elif query.data == "verify_now":
        yt_status = user_data[user_id].get("yt_verified", False)
        fb_status = user_data[user_id].get("fb_verified", False)

        if yt_status and fb_status:
            user_data[user_id]["access_until"] = time.time() + ACCESS_DURATION
            await query.message.reply_text("🎉 অভিনন্দন! আপনার সব ভেরিফিকেশন সফল হয়েছে। বট আনলক করা হলো (২৪ ঘন্টার জন্য)।")
            
            if SAVED_FILE_ID:
                await context.bot.send_document(chat_id=user_id, document=SAVED_FILE_ID, caption="📁 এই নিন আপনার কাঙ্ক্ষিত ফাইল:")
            else:
                await query.message.reply_text("⚠️ ফাইল প্রস্তুত করা হচ্ছে, অনুগ্রহ করে অ্যাডমিনের আপলোড পর্যন্ত অপেক্ষা করুন।")
        else:
            missing = []
            if not fb_status:
                missing.append("ফেসবুক স্ক্রিনশট")
            if not yt_status:
                missing.append("ইউটিউব স্ক্রিনশট")
            
            await query.message.reply_text(f"❌ আপনার ভেরিফিকেশন অসম্পূর্ণ রয়েছে!\nবাকি আছে: {', '.join(missing)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_data.get(user_id, {}).get("expecting", None)

    if not state:
        await update.message.reply_text("⚠️ অনুগ্রহ করে প্রথমে ভেরিফিকেশন বাটন চেপে স্ক্রিনশট পাঠান।")
        return

    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{user_id}.jpg"
    await photo_file.download_to_drive(file_path)

    try:
        text = pytesseract.image_to_string(Image.open(file_path))
        
        if state == "yt":
            if any(keyword.lower() in text.lower() for keyword in YOUTUBE_KEYWORDS):
                user_data[user_id]["yt_verified"] = True
                user_data[user_id]["expecting"] = None
                await update.message.reply_text("✅ ইউটিউব ভেরিফিকেশন সফল হয়েছে!")
            else:
                await update.message.reply_text("❌ ইউটিউব সাবস্ক্রিপশন পাওয়া যায়নি। পরিষ্কার স্ক্রিনশট আবার পাঠান।")

        elif state == "fb":
            if any(keyword.lower() in text.lower() for keyword in FACEBOOK_KEYWORDS):
                user_data[user_id]["fb_verified"] = True
                user_data[user_id]["expecting"] = None
                await update.message.reply_text("✅ ফেসবুক ভেরিফিকেশন সফল হয়েছে!")
            else:
                await update.message.reply_text("❌ ফেসবুক ফলো পাওয়া যায়নি। পরিষ্কার স্ক্রিনশট আবার পাঠান।")

    except Exception as e:
        await update.message.reply_text("⚠️ ছবি স্ক্যান করতে সমস্যা হয়েছে। আবার চেষ্টা করুন।")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVED_FILE_ID, ADMIN_ID
    user_id = update.effective_user.id

    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if user_id == ADMIN_ID:
        SAVED_FILE_ID = update.message.document.file_id
        await update.message.reply_text("✅ ফাইলটি সফলভাবে বটের ড্রাইভে সেভ করা হয়েছে! এখন থেকে ভেরিফাই হওয়া ইউজাররা এই ফাইলটি পেয়ে যাবে।")
    else:
        await update.message.reply_text("⚠️ ফাইল আপলোড করার এক্সেস কেবল অ্যাডমিনের রয়েছে।")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
