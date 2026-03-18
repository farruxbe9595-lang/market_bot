import os
import json
import asyncio
import logging
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
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
    ORDER_PHONE,
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
            "products": products,
        }

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Data save error: {e}")

async def delete_after_delay(bot, chat_id, message_id, delay=5):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def restrict_topic_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if not msg:
        return

    if msg.chat_id != GROUP_ID:
        return

    if msg.message_thread_id is None:
        return

    if msg.from_user and msg.from_user.is_bot:
        return

    text = msg.text or msg.caption or ""

    if text.startswith("/settopic"):
        return

    try:
        await context.bot.delete_message(chat_id=msg.chat_id, message_id=msg.message_id)
    except Exception:
        return

    try:
        warn = await context.bot.send_message(
            chat_id=msg.chat_id,
            message_thread_id=msg.message_thread_id,
            text="❗ Bu yerda faqat buyurtma berishingiz mumkin.\n\nIltimos, chat bo'limida yozing."
        )
        context.application.create_task(
            delete_after_delay(context.bot, warn.chat_id, warn.message_id, 5)
        )
    except Exception:
        pass
        
async def is_admin(user_id, context):
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ["administrator", "creator"]
    except Exception:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args:
        for key in ["product", "qty", "size"]:
            context.user_data.pop(key, None)

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
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
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

async def list_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id, context):
        await update.message.reply_text("❌ Siz admin emassiz")
        return

    if not topics:
        await update.message.reply_text("📂 Topiclar yo'q")
        return

    text = "📂 Topiclar ro'yxati:\n\n"
    for name, tid in topics.items():
        text += f"• {name} → {tid}\n"

    await update.message.reply_text(text)


async def remove_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id, context):
        await update.message.reply_text("❌ Siz admin emassiz")
        return

    if not context.args:
        await update.message.reply_text("❗ Misol: /removetopic Krasofka")
        return

    topic_name = " ".join(context.args).strip()

    if topic_name not in topics:
        await update.message.reply_text("❗ Bunday topic topilmadi")
        return

    topics.pop(topic_name, None)
    save_data()

    await update.message.reply_text(f"🗑 {topic_name} o'chirildi")
    
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["topic", "photo", "desc", "size_type", "product_id"]:
        context.user_data.pop(key, None)

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
        reply_markup=InlineKeyboardMarkup(keyboard),
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
        InlineKeyboardButton("👟 Oyoq kiyim", callback_data="shoe"),
    ]]

    await update.message.reply_text(
        "📏 O'lcham turini tanlang",
        reply_markup=InlineKeyboardMarkup(keyboard),
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

    topic_name = context.user_data.get("topic")
    if not topic_name or topic_name not in topics:
        await update.message.reply_text("❗ Topic topilmadi, qaytadan boshlang")
        return ConversationHandler.END

    context.user_data["product_id"] = pid
    products[pid] = context.user_data.copy()
    save_data()

    thread_id = topics[topic_name]

    caption = f"""📦 Mahsulot ID: {pid}

📝 Tavsif:
{context.user_data['desc']}

🛒 Buyurtma berish uchun tugmani bosing"""

    button = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🛒 Buyurtma berish",
            url=f"https://t.me/Buyurtma9020_bot?start=buy_{pid}",
        )
    ]])

    await context.bot.send_photo(
        chat_id=GROUP_ID,
        photo=context.user_data["photo"],
        caption=caption,
        message_thread_id=thread_id,
        reply_markup=button,
    )

    await update.message.reply_text(
        "✅ Mahsulot topicga joylandi",
        reply_markup=ReplyKeyboardMarkup([["📦 Tovar joylash"]], resize_keyboard=True),
    )
    return ConversationHandler.END


async def order_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qty = update.message.text.strip()

    if not qty.isdigit():
        await update.message.reply_text("❗ Iltimos, son kiriting")
        return ORDER_QTY

    context.user_data["qty"] = qty

    pid = context.user_data["product"]
    product = products.get(pid, {})
    size_type = product.get("size_type", "")

    if size_type == "cloth":
        keyboard = [
            [InlineKeyboardButton("XS", callback_data="XS"), InlineKeyboardButton("S", callback_data="S")],
            [InlineKeyboardButton("M", callback_data="M"), InlineKeyboardButton("L", callback_data="L")],
            [InlineKeyboardButton("XL", callback_data="XL"), InlineKeyboardButton("XXL", callback_data="XXL")],
            [InlineKeyboardButton("3-4 yosh", callback_data="3-4 yosh")],
            [InlineKeyboardButton("5-6 yosh", callback_data="5-6 yosh")],
            [InlineKeyboardButton("7-8 yosh", callback_data="7-8 yosh")],
            [InlineKeyboardButton("9-10 yosh", callback_data="9-10 yosh")],
            [InlineKeyboardButton("11-12 yosh", callback_data="11-12 yosh")],
            [InlineKeyboardButton("Bolalar o'lchami", callback_data="Bolalar o'lchami")]
        ]
        text = "👕 Kiyim o'lchamini tanlang"

    elif size_type == "shoe":
        keyboard = [
            [InlineKeyboardButton("26", callback_data="26"), InlineKeyboardButton("27", callback_data="27")],
            [InlineKeyboardButton("28", callback_data="28"), InlineKeyboardButton("29", callback_data="29")],
            [InlineKeyboardButton("30", callback_data="30"), InlineKeyboardButton("31", callback_data="31")],
            [InlineKeyboardButton("32", callback_data="32"), InlineKeyboardButton("33", callback_data="33")],
            [InlineKeyboardButton("34", callback_data="34"), InlineKeyboardButton("35", callback_data="35")],
            [InlineKeyboardButton("36", callback_data="36"), InlineKeyboardButton("37", callback_data="37")],
            [InlineKeyboardButton("38", callback_data="38"), InlineKeyboardButton("39", callback_data="39")],
            [InlineKeyboardButton("40", callback_data="40"), InlineKeyboardButton("41", callback_data="41")],
            [InlineKeyboardButton("42", callback_data="42"), InlineKeyboardButton("43", callback_data="43")],
            [InlineKeyboardButton("44", callback_data="44"), InlineKeyboardButton("45", callback_data="45")],
            [InlineKeyboardButton("Bolalar o'lchami", callback_data="Bolalar o'lchami")]
        ]
        text = "👟 Oyoq kiyim o'lchamini tanlang"

    else:
        keyboard = [
            [InlineKeyboardButton("Standart", callback_data="Standart")]
        ]
        text = "📏 O'lchamni tanlang"

    await update.message.reply_text(
        text,
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
        reply_markup=ReplyKeyboardMarkup([[button]], resize_keyboard=True),
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

    user = update.effective_user
    buyer_id = user.id
    buyer_name = user.full_name
    buyer_username = user.username

    product = products.get(pid, {})
    size_type = product.get("size_type", "")
    selected_size = context.user_data.get("size", "")

    if size_type == "cloth":
        size_text = f"👕 {selected_size}"
    elif size_type == "shoe":
        size_text = f"👟 {selected_size}"
    else:
        size_text = f"📏 {selected_size}"

    buyer_mention = f'<a href="tg://user?id={buyer_id}">{buyer_name}</a>'

    text = f"""🛒 <b>YANGI BUYURTMA</b>

👤 Buyurtmachi: {buyer_mention}
🆔 Mahsulot: {pid}
📏 O'lcham: {size_text}
📦 Soni: {context.user_data['qty']}
📞 Tel: +{phone}"""

    if buyer_username:
        write_url = f"https://t.me/{buyer_username}"
    else:
        write_url = f"tg://user?id={buyer_id}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✉️ Buyurtmachiga yozish", url=write_url)]
    ])

    await context.bot.send_message(
        chat_id=ORDER_GROUP_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
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

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["product", "qty", "size"]:
        context.user_data.pop(key, None)

    await update.message.reply_text("❌ Buyurtma jarayoni bekor qilindi")
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
        allow_reentry=True,
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
        fallbacks=[CommandHandler("cancel", cancel_order)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("settopic", set_topic))
    app.add_handler(CommandHandler("listtopics", list_topics))
    app.add_handler(CommandHandler("removetopic", remove_topic))
    app.add_handler(admin_conv)
    app.add_handler(order_conv)
    app.add_handler(
        MessageHandler(
            filters.Chat(chat_id=GROUP_ID),
            restrict_topic_messages
        ),
        group=10
    )

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
