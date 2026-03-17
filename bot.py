import os
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
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

ADMIN_PASSWORD = "1234"

GROUP_ID = -1003618675735
ORDER_GROUP_ID = -1003631320685

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

async def is_admin(user_id, context):
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False
        
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    # 🔥 1. Agar deep-link orqali kelgan bo‘lsa (client)
    if context.args:
        data = context.args[0]

        if data.startswith("buy_"):
            pid = data.split("_")[1]

            context.user_data["product"] = pid

            await update.message.reply_text(
                f"📦 Mahsulot ID: {pid}\n\n📦 Nechta olmoqchisiz?"
            )

            return ORDER_QTY

    # 🔐 2. Adminni tekshirish (ID orqali)
    ADMIN_IDS = [123456789]  # 👈 o'zingizni telegram ID qo'ying

    if user_id in ADMIN_IDS:
        keyboard = [["📦 Tovar joylash"]]

        await update.message.reply_text(
            "📦 Admin panelga xush kelibsiz",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    else:
        # 👤 Oddiy user
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\nMahsulotni tanlab 'Buyurtma berish' tugmasini bosing."
        )
async def set_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message

    if msg.message_thread_id is None:
        await msg.reply_text("❗ Bu buyruqni topic ichida yuboring")
        return

    thread_id = msg.message_thread_id

    try:
        topic_name = msg.reply_to_message.forum_topic_created.name
    except:
        topic_name = f"Topic {thread_id}"

    topics[topic_name] = thread_id

    await msg.reply_text(f"✅ {topic_name} topic ro'yxatga qo'shildi")


async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not topics:

        await update.message.reply_text(
            "❗ Avval topic ochib /settopic buyrug'ini yuboring"
        )

        return ConversationHandler.END

    await update.message.reply_text("🔐 Admin parolini kiriting")

    return ADMIN_PASS


async def check_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text != ADMIN_PASSWORD:

        await update.message.reply_text("❌ Parol noto'g'ri")

        return ConversationHandler.END

    keyboard = []

    for name in topics:

        keyboard.append(
            [InlineKeyboardButton(name, callback_data=name)]
        )

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

    keyboard = [
        [
            InlineKeyboardButton("👕 Kiyim", callback_data="cloth"),
            InlineKeyboardButton("👟 Oyoq kiyim", callback_data="shoe")
        ]
    ]

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

    pid = update.message.text

    if pid in products:

        await update.message.reply_text("❗ Bu ID mavjud")

        return PRODUCT_ID

    context.user_data["product_id"] = pid

    products[pid] = context.user_data.copy()

    topic_name = context.user_data["topic"]

    thread_id = topics[topic_name]

    caption = f"""
📦 Mahsulot ID: {pid}

📝 Tavsif:
{context.user_data['desc']}

🛒 Buyurtma berish uchun tugmani bosing
"""

    button = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛒 Buyurtma berish",
                url=f"https://t.me/Buyurtma9020_bot?start=buy_{pid}"
            )
        ]
    ])

    await context.bot.send_photo(
        chat_id=GROUP_ID,
        photo=context.user_data["photo"],
        caption=caption,
        message_thread_id=thread_id,
        reply_markup=button
    )

    await update.message.reply_text("✅ Mahsulot topicga joylandi")

    return ConversationHandler.END


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    pid = query.data.split("_")[1]

    context.user_data["product"] = pid

    await query.message.reply_text("📦 Mahsulot sonini yozing")

    return ORDER_QTY


async def order_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["qty"] = update.message.text

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

    phone = update.message.contact.phone_number

    pid = context.user_data["product"]

    text = f"""
🛒 YANGI BUYURTMA

Mahsulot: {pid}
O'lcham: {context.user_data['size']}
Soni: {context.user_data['qty']}

Tel: +{phone}
"""

    await context.bot.send_message(
        chat_id=ORDER_GROUP_ID,
        text=text
    )

    await update.message.reply_text("✅ Buyurtmangiz qabul qilindi")

    return ConversationHandler.END


def main():

    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(

        entry_points=[
            MessageHandler(filters.TEXT & filters.Regex("Tovar joylash"), add_product),
            CommandHandler("start", start)
        ],

        states={

            ADMIN_PASS: [MessageHandler(filters.TEXT, check_pass)],

            SELECT_TOPIC: [CallbackQueryHandler(select_topic)],

            PHOTO: [MessageHandler(filters.PHOTO, get_photo)],

            DESC: [MessageHandler(filters.TEXT, get_desc)],

            SIZE_TYPE: [CallbackQueryHandler(size_type)],

            PRODUCT_ID: [MessageHandler(filters.TEXT, finish_product)],

            ORDER_QTY: [MessageHandler(filters.TEXT, order_qty)],

            ORDER_SIZE: [CallbackQueryHandler(order_size)],

            ORDER_PHONE: [MessageHandler(filters.CONTACT, order_phone)]

        },

        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CommandHandler("settopic", set_topic))

    app.add_handler(conv)

    app.run_polling()


if __name__ == "__main__":
    main()
