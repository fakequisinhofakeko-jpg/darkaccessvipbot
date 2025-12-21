# ===================== BOT VIP TELEGRAM | PIX MANUAL | ADMIN APROVA =====================
# Python 3.11 | python-telegram-bot v20+
# NÃO use asyncio.run() — run_polling já gerencia o loop

import os
import sqlite3
import uuid
import threading
import time
from datetime import datetime, timedelta

import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN or not GROUP_ID or not ADMIN_ID:
    raise RuntimeError("❌ Defina BOT_TOKEN, GROUP_ID e ADMIN_ID nas variáveis de ambiente")

DB_FILE = "database.db"

# ===================== PLANOS =====================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": "R$24,90", "days": 30},
    "vip_3": {"name": "VIP 3 Meses", "price": "R$64,90", "days": 90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": "R$149,90", "days": None},
}

# ===================== DATABASE =====================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT,
    expires_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    plan TEXT,
    status TEXT,
    created_at TEXT
)
""")

conn.commit()

# ===================== HELPERS DB =====================
def save_payment(user_id, username, plan):
    cur.execute(
        "INSERT INTO payments (user_id, username, plan, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, username or "-", plan, "pending", datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

def approve_payment(user_id, plan_key):
    plan = PLANS[plan_key]
    expires = None
    if plan["days"]:
        expires = (datetime.now() + timedelta(days=plan["days"])).isoformat()

    cur.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan_key, expires)
    )
    cur.execute(
        "UPDATE payments SET status='approved' WHERE user_id=? AND status='pending'",
        (user_id,)
    )
    conn.commit()

def get_users():
    cur.execute("SELECT user_id, plan, expires_at FROM users")
    return cur.fetchall()

def get_stats():
    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN status='approved' THEN 1 END) FROM payments")
    total, approved = cur.fetchone()
    return total or 0, approved or 0

# ===================== CLEAN CHAT (30 MIN) =====================
def schedule_cleanup(bot, chat_id, message_ids, delay=1800):
    def worker():
        time.sleep(delay)
        for mid in message_ids:
            try:
                bot.delete_message(chat_id, mid)
            except:
                pass
    threading.Thread(target=worker, daemon=True).start()

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔞 *AVISO LEGAL*\n"
        "O grupo VIP contém conteúdo adulto +18 (anime).\n"
        "Ao continuar, você declara ser maior de 18 anos.\n\n"
        "📌 Pagamento via PIX\n"
        "🔒 Conteúdo premium"
    )

    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]

    msg = await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

    context.user_data["cleanup"] = [msg.message_id]

# ===================== PLANOS =====================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")],
    ]

    await q.edit_message_text(
        "💥 *Escolha seu plano VIP:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ===================== BUY (PIX MANUAL) =====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data.replace("buy_", "")
    plan = PLANS[plan_key]

    context.user_data["plan"] = plan_key

    text = (
        f"💳 *Pagamento via PIX*\n\n"
        f"📌 Plano: {plan['name']}\n"
        f"💰 Valor: {plan['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n"
        f"`SUA_CHAVE_PIX_AQUI`\n\n"
        f"📷 Envie o comprovante aqui no chat e depois toque em **Confirmar Pagamento**."
    )

    kb = [[InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirm_payment")]]

    msg = await q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

    context.user_data.setdefault("cleanup", []).append(msg.message_id)

# ===================== RECEIVE PROOF =====================
async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Apenas registra que o comprovante chegou
    await update.message.reply_text(
        "📥 Comprovante recebido.\nAguarde a confirmação do administrador."
    )

# ===================== CONFIRM (USER) =====================
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user
    plan_key = context.user_data.get("plan")

    if not plan_key:
        await q.edit_message_text("❌ Sessão expirada. Use /start novamente.")
        return

    save_payment(user.id, user.username, plan_key)

    await q.edit_message_text(
        "⏳ Pagamento em análise.\nVocê será notificado após aprovação."
    )

# ===================== ADMIN PANEL =====================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    total, approved = get_stats()

    kb = [
        [InlineKeyboardButton("👥 Usuários ativos", callback_data="admin_users")],
        [InlineKeyboardButton("🧾 Vendas", callback_data="admin_sales")],
    ]

    await update.message.reply_text(
        f"👑 *Painel Admin*\n\n"
        f"📊 Vendas totais: {total}\n"
        f"✅ Aprovadas: {approved}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    rows = get_users()
    if not rows:
        await q.edit_message_text("Nenhum usuário ativo.")
        return

    text = "👥 *Usuários VIP:*\n\n"
    for uid, plan, exp in rows:
        exp_txt = "Vitalício" if not exp else datetime.fromisoformat(exp).strftime("%d/%m/%Y")
        text += f"🆔 {uid} — {plan} — {exp_txt}\n"

    await q.edit_message_text(text, parse_mode="Markdown")

async def admin_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cur.execute("SELECT user_id, plan, status, created_at FROM payments ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()

    if not rows:
        await q.edit_message_text("Nenhuma venda.")
        return

    text = "🧾 *Últimas vendas:*\n\n"
    for uid, plan, status, date in rows:
        text += f"👤 {uid}\n📦 {plan}\n📌 {status}\n📅 {date}\n\n"

    await q.edit_message_text(text, parse_mode="Markdown")

# ===================== ADMIN APPROVE =====================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Use: /aprovar USER_ID PLANO")
        return

    user_id = int(context.args[0])
    plan_key = context.args[1]

    approve_payment(user_id, plan_key)

    invite = await context.bot.create_chat_invite_link(
        GROUP_ID,
        member_limit=1,
        expire_date=int(time.time()) + 600
    )

    await context.bot.send_message(
        user_id,
        f"✅ *Pagamento aprovado!*\n\n"
        f"🔓 Acesse o grupo:\n{invite.invite_link}",
        parse_mode="Markdown"
    )

# ===================== MAIN =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("aprovar", approve))

    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_payment$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_sales, pattern="^admin_sales$"))

    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_proof))

    print("🤖 Bot iniciado com sucesso")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
