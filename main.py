import os
import sqlite3
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

if not BOT_TOKEN or not GROUP_ID or not ADMIN_ID:
    raise RuntimeError("Variáveis obrigatórias não configuradas")

# ================= PLANOS =================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90, "days": 30},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90, "days": 90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90, "days": None},
}

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT,
    expires_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    plan TEXT,
    status TEXT,
    date TEXT
)
""")

conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔞 *AVISO LEGAL*\n"
        "O grupo VIP contém conteúdo adulto +18 (anime).\n"
        "Ao continuar, você declara ser maior de 18 anos.\n\n"
        "📌 Pagamento via PIX\n"
        "🔒 Conteúdo premium"
    )

    kb = [[InlineKeyboardButton("🔥 Ver planos", callback_data="plans")]]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await q.edit_message_text(
        "📦 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= COMPRA =================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data.replace("buy_", "")
    plan = PLANS[plan_key]

    context.user_data["plan"] = plan_key

    kb = [
        [InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirm_payment")]
    ]

    await q.edit_message_text(
        f"📦 *Plano:* {plan['name']}\n"
        f"💰 *Valor:* R${plan['price']}\n\n"
        f"🔑 *Chave PIX:*\n`{PIX_KEY}`\n\n"
        "Após pagar, clique em *Confirmar pagamento*.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= CONFIRMAÇÃO =================
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user
    plan_key = context.user_data.get("plan")

    cursor.execute(
        "INSERT INTO payments (user_id, username, plan, status, date) VALUES (?, ?, ?, ?, ?)",
        (
            user.id,
            user.username,
            plan_key,
            "pending",
            datetime.now().strftime("%d/%m/%Y %H:%M")
        )
    )
    conn.commit()

    await context.bot.send_message(
        ADMIN_ID,
        f"💰 *NOVA SOLICITAÇÃO*\n\n"
        f"👤 @{user.username}\n"
        f"🆔 `{user.id}`\n"
        f"📦 {PLANS[plan_key]['name']}\n\n"
        f"Use:\n/aprovar {user.id}\n/recusar {user.id}",
        parse_mode="Markdown"
    )

    await q.edit_message_text(
        "⏳ Pagamento enviado para análise.\n"
        "Aguarde a confirmação."
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) FROM payments")
    total, approved = cursor.fetchone()

    await update.message.reply_text(
        f"👑 *PAINEL ADMIN*\n\n"
        f"📥 Solicitações: {total}\n"
        f"✅ Aprovadas: {approved}\n\n"
        f"🔑 PIX:\n`{PIX_KEY}`",
        parse_mode="Markdown"
    )

# ================= APROVAR =================
async def aprovar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    user_id = int(context.args[0])

    cursor.execute("SELECT plan FROM payments WHERE user_id=? AND status='pending'", (user_id,))
    row = cursor.fetchone()
    if not row:
        await update.message.reply_text("Pagamento não encontrado.")
        return

    plan_key = row[0]
    plan = PLANS[plan_key]

    expires = (
        (datetime.now() + timedelta(days=plan["days"])).isoformat()
        if plan["days"] else None
    )

    cursor.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan_key, expires)
    )
    cursor.execute(
        "UPDATE payments SET status='approved' WHERE user_id=?",
        (user_id,)
    )
    conn.commit()

    invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)

    await context.bot.send_message(
        user_id,
        f"✅ *Pagamento aprovado!*\n\n"
        f"🔓 Acesso VIP:\n{invite.invite_link}",
        parse_mode="Markdown"
    )

    await update.message.reply_text("Aprovado com sucesso.")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("aprovar", aprovar))

    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_payment$"))

    app.run_polling()

if __name__ == "__main__":
    main()
