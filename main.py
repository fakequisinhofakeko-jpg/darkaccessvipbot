import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GROUP_ID = int(os.getenv("GROUP_ID"))

DB_FILE = "database.db"

PIX_COPIA_COLA = """00020126580014br.gov.bcb.pix
0136944ea988-65d3-45ef-a7ee-f8c96b1e1235
520400005303986540524.90
5802BR
5912VITORMIGUELS
6009Sao Paulo
62250521mpqrinter13822789047563047432
"""

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
def save_user(user_id, plan_key):
    plan = PLANS[plan_key]
    expires = None
    if plan["days"]:
        expires = (datetime.now() + timedelta(days=plan["days"])).isoformat()

    cursor.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan_key, expires)
    )
    conn.commit()

def log_payment(user_id, plan_key):
    cursor.execute(
        "INSERT INTO logs (user_id, plan, value, date) VALUES (?, ?, ?, ?)",
        (user_id, PLANS[plan_key]["name"], PLANS[plan_key]["price"],
         datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]

    await update.message.reply_text(
        "🔞 *AVISO LEGAL*\n"
        "Este bot contém *conteúdo adulto +18 (anime)*.\n"
        "Ao continuar, você declara ser maior de 18 anos.\n\n"
        "📌 Pagamento via PIX\n"
        "🔒 Conteúdo premium",
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
    plan = PLANS[plan_key]

    await q.edit_message_text(
        f"📌 *Plano:* {plan['name']}\n"
        f"💰 *Valor:* R${plan['price']}\n\n"
        f"🔑 *PIX Copia e Cola:*\n`{PIX_COPIA_COLA}`\n\n"
        "📸 Após o pagamento, envie o comprovante para o admin.",
        parse_mode="Markdown"
    )

# ================= CONFIRMAÇÃO ADMIN =================
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        user_id = int(context.args[0])
        plan_key = context.args[1]
    except:
        await update.message.reply_text("Uso: /confirmar user_id plano")
        return

    save_user(user_id, plan_key)
    log_payment(user_id, plan_key)

    invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)

    await context.bot.send_message(
        user_id,
        f"✅ *Pagamento confirmado!*\n\n🔓 Acesso:\n{invite.invite_link}",
        parse_mode="Markdown"
    )

    await update.message.reply_text("✅ Usuário liberado.")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*), SUM(value) FROM logs")
    vendas, total = cursor.fetchone()
    total = total or 0

    await update.message.reply_text(
        f"👑 *Painel Admin*\n\n"
        f"🧾 Vendas: {vendas}\n"
        f"💰 Total arrecadado: R${total}",
        parse_mode="Markdown"
    )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("confirmar", confirm))
    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))

    print("🤖 Bot iniciado com sucesso")
    app.run_polling()

if __name__ == "__main__":
    main()
