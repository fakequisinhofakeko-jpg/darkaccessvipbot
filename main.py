import os
import sqlite3
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MP_API = "https://api.mercadopago.com/checkout/preferences"
DB_FILE = "database.db"

# ================= DATABASE =================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

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

# ================= PLANOS =================
PLANS = {
    "vip_1": ("VIP 1 Mês", 24.90),
    "vip_3": ("VIP 3 Meses", 64.90),
    "vip_vitalicio": ("VIP Vitalício", 149.90)
}

# ================= HELPERS =================
def create_checkout(plan_key, user_id):
    name, price = PLANS[plan_key]

    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    data = {
        "items": [{
            "title": name,
            "quantity": 1,
            "unit_price": price
        }],
        "external_reference": f"{user_id}|{plan_key}",
        "auto_return": "approved"
    }

    r = requests.post(MP_API, headers=headers, json=data)
    return r.json()["init_point"]

def log_payment(user_id, plan, value):
    cursor.execute(
        "INSERT INTO logs (user_id, plan, value, date) VALUES (?, ?, ?, ?)",
        (user_id, plan, value, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🚨 *ACESSO VIP EXCLUSIVO*\n\n💳 PIX ou Cartão\n🔒 Conteúdo premium",
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
        "💥 *Escolha seu plano:*",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= COMPRA =================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = q.data.replace("buy_", "")
    user_id = q.from_user.id

    link = create_checkout(plan_key, user_id)

    kb = [[InlineKeyboardButton("💳 Pagar agora (PIX / Cartão)", url=link)]]

    await q.edit_message_text(
        f"📌 Plano: {PLANS[plan_key][0]}\n💰 Valor: R${PLANS[plan_key][1]}",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*), SUM(value) FROM logs")
    count, total = cursor.fetchone()
    total = total or 0

    await update.message.reply_text(
        f"👑 *Painel Admin*\n\n"
        f"🧾 Vendas: {count}\n"
        f"💰 Total arrecadado: R${total}",
        parse_mode="Markdown"
    )

# ================= MAIN =================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
