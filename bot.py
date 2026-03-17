import os
import json
import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")

GROUP_ID_STR = os.getenv("GROUP_ID")
ORDER_GROUP_ID_STR = os.getenv("ORDER_GROUP_ID")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")
if not GROUP_ID_STR:
    raise ValueError("GROUP_ID topilmadi")
if not ORDER_GROUP_ID_STR:
    raise ValueError("ORDER_GROUP_ID topilmadi")

GROUP_ID = int(GROUP_ID_STR)
ORDER_GROUP_ID = int(ORDER_GROUP_ID_STR)

DATA_FILE = Path(os.getenv("DATA_FILE_PATH", "/app/storage/data.json"))

topics = {}
products = {}

(
    ADMIN_PASS,
    SELECT_TOPIC,
    PHOTO,
    DESC,
    SIZE_TYPE,
    PRODUCT_ID,
    ORDER_QTY,
    ORDER_SIZE,
    ORDER_PHONE
) = range(9)

logging.basicConfig(level=logging.INFO)


def load_data():
    global topics, products

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        topics = {}
        products = {}
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        topics = data.get("topics", {})
        products = data.get("products", {})
    except Exception as e:
        logging.error(f"Data load error: {e}")
        topics = {}
        products = {}


def save_data():
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "topics": topics,
            "products": products
        }

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Data save error: {e}")


async def is_admin(user_id, context):
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args:
        arg = context.args[0]
        if arg.startswith("buy_"):
            pid = arg.split("_", 1)[1]

            if pid not in products:
                await update.message.reply_text("❌ Mahsulot topilmadi")
                return ConversationHandler.END

            context.user_data["product"] = pid
            await update.message.reply_text("📦 Mahsulot sonini yozing")
            return ORDER_QTY

    if await is_admin(user_id, context):
        keyboard = [["📦 Tovar joylash"]]
        await update.message.reply_text(
            "📦 Admin panel",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\nMahsulotni tanlab 'Buyurtma berish' tugmasini bosing."
        )

    return ConversationHandler.END


async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    if msg.message_thread_id is None:
        await msg.reply_text("❗ Bu buyruqni topic ichida yuboring")
        return

    if not context.args:
        await msg.reply_text("❗ Misol: /settopic Krasofka")
        return

    topic_name = " ".join(context.args).strip()
    thread_id = msg.message_thread_id

    if topic_name in topics:
        await msg.reply_text("⚠️ Bu topic nomi allaqachon qo'shilgan")
        return

    if thread_id in topics.values():
        await msg.reply_text("⚠️ Bu topic allaqachon ro'yxatga olingan")
        return

    topics[topic_name] = thread_id
    save_data()

    await msg.reply_text(f"✅ {topic_name} topic ro'yxatga qo'shildi")


async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("topic", None)
    context.user_data.pop("photo", None)
    context.user_data.pop("desc", None)
    context.user_data.pop("size_type", None)
    context.user_data.pop("product_id", None)

    if not topics:
        await update.message.reply_text(
            "❗ Avval topic ochib /settopic buyrug'ini yuboring"
        )
        return ConversationHandler.END

    await update.message.reply_text("🔐 Admin parolini kiriting")
    return ADMIN_PASS


async def check_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Parol noto'g'ri, qayta kiriting")
        return ADMIN_PASS

    keyboard = []
    for name in topics:
        keyboard.append([InlineKeyboardButton(name, callback_data=name)])

    await update.message.reply_text(
        "📂 Topicni tanlang",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_TOPIC


async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["topic"] = query.data
    await query.message.reply_text("📸 Mahsulot rasmini yuboring")
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Mahsulot tavsifini yuboring")
    return DESC


async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["desc"] = update.message.text

    keyboard = [[
        InlineKeyboardButton("👕 Kiyim", callback_data="cloth"),
        InlineKeyboardButton("👟 Oyoq kiyim", callback_data="shoe")
    ]]

    await update.message.reply_text(
        "📏 O'lcham turini tanlang",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SIZE_TYPE


async def size_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["size_type"] = query.data
    await query.message.reply_text("🆔 Mahsulot ID ni kiriting")
    return PRODUCT_ID


async def finish_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = update.message.text.strip()

    if pid in products:
        await update.message.reply_text("❗ Bu ID mavjud")
        return PRODUCT_ID

    context.user_data["product_id"] = pid
    products[pid] = context.user_data.copy()
    save_data()

    topic_name = context.user_data["topic"]
    thread_id = topics[topic_name]

    caption = f"""📦 Mahsulot ID: {pid}

📝 Tavsif:
{context.user_data['desc']}

🛒 Buyurtma berish uchun tugmani bosing"""

    button = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🛒 Buyurtma berish",
            url=f"https://t.me/Buyurtma9020_bot?start=buy_{pid}"
        )
    ]])

    await context.bot.send_photo(
        chat_id=GROUP_ID,
        photo=context.user_data["photo"],
        caption=caption,
        message_thread_id=thread_id,
        reply_markup=button
    )

   await update.message.reply_text(
        "✅ Mahsulot topicga joylandi",
        reply_markup=ReplyKeyboardMarkup([["📦 Tovar joylash"]], resize_keyboard=True)
    )

async def order_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qty = update.message.text.strip()

    if not qty.isdigit():
        await update.message.reply_text("❗ Iltimos, son kiriting")
        return ORDER_QTY

    context.user_data["qty"] = qty

    keyboard = [
        [InlineKeyboardButton("39", callback_data="39")],
        [InlineKeyboardButton("40", callback_data="40")],
        [InlineKeyboardButton("41", callback_data="41")],
        [InlineKeyboardButton("42", callback_data="42")],
        [InlineKeyboardButton("43", callback_data="43")]
    ]

    await update.message.reply_text(
        "📏 O'lchamni tanlang",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ORDER_SIZE


async def order_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["size"] = query.data

    button = KeyboardButton("📞 Telefon yuborish", request_contact=True)

    await query.message.reply_text(
        "📲 Telefon raqamingizni yuboring",
        reply_markup=ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    )

    return ORDER_PHONE


async def order_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.contact:
        await update.message.reply_text("❗ Pastdagi tugma orqali telefon yuboring")
        return ORDER_PHONE
    if update.message.contact.user_id != update.effective_user.id:
        await update.message.reply_text("❗ Iltimos, o'zingizning raqamingizni yuboring")
        return ORDER_PHONE
    phone = update.message.contact.phone_number
    pid = context.user_data["product"]

    text = f"""🛒 YANGI BUYURTMA

Mahsulot: {pid}
O'lcham: {context.user_data['size']}
Soni: {context.user_data['qty']}

Tel: +{phone}"""

    await context.bot.send_message(
        chat_id=ORDER_GROUP_ID,
        text=text
    )

    await update.message.reply_text(
        "✅ Buyurtmangiz qabul qilindi",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
    
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["topic", "photo", "desc", "size_type", "product_id"]:
        context.user_data.pop(key, None)

    await update.message.reply_text("❌ Jarayon bekor qilindi")
    return ConversationHandler.END

def main():
    load_data()

    app = Application.builder().token(TOKEN).build()

    admin_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📦 Tovar joylash$"), add_product)
        ],
        states={
            ADMIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_pass)],
            SELECT_TOPIC: [CallbackQueryHandler(select_topic)],
            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],
            DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_desc)],
            SIZE_TYPE: [CallbackQueryHandler(size_type)],
            PRODUCT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, finish_product)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    order_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ORDER_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_qty)],
            ORDER_SIZE: [CallbackQueryHandler(order_size)],
            ORDER_PHONE: [
                MessageHandler((filters.CONTACT | filters.TEXT) & ~filters.COMMAND, order_phone)
            ],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("settopic", set_topic))
    app.add_handler(admin_conv)
    app.add_handler(order_conv)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
