import os
import uuid
import requests
import sqlite3
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

MP_API = "https://api.mercadopago.com/v1/payments"
DB_FILE = "database.db"

app_instance = None  # usado para log automático do admin

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
    username TEXT,
    plan TEXT,
    value REAL,
    date TEXT
)
""")

conn.commit()

# ================= HELPERS =================
def get_user(user_id):
    cursor.execute("SELECT plan, expires_at FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def save_user(user_id, plan, expires):
    cursor.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan, expires)
    )
    conn.commit()

def remove_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()

def log_payment(user_id, username, plan, value):
    cursor.execute(
        "INSERT INTO logs (user_id, username, plan, value, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, plan, value, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

# ================= LOG AUTOMÁTICO ADMIN =================
async def notify_admin_payment(user, plan_name, value):
    try:
        username = f"@{user.username}" if user.username else f"ID {user.id}"

        message = (
            "💰 *PAGAMENTO APROVADO*\n\n"
            f"👤 Usuário: {username}\n"
            f"📦 Plano: {plan_name}\n"
            f"💵 Valor: R${value}\n"
            f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

        await app_instance.bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print("Erro ao enviar log para admin:", e)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 *ACESSO VIP EXCLUSIVO*\n\n"
        "⚡ Liberação automática\n"
        "🔒 Conteúdo premium\n\n"
        "👇 Clique abaixo:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= PLANOS =================
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = [
        [InlineKeyboardButton("💎 VIP 1 Mês – R$24,90", callback_data="buy_vip_1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses – R$64,90", callback_data="buy_vip_3")],
        [InlineKeyboardButton("👑 VIP Vitalício – R$149,90", callback_data="buy_vip_vitalicio")]
    ]

    await q.edit_message_text(
        "💥 *Escolha seu plano VIP:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= MERCADO PAGO =================
def criar_pix(plan_key, user_id):
    plan = PLANS[plan_key]

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4())
    }

    data = {
        "transaction_amount": float(plan["price"]),
        "description": plan["name"],
        "payment_method_id": "pix",
        "payer": {
            "email": f"user{user_id}@vip.com",
            "identification": {"type": "CPF", "number": "11111111111"}
        }
    }

    return requests.post(MP_API, headers=headers, json=data, timeout=20).json()

# ================= COMPRAR =================
async def buy_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user_id = q.from_user.id
    plan_key = q.data.replace("buy_", "")

    existing = get_user(user_id)
    if existing and existing[0] == "vip_vitalicio":
        await q.edit_message_text(
            "👑 *Você já possui VIP Vitalício.*\n\nNão é necessário comprar novamente.",
            parse_mode="Markdown"
        )
        return

    pix = criar_pix(plan_key, user_id)

    try:
        data = pix["point_of_interaction"]["transaction_data"]
        pix_code = data["qr_code"]
        checkout = data.get("ticket_url")
        payment_id = pix["id"]
    except Exception:
        await q.edit_message_text("❌ Erro ao gerar pagamento.")
        return

    context.user_data["payment_id"] = payment_id
    context.user_data["plan"] = plan_key

    buttons = []
    if checkout:
        buttons.append([InlineKeyboardButton("💳 Pagar com cartão", url=checkout)])
    buttons.append([InlineKeyboardButton("🔄 Verificar pagamento", callback_data="check_payment")])

    await q.edit_message_text(
        f"💳 *Pagamento VIP*\n\n"
        f"📌 Plano: {PLANS[plan_key]['name']}\n"
        f"💰 Valor: R${PLANS[plan_key]['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{pix_code}`",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# ================= VERIFICAR =================
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    payment_id = context.user_data.get("payment_id")
    plan_key = context.user_data.get("plan")

    r = requests.get(
        f"{MP_API}/{payment_id}",
        headers={"Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
        timeout=15
    ).json()

    if r.get("status") == "approved":
        plan = PLANS[plan_key]
        expires = (
            (datetime.now() + timedelta(days=plan["days"])).isoformat()
            if plan["days"] else None
        )

        save_user(q.from_user.id, plan_key, expires)
        log_payment(q.from_user.id, q.from_user.username, plan["name"], plan["price"])

        await notify_admin_payment(q.from_user, plan["name"], plan["price"])

        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)

        await q.edit_message_text(
            "✅ *Pagamento aprovado!*\n\n"
            f"🔓 Acesso liberado:\n{invite.invite_link}",
            parse_mode="Markdown"
        )
    else:
        await q.edit_message_text("⏳ Pagamento ainda não aprovado.")

# ================= BACKGROUND =================
async def expiration_loop(app):
    while True:
        await asyncio.sleep(300)
        now = datetime.now()

        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for user_id, expires in cursor.fetchall():
            if datetime.fromisoformat(expires) <= now:
                try:
                    await app.bot.ban_chat_member(GROUP_ID, user_id)
                    await app.bot.unban_chat_member(GROUP_ID, user_id)
                except:
                    pass
                remove_user(user_id)

async def warning_loop(app):
    while True:
        await asyncio.sleep(3600)
        now = datetime.now()

        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for user_id, expires in cursor.fetchall():
            exp = datetime.fromisoformat(expires)
            if 0 < (exp - now).days == 3:
                try:
                    await app.bot.send_message(
                        user_id,
                        "⚠️ *Seu VIP vence em 3 dias!*",
                        parse_mode="Markdown"
                    )
                except:
                    pass

async def post_init(app):
    app.create_task(expiration_loop(app))
    app.create_task(warning_loop(app))

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        [InlineKeyboardButton("👥 Usuários ativos", callback_data="admin_users")],
        [InlineKeyboardButton("🧾 Logs de pagamento", callback_data="admin_logs")]
    ]

    await update.message.reply_text(
        "👑 *Painel Administrativo*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cursor.execute("SELECT user_id, plan, expires_at FROM users")
    rows = cursor.fetchall()

    if not rows:
        await q.edit_message_text("Nenhum usuário ativo.")
        return

    text = "👥 *Usuários VIP:*\n\n"
    for uid, plan, exp in rows:
        exp_txt = "Vitalício" if not exp else datetime.fromisoformat(exp).strftime("%d/%m/%Y")
        text += f"🆔 {uid} — {plan} — {exp_txt}\n"

    await q.edit_message_text(text, parse_mode="Markdown")

async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    cursor.execute("SELECT user_id, plan, value, date FROM logs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()

    if not rows:
        await q.edit_message_text("Nenhum pagamento registrado.")
        return

    text = "🧾 *Últimos pagamentos:*\n\n"
    for uid, plan, value, date in rows:
        text += f"👤 {uid}\n💳 {plan} — R${value}\n📅 {date}\n\n"

    await q.edit_message_text(text, parse_mode="Markdown")

# ================= MAIN =================
def main():
    global app_instance
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app_instance = app

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy_plan, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_logs, pattern="^admin_logs$"))

    app.run_polling()

if __name__ == "__main__":
    main()
