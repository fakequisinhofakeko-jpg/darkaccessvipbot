import os
import uuid
import asyncio
import sqlite3
import requests
from functools import partial
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not all([BOT_TOKEN, MP_ACCESS_TOKEN, GROUP_ID, ADMIN_ID]):
    raise RuntimeError("Variáveis obrigatórias não definidas")

MP_API = "https://api.mercadopago.com/v1/payments"
DB_FILE = "database.db"

# ================= PLANOS =================
PLANS = {
    "vip_1": {"name": "VIP 1 Mês", "price": 24.90, "days": 30},
    "vip_3": {"name": "VIP 3 Meses", "price": 64.90, "days": 90},
    "vip_vitalicio": {"name": "VIP Vitalício", "price": 149.90, "days": None},
}

# ================= DATABASE =================
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

# ================= HELPERS =================
def get_user(uid):
    cursor.execute("SELECT plan, expires_at FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone()

def save_user(uid, plan, expires):
    cursor.execute("REPLACE INTO users VALUES (?, ?, ?)", (uid, plan, expires))
    conn.commit()

def log_payment(uid, plan, value):
    cursor.execute(
        "INSERT INTO logs (user_id, plan, value, date) VALUES (?, ?, ?, ?)",
        (uid, plan, value, datetime.now().isoformat())
    )
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 *ACESSO VIP EXCLUSIVO*\n\n⚡ Liberação automática\n🔒 Conteúdo premium",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("💎 VIP 1 Mês", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício", callback_data="buy_vip_vitalicio")]
    ]
    await q.edit_message_text("Escolha seu plano:", reply_markup=InlineKeyboardMarkup(kb))

# ================= MERCADO PAGO =================
def _pix_sync(plan_key, uid):
    plan = PLANS[plan_key]
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }
    data = {
        "transaction_amount": plan["price"],
        "description": plan["name"],
        "payment_method_id": "pix",
        "payer": {"email": f"user{uid}@vip.com"}
    }
    return requests.post(MP_API, headers=headers, json=data, timeout=20).json()

async def criar_pix(plan_key, uid):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_pix_sync, plan_key, uid))

# ================= COMPRA =================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data.replace("buy_", "")
    uid = q.from_user.id

    pix = await criar_pix(plan_key, uid)
    data = pix["point_of_interaction"]["transaction_data"]

    context.user_data["payment_id"] = pix["id"]
    context.user_data["plan"] = plan_key

    kb = [[InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")]]

    await q.edit_message_text(
        f"Plano: {PLANS[plan_key]['name']}\n"
        f"Valor: R${PLANS[plan_key]['price']}\n\n"
        f"PIX:\n`{data['qr_code']}`",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= VERIFICAR =================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    pid = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    r = requests.get(f"{MP_API}/{pid}", headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}).json()

    if r.get("status") != "approved":
        await q.edit_message_text("⏳ Pagamento ainda não aprovado.")
        return

    plan = PLANS[plan_key]
    user = get_user(q.from_user.id)

    if plan["days"]:
        base = datetime.fromisoformat(user[1]) if user and user[1] else datetime.now()
        expires = (base + timedelta(days=plan["days"])).isoformat()
    else:
        expires = None

    save_user(q.from_user.id, plan_key, expires)
    log_payment(q.from_user.id, plan["name"], plan["price"])

    invite = await q.bot.create_chat_invite_link(GROUP_ID, member_limit=1)

    await q.edit_message_text(f"✅ Acesso liberado:\n{invite.invite_link}")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        [InlineKeyboardButton("👥 Usuários ativos", callback_data="admin_users")],
        [InlineKeyboardButton("🧾 Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("💰 Resumo financeiro", callback_data="admin_finance")]
    ]
    await update.message.reply_text("Painel Admin", reply_markup=InlineKeyboardMarkup(kb))

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    await q.edit_message_text(str(rows) if rows else "Nenhum usuário ativo.")

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cursor.execute("SELECT plan, value, date FROM logs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    await q.edit_message_text(str(rows) if rows else "Nenhum log.")

async def admin_finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    now = datetime.now()
    cursor.execute("SELECT value, date FROM logs")
    rows = cursor.fetchall()

    daily = sum(v for v, d in rows if datetime.fromisoformat(d).date() == now.date())
    weekly = sum(v for v, d in rows if datetime.fromisoformat(d) >= now - timedelta(days=7))

    await q.edit_message_text(f"💰 Hoje: R${daily}\n📊 7 dias: R${weekly}")

# ================= LOOPS =================
async def expiration_loop(app):
    while True:
        await asyncio.sleep(300)
        now = datetime.now()
        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for uid, exp in cursor.fetchall():
            if datetime.fromisoformat(exp) <= now:
                await app.bot.ban_chat_member(GROUP_ID, uid)
                await app.bot.unban_chat_member(GROUP_ID, uid)
                cursor.execute("DELETE FROM users WHERE user_id=?", (uid,))
                conn.commit()

async def warning_loop(app):
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()
        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for uid, exp in cursor.fetchall():
            if (datetime.fromisoformat(exp) - now).days == 3:
                await app.bot.send_message(uid, "⚠️ Seu VIP vence em 3 dias!")

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(show_plans, "^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, "^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, "^check_payment$"))
    app.add_handler(CallbackQueryHandler(admin_users, "^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_logs, "^admin_logs$"))
    app.add_handler(CallbackQueryHandler(admin_finance, "^admin_finance$"))

    asyncio.create_task(expiration_loop(app))
    asyncio.create_task(warning_loop(app))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
