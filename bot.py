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
all_users = set()
SAVED_FILE_ID = None
ADMIN_ID = None

def extract_channel_username(link):
    clean = link.strip().rstrip("/")
    if "t.me/" in clean:
        return "@" + clean.split("t.me/")[-1].replace("+", "")
    return clean

CHANNEL_USERNAME = extract_channel_username(TELEGRAM_LINK)

def is_access_valid(user_id):
    if user_id in user_data and "access_until" in user_data[user_id]:
        return time.time() < user_data[user_id]["access_until"]
    return False

async def check_telegram_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception as e:
        logging.error(f"Telegram membership check error: {e}")
        return False
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if is_access_valid(user_id):
        remaining = int((user_data[user_id]["access_until"] - time.time()) / 3600)
        await update.message.reply_text(f"✅ আপনি ইতিমধ্যে এক্সেস পেয়েছেন! অবশিষ্ট সময়: {remaining} ঘণ্টা।")
        if SAVED_FILE_ID:
            await update.message.reply_document(document=SAVED_FILE_ID, caption="🎉 এই যে আপনার ফাইল!")
        return

    if user_id not in user_data:
        user_data[user_id] = {
            "yt_verified": False,
            "fb_verified": False,
            "access_until": 0,
            "expecting": None,
            "request_time": 0
        }

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
        "বট ব্যবহার করতে নিচের কাজগুলো সম্পন্ন করুন:\n"
        "১. শুধুমাত্র **আমাদের** ফেসবুক পেজ ও ইউটিউব চ্যানেল ফলো/সাবস্ক্রাইব করে স্ক্রিনশট পাঠান (অন্য চ্যানেলের স্ক্রিনশট গ্রহণ করা হবে না)।\n"
        "২. টেলিগ্রাম চ্যানেলে জয়েন থাকতে হবে।\n\n"
        "⏱️ **নোট:** ভেরিফিকেশন বাটন চাপার ১০ মিনিটের মধ্যে স্ক্রিনশট পাঠাতে হবে।\n"
        "সব কাজ শেষ হলে **VERIFY NOW** বাটনে ক্লিক করুন।"
    )

    await update.message.reply_text(text=caption_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    all_users.add(user_id)

    if user_id not in user_data:
        user_data[user_id] = {
            "yt_verified": False,
            "fb_verified": False,
            "access_until": 0,
            "expecting": None,
            "request_time": 0
        }

    if query.data == "verify_fb":
        user_data[user_id]["expecting"] = "fb"
        user_data[user_id]["request_time"] = time.time()
        await query.message.reply_text("⏱️ আপনার সময় শুরু হয়েছে (১০ মিনিট)!\n📸 দয়া করে **আমাদের ফেসবুক পেজ** ফলো করার পর পরিষ্কার স্ক্রিনশট পাঠান:")

    elif query.data == "verify_yt":
        user_data[user_id]["expecting"] = "yt"
        user_data[user_id]["request_time"] = time.time()
        await query.message.reply_text("⏱️ আপনার সময় শুরু হয়েছে (১০ মিনিট)!\n📸 দয়া করে **আমাদের ইউটিউব চ্যানেল** সাবস্ক্রাইব (Subscribed) করার পর পরিষ্কার স্ক্রিনশট পাঠান:")

    elif query.data == "verify_now":
        yt_status = user_data[user_id].get("yt_verified", False)
        fb_status = user_data[user_id].get("fb_verified", False)
        
        is_tg_member = await check_telegram_membership(context, user_id)
        
        if not is_tg_member:
            await query.message.reply_text("❌ আপনি আমাদের টেলিগ্রাম চ্যানেলে যুক্ত হননি! অনুগ্রহ করে চ্যানেলটিতে জয়েন হয়ে আবার চেষ্টা করুন।")
            return

        if yt_status and fb_status:
            user_data[user_id]["access_until"] = time.time() + ACCESS_DURATION
            await query.message.reply_text("🎉 অভিনন্দন! আপনার সব ভেরিফিকেশন সফল হয়েছে। বট আনলক করা হলো (২৪ ঘণ্টার জন্য)।")
            
            if SAVED_FILE_ID:
                await context.bot.send_document(chat_id=user_id, document=SAVED_FILE_ID, caption="📁 এই নিন আপনার কাঙ্ক্ষিত ফাইল:")
            else:
                await query.message.reply_text("⚠️ ফাইল প্রস্তুত করা হচ্ছে, অনুগ্রহ করে অ্যাডমিনের আপলোড পর্যন্ত অপেক্ষা করুন।")
        else:
            missing = []
            if not fb_status:
                missing.append("ফেসবুক ফলো স্ক্রিনশট (সঠিক পেজের নাম সহ)")
            if not yt_status:
                missing.append("ইউটিউব সাবস্ক্রাইব স্ক্রিনশট (সঠিক চ্যানেলের নাম সহ)")
            
            await query.message.reply_text(f"❌ ভেরিফিকেশন অসম্পূর্ণ বা ভুল রয়েছে!\nবাকি আছে: {', '.join(missing)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    user_info = user_data.get(user_id, {})
    state = user_info.get("expecting", None)
    req_time = user_info.get("request_time", 0)

    if not state:
        await update.message.reply_text("⚠️ অনুগ্রহ করে প্রথমে ভেরিফিকেশন বাটন চাপুন, তারপর স্ক্রিনশট পাঠান।")
        return

    if time.time() - req_time > 600:
        user_data[user_id]["expecting"] = None
        await update.message.reply_text("⏱️ সময় পার হয়ে গেছে (১০ মিনিট সীমা অতিক্রম করেছে)! দয়া করে আবার ভেরিফিকেশন বাটনে চাপ দিয়ে নতুন স্ক্রিনশট পাঠান।")
        return

    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{user_id}.jpg"
    await photo_file.download_to_drive(file_path)

    try:
        text = pytesseract.image_to_string(Image.open(file_path)).lower()
        
        if state == "yt":
            name_match = any(keyword.lower() in text for keyword in YOUTUBE_KEYWORDS)
            sub_proof = ("subscribed" in text) or ("subscribing" in text) or ("bell" in text) or ("সদস্যতা নেওয়া হয়েছে" in text)
            
            if name_match and sub_proof:
                user_data[user_id]["yt_verified"] = True
                user_data[user_id]["expecting"] = None
                await update.message.reply_text("✅ ইউটিউব চ্যানেল এবং সাবস্ক্রিপশন সফলভাবে ভেরিফাই হয়েছে!")
            else:
                await update.message.reply_text("❌ ভেরিফিকেশন ব্যর্থ! স্ক্রিনশটে হয় আপনার **সঠিক ইউটিউব চ্যানেলের নাম** পাওয়া যায়নি অথবা চ্যানেলটি **Subscribed** করা নেই। দয়া করে সঠিক স্ক্রিনশট দিন।")

        elif state == "fb":
            name_match = any(keyword.lower() in text for keyword in FACEBOOK_KEYWORDS)
            fb_proof = ("following" in text) or ("followed" in text) or ("ফলো করছেন" in text) or ("liked" in text)
            
            if name_match and fb_proof:
                user_data[user_id]["fb_verified"] = True
                user_data[user_id]["expecting"] = None
                await update.message.reply_text("✅ ফেসবুক পেজ এবং ফলো সফলভাবে ভেরিফাই হয়েছে!")
            else:
                await update.message.reply_text("❌ ভেরিফিকেশন ব্যর্থ! স্ক্রিনশটে হয় আপনার **সঠিক ফেসবুক পেজের নাম** পাওয়া যায়নি অথবা পেজটি **Follow** করা নেই। দয়া করে সঠিক স্ক্রিনশট দিন।")

    except Exception as e:
        await update.message.reply_text("⚠️ ছবি স্ক্যান করতে সমস্যা হয়েছে। দয়া করে স্পষ্ট স্ক্রিনশট পাঠান।")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVED_FILE_ID, ADMIN_ID
    user_id = update.effective_user.id
    all_users.add(user_id)

    # যেকোনো ফাইল মেসেজ পাঠালে তা সরাসরি সেভ হয়ে যাবে
    SAVED_FILE_ID = update.message.document.file_id
    ADMIN_ID = user_id
    await update.message.reply_text("✅ ফাইলটি সফলভাবে বটের ড্রাইভে সেভ করা হয়েছে! এখন থেকে ভেরিফাই হওয়া ইউজাররা এই ফাইলটি পেয়ে যাবে।")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if user_id == ADMIN_ID:
        voice_id = update.message.voice.file_id
        sent_count = 0
        for uid in all_users:
            if uid != ADMIN_ID:
                try:
                    await context.bot.send_voice(chat_id=uid, voice=voice_id)
                    sent_count += 1
                except Exception:
                    pass
        await update.message.reply_text(f"📢 ভয়েস মেসেজটি {sent_count} জনের কাছে পাঠানো হয়েছে।")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if user_id == ADMIN_ID:
        msg_text = update.message.text
        sent_count = 0
        for uid in all_users:
            if uid != ADMIN_ID:
                try:
                    await context.bot.send_message(chat_id=uid, text=msg_text)
                    sent_count += 1
                except Exception:
                    pass
        await update.message.reply_text(f"📢 মেসেজটি {sent_count} জনের কাছে পাঠানো হয়েছে।")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
