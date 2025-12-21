import os
import uuid
import asyncio
import sqlite3
import requests
from datetime import datetime, timedelta
from functools import partial

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MP_API = "https://api.mercadopago.com/checkout/preferences"
DB_FILE = "database.db"

# ================== PLANOS ==================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90, "days": 30},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90, "days": 90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90, "days": None},
}

# ================== DATABASE ==================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    plan TEXT,
    expires_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan TEXT,
    value REAL,
    date TEXT
)
""")

conn.commit()

# ================== HELPERS ==================
def get_user(user_id):
    cursor.execute("SELECT plan, expires_at FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def save_user(user_id, plan, expires):
    cursor.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan, expires)
    )
    conn.commit()

def log_payment(user_id, plan, value):
    cursor.execute(
        "INSERT INTO logs (user_id, plan, value, date) VALUES (?, ?, ?, ?)",
        (user_id, plan, value, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 *ACESSO VIP EXCLUSIVO*\n\n⚡ Liberação automática\n🔒 Conteúdo premium",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================== PLANOS ==================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await q.edit_message_text("💥 *Escolha seu plano:*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ================== MERCADO PAGO ==================
def criar_checkout(plan_key, user_id):
    plan = PLANS[plan_key]
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}

    data = {
        "items": [{
            "title": plan["name"],
            "quantity": 1,
            "unit_price": plan["price"]
        }],
        "external_reference": f"{user_id}|{plan_key}",
        "auto_return": "approved"
    }

    return requests.post(MP_API, headers=headers, json=data).json()

async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data.replace("buy_", "")
    user_id = q.from_user.id

    checkout = criar_checkout(plan_key, user_id)
    link = checkout["init_point"]

    context.user_data["renew_plan"] = plan_key

    kb = [
        [InlineKeyboardButton("💳 Pagar com cartão / PIX", url=link)],
        [InlineKeyboardButton("🔁 Renovar depois", callback_data="renew")]
    ]

    await q.edit_message_text(
        f"📌 Plano: {PLANS[plan_key]['name']}\n💰 Valor: R${PLANS[plan_key]['price']}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================== RENOVAÇÃO ==================
async def renew(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_key = context.user_data.get("renew_plan")
    if not plan_key:
        return

    checkout = criar_checkout(plan_key, update.callback_query.from_user.id)
    await update.callback_query.edit_message_text(
        "🔁 *Renovação gerada:*",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("💳 Renovar agora", url=checkout["init_point"])]]
        ),
        parse_mode="Markdown"
    )

# ================== ADMIN ==================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        [InlineKeyboardButton("👥 Usuários ativos", callback_data="admin_users")],
        [InlineKeyboardButton("🧾 Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("📊 Financeiro hoje", callback_data="admin_today")],
        [InlineKeyboardButton("📈 Financeiro semana", callback_data="admin_week")]
    ]

    await update.message.reply_text("👑 *Painel Admin*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# ================== ADMIN CALLBACKS ==================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cursor.execute("SELECT user_id, plan, expires_at FROM users")
    rows = cursor.fetchall()

    if not rows:
        await q.edit_message_text("Nenhum usuário ativo.")
        return

    text = "👥 Usuários:\n\n"
    for u, p, e in rows:
        text += f"{u} — {p} — {e or 'Vitalício'}\n"

    await q.edit_message_text(text)

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cursor.execute("SELECT plan, value, date FROM logs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()

    if not rows:
        await q.edit_message_text("Nenhum log.")
        return

    text = "🧾 Logs:\n\n"
    for p, v, d in rows:
        text += f"{p} — R${v} — {d}\n"

    await q.edit_message_text(text)

async def admin_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    today = datetime.now().strftime("%d/%m/%Y")
    cursor.execute("SELECT SUM(value) FROM logs WHERE date LIKE ?", (f"%{today}%",))
    total = cursor.fetchone()[0] or 0

    await q.edit_message_text(f"💰 Total hoje: R${total}")

async def admin_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    week_ago = datetime.now() - timedelta(days=7)
    cursor.execute("SELECT SUM(value) FROM logs WHERE date >= ?", (week_ago.strftime("%d/%m/%Y"),))
    total = cursor.fetchone()[0] or 0

    await q.edit_message_text(f"📈 Total 7 dias: R${total}")

# ================== AVISO DE VENCIMENTO ==================
async def expiration_warning(app):
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for u, e in cursor.fetchall():
            if (datetime.fromisoformat(e) - now).days == 3:
                await app.bot.send_message(u, "⚠️ Seu VIP vence em 3 dias. Renove para não perder acesso.")

# ================== MAIN ==================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(renew, pattern="^renew$"))

    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_logs, pattern="^admin_logs$"))
    app.add_handler(CallbackQueryHandler(admin_today, pattern="^admin_today$"))
    app.add_handler(CallbackQueryHandler(admin_week, pattern="^admin_week$"))

    asyncio.create_task(expiration_warning(app))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
