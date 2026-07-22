import logging
import os
import time
import pytesseract
import cv2
import numpy as np
from PIL import Image
from gtts import gTTS
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
    ACCESS_DURATION,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

user_data = {}
all_users = set()
SAVED_FILE_ID = None
ADMIN_ID = None  

async def send_voice_text(context, chat_id, text):
    try:
        tts = gTTS(text=text, lang='bn')
        filename = f"voice_{chat_id}_{int(time.time())}.mp3"
        tts.save(filename)
        with open(filename, 'rb') as voice_file:
            await context.bot.send_voice(chat_id=chat_id, voice=voice_file, caption=text)
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        logging.error(f"Voice generation error: {e}")
        await context.bot.send_message(chat_id=chat_id, text=text)

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
    global ADMIN_ID, SAVED_FILE_ID
    user_id = update.effective_user.id
    all_users.add(user_id)
    
    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if is_access_valid(user_id):
        remaining = int((user_data[user_id]["access_until"] - time.time()) / 3600)
        msg = f"আপনি ইতিমধ্যে এক্সেস পেয়েছেন! অবশিষ্ট সময়: {remaining} ঘণ্টা।"
        await send_voice_text(context, user_id, msg)
        
        if SAVED_FILE_ID:
            try:
                await context.bot.send_document(
                    chat_id=user_id, 
                    document=SAVED_FILE_ID, 
                    caption="🎉 এই যে আপনার কাঙ্ক্ষিত ফাইল!"
                )
            except Exception as e:
                logging.error(f"Error sending saved file: {e}")
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
        "🔒 **স্মার্ট ভেরিফিকেশন সিস্টেম**\n\n"
        "বট ব্যবহার করতে নিচের কাজগুলো সম্পন্ন করুন:\n"
        "১. ফেসবুক পেজ ও ইউটিউব চ্যানেল সাবস্ক্রাইব/ফলো করে স্ক্রিনশট দিন।\n"
        "২. ব্র্যান্ড নাম ও প্রুফ কঠোরভাবে যাচাই করা হবে।\n"
        "৩. ১০ মিনিটের মধ্যে প্রুফ সাবমিট করতে হবে।\n"
        "৪. কাজ শেষ হলে **VERIFY NOW** বাটনে ক্লিক করুন।"
    )

    await update.message.reply_text(text=caption_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVED_FILE_ID
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
        msg = "আমাদের ফেসবুক পেজটি ফলো করে স্ক্রিনশট পাঠান। আপনার সময় ১০ মিনিট।"
        await send_voice_text(context, user_id, msg)

    elif query.data == "verify_yt":
        user_data[user_id]["expecting"] = "yt"
        user_data[user_id]["request_time"] = time.time()
        msg = "আমাদের ইউটিউব চ্যানেলটি সাবস্ক্রাইব করে স্ক্রিনশট পাঠান। আপনার সময় ১০ মিনিট।"
        await send_voice_text(context, user_id, msg)

    elif query.data == "verify_now":
        yt_status = user_data[user_id].get("yt_verified", False)
        fb_status = user_data[user_id].get("fb_verified", False)
        
        is_tg_member = await check_telegram_membership(context, user_id)
        
        if not is_tg_member:
            msg = "আপনি এখনো আমাদের টেলিগ্রাম চ্যানেলে জয়েন করেননি। অনুগ্রহ করে জয়েন হয়ে আবার চেষ্টা করুন।"
            await send_voice_text(context, user_id, msg)
            return

        if yt_status and fb_status:
            user_data[user_id]["access_until"] = time.time() + ACCESS_DURATION
            msg = "অভিনন্দন! আপনার সব ভেরিফিকেশন সফল হয়েছে। বট ২৪ ঘণ্টার জন্য আনলক করা হলো।"
            await send_voice_text(context, user_id, msg)
            
            if SAVED_FILE_ID:
                try:
                    await context.bot.send_document(chat_id=user_id, document=SAVED_FILE_ID, caption="📁 এই নিন আপনার কাঙ্ক্ষিত ফাইল:")
                except Exception as e:
                    logging.error(f"Error sending file on verify: {e}")
        else:
            missing_text = ""
            if not fb_status and not yt_status:
                missing_text = "আপনার ফেসবুক এবং ইউটিউব দুটি ভেরিফিকেশনই বাকি আছে।"
            elif not fb_status:
                missing_text = "আপনার ফেসবুক ফলো ভেরিফিকেশন বাকি আছে।"
            elif not yt_status:
                missing_text = "আপনার ইউটিউব সাবস্ক্রাইব ভেরিফিকেশন বাকি আছে।"
            
            await send_voice_text(context, user_id, f"ভেরিফিকেশন ব্যর্থ হয়েছে! {missing_text}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    all_users.add(user_id)
    user_info = user_data.get(user_id, {})
    state = user_info.get("expecting", None)
    req_time = user_info.get("request_time", 0)

    if not state:
        msg = "অনুগ্রহ করে প্রথমে ভেরিফিকেশন বাটন চাপুন, তারপর স্ক্রিনশট পাঠান।"
        await send_voice_text(context, user_id, msg)
        return

    if time.time() - req_time > 600:
        user_data[user_id]["expecting"] = None
        msg = "১০ মিনিট সময় পার হয়ে গেছে। দয়া করে আবার ভেরিফিকেশন বাটনে ক্লিক করুন।"
        await send_voice_text(context, user_id, msg)
        return

    photo_file = await update.message.photo[-1].get_file()
    file_path = f"temp_{user_id}.jpg"
    await photo_file.download_to_drive(file_path)

    try:
        text = pytesseract.image_to_string(Image.open(file_path)).lower()
        
        if state == "yt":
            yt_keywords = ["khlomni7", "omni7", "aman ullah", "khl omni7"]
            has_yt_identity = any(k in text for k in yt_keywords)
            sub_proof = ("subscribed" in text) or ("subscribing" in text) or ("সদস্যতা নেওয়া হয়েছে" in text)
            
            if has_yt_identity and sub_proof:
                user_data[user_id]["yt_verified"] = True
                user_data[user_id]["expecting"] = None
                msg = "ইউটিউব ভেরিফিকেশন সফল হয়েছে!"
                await send_voice_text(context, user_id, msg)
            else:
                msg = "ভেরিফিকেশন ব্যর্থ! স্ক্রিনশটে সঠিক ইউটিউব চ্যানেল এবং সাবস্ক্রাইব প্রুফ পাওয়া যায়নি।"
                await send_voice_text(context, user_id, msg)

        elif state == "fb":
            fb_keywords = ["khl omni7", "aman ullah", "khalilnagar", "satkhira"]
            has_fb_identity = any(k in text for k in fb_keywords)
            fb_proof = ("following" in text) or ("followed" in text) or ("ফলো করছেন" in text)
            
            if has_fb_identity and fb_proof:
                user_data[user_id]["fb_verified"] = True
                user_data[user_id]["expecting"] = None
                msg = "ফেসবুক পেজ ভেরিফিকেশন সফল হয়েছে!"
                await send_voice_text(context, user_id, msg)
            else:
                msg = "ভেরিফিকেশন ব্যর্থ! স্ক্রিনশটে সঠিক ফেসবুক পেজ এবং ফলো প্রুফ পাওয়া যায়নি।"
                await send_voice_text(context, user_id, msg)

    except Exception as e:
        msg = "ছবিটি পরিষ্কার নয়। দয়া করে আবার স্পষ্ট স্ক্রিনশট পাঠান।"
        await send_voice_text(context, user_id, msg)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SAVED_FILE_ID, ADMIN_ID
    user_id = update.effective_user.id
    all_users.add(user_id)

    if ADMIN_ID is None:
        ADMIN_ID = user_id

    if user_id == ADMIN_ID:
        SAVED_FILE_ID = update.message.document.file_id
        await update.message.reply_text("✅ ফাইলটি সফলভাবে ড্রাইভে সেভ করা হয়েছে!")
    else:
        await update.message.reply_text("⚠️ ফাইল আপলোড করার এক্সেস কেবল অ্যাডমিনের রয়েছে।")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user_id = update.effective_user.id
    all_users.add(user_id)
    
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
    all_users.add(user_id)

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
        await update.message.reply_text(f"📢 টেক্সট মেসেজটি {sent_count} জনের কাছে পাঠানো হয়েছে।")

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
