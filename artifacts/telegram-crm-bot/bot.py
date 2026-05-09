import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from database import Database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()

ADD_NAME, ADD_PHONE, ADD_EMAIL, ADD_NOTES = range(4)
SEARCH_INPUT = range(1)
EDIT_FIELD, EDIT_VALUE = range(2)

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add client", callback_data="add_client")],
        [InlineKeyboardButton("🔍 Find client", callback_data="find_client")],
        [InlineKeyboardButton("📋 All clients", callback_data="all_clients")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to your CRM bot!\n\nWhat would you like to do?",
        reply_markup=main_menu_keyboard(),
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "What would you like to do?",
        reply_markup=main_menu_keyboard(),
    )


async def add_client_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("📝 Let's add a new client.\n\nEnter the client's *full name*:", parse_mode="Markdown")
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("📞 Enter the client's *phone number*:", parse_mode="Markdown")
    return ADD_PHONE


async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["phone"] = update.message.text.strip()
    await update.message.reply_text(
        "📧 Enter the client's *email* (or send /skip to leave empty):",
        parse_mode="Markdown"
    )
    return ADD_EMAIL


async def add_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 Add any *notes* about this client (or send /skip to leave empty):",
        parse_mode="Markdown"
    )
    return ADD_NOTES


async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["email"] = ""
    await update.message.reply_text(
        "📝 Add any *notes* about this client (or send /skip to leave empty):",
        parse_mode="Markdown"
    )
    return ADD_NOTES


async def add_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notes"] = update.message.text.strip()
    return await save_client(update, context)


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notes"] = ""
    return await save_client(update, context)


async def save_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    client_id = db.add_client(
        name=data.get("name", ""),
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        notes=data.get("notes", ""),
    )
    keyboard = [[InlineKeyboardButton("⬅️ Back to menu", callback_data="menu")]]
    await update.message.reply_text(
        f"✅ *Client saved!*\n\n"
        f"👤 Name: {data.get('name')}\n"
        f"📞 Phone: {data.get('phone')}\n"
        f"📧 Email: {data.get('email') or '—'}\n"
        f"📝 Notes: {data.get('notes') or '—'}\n"
        f"🆔 ID: `{client_id}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def find_client_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔍 Enter a *name* or *phone number* to search:",
        parse_mode="Markdown"
    )
    return SEARCH_INPUT


async def search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = update.message.text.strip()
    clients = db.search_clients(query_text)

    if not clients:
        keyboard = [
            [InlineKeyboardButton("🔍 Search again", callback_data="find_client")],
            [InlineKeyboardButton("⬅️ Back to menu", callback_data="menu")],
        ]
        await update.message.reply_text(
            f"😕 No clients found for *{query_text}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    for client in clients:
        await send_client_card(update, client)

    await update.message.reply_text(
        f"Found *{len(clients)}* client(s).",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END


async def send_client_card(update_or_query, client):
    cid, name, phone, email, notes, created_at = client
    keyboard = [
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{cid}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{cid}"),
        ]
    ]
    text = (
        f"👤 *{name}*\n"
        f"📞 {phone}\n"
        f"📧 {email or '—'}\n"
        f"📝 {notes or '—'}\n"
        f"📅 Added: {created_at[:10]}\n"
        f"🆔 ID: `{cid}`"
    )
    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update_or_query.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def all_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    clients = db.get_all_clients()

    if not clients:
        await query.edit_message_text(
            "📋 No clients yet. Add your first one!",
            reply_markup=main_menu_keyboard(),
        )
        return

    await query.edit_message_text(f"📋 You have *{len(clients)}* client(s):", parse_mode="Markdown")
    for client in clients:
        await send_client_card(query, client)

    await query.message.reply_text("What would you like to do?", reply_markup=main_menu_keyboard())


async def delete_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    client = db.get_client(client_id)
    if not client:
        await query.edit_message_text("Client not found.")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, delete", callback_data=f"confirm_delete_{client_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="menu"),
        ]
    ]
    await query.edit_message_text(
        f"🗑 Are you sure you want to delete *{client[1]}*?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[2])
    client = db.get_client(client_id)
    name = client[1] if client else "Client"
    db.delete_client(client_id)
    await query.edit_message_text(
        f"✅ *{name}* has been deleted.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def edit_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    client_id = int(query.data.split("_")[1])
    context.user_data["edit_client_id"] = client_id
    client = db.get_client(client_id)
    if not client:
        await query.edit_message_text("Client not found.")
        return

    keyboard = [
        [InlineKeyboardButton("👤 Name", callback_data=f"editfield_{client_id}_name")],
        [InlineKeyboardButton("📞 Phone", callback_data=f"editfield_{client_id}_phone")],
        [InlineKeyboardButton("📧 Email", callback_data=f"editfield_{client_id}_email")],
        [InlineKeyboardButton("📝 Notes", callback_data=f"editfield_{client_id}_notes")],
        [InlineKeyboardButton("⬅️ Cancel", callback_data="menu")],
    ]
    await query.edit_message_text(
        f"✏️ Editing *{client[1]}*\n\nWhich field would you like to update?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def edit_field_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    client_id = int(parts[1])
    field = parts[2]
    context.user_data["edit_client_id"] = client_id
    context.user_data["edit_field"] = field
    field_labels = {"name": "Name", "phone": "Phone", "email": "Email", "notes": "Notes"}
    await query.edit_message_text(
        f"✏️ Enter the new *{field_labels[field]}*:",
        parse_mode="Markdown"
    )
    return EDIT_VALUE


async def edit_value_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_value = update.message.text.strip()
    client_id = context.user_data.get("edit_client_id")
    field = context.user_data.get("edit_field")
    db.update_client_field(client_id, field, new_value)
    client = db.get_client(client_id)
    keyboard = [[InlineKeyboardButton("⬅️ Back to menu", callback_data="menu")]]
    await update.message.reply_text(
        f"✅ *{field.capitalize()}* updated!\n\n"
        f"👤 Name: {client[1]}\n"
        f"📞 Phone: {client[2]}\n"
        f"📧 Email: {client[3] or '—'}\n"
        f"📝 Notes: {client[4] or '—'}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    context.user_data.clear()
    return ConversationHandler.END


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable not set")

    app = Application.builder().token(token).build()

    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_client_start, pattern="^add_client$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
            ADD_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_email),
                CommandHandler("skip", skip_email),
            ],
            ADD_NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_notes),
                CommandHandler("skip", skip_notes),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        per_chat=True,
    )

    find_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(find_client_start, pattern="^find_client$")],
        states={
            SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        per_chat=True,
    )

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_field_prompt, pattern=r"^editfield_\d+_\w+$")],
        states={
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        per_chat=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv)
    app.add_handler(find_conv)
    app.add_handler(edit_conv)
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.add_handler(CallbackQueryHandler(all_clients, pattern="^all_clients$"))
    app.add_handler(CallbackQueryHandler(delete_client, pattern=r"^delete_\d+$"))
    app.add_handler(CallbackQueryHandler(confirm_delete, pattern=r"^confirm_delete_\d+$"))
    app.add_handler(CallbackQueryHandler(edit_client, pattern=r"^edit_\d+$"))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
