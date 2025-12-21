import os
import sqlite3
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

if not BOT_TOKEN or not GROUP_ID or not ADMIN_ID:
    raise RuntimeError("Variáveis obrigatórias não definidas")

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
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan TEXT,
    value REAL,
    status TEXT,
    date TEXT
)
""")

conn.commit()

# ================= HELPERS =================
def save_user(user_id, plan, expires):
    cursor.execute(
        "REPLACE INTO users (user_id, plan, expires_at) VALUES (?, ?, ?)",
        (user_id, plan, expires)
    )
    conn.commit()

def remove_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()

def log_payment(user_id, plan, value, status):
    cursor.execute(
        "INSERT INTO payments (user_id, plan, value, status, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, plan, value, status, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )
    conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🔥 Ver planos VIP", callback_data="plans")]]
    await update.message.reply_text(
        "🔞 *AVISO LEGAL*\n"
        "O grupo contém conteúdo adulto +18 (anime).\n"
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

    context.user_data["pending_plan"] = plan_key

    kb = [[InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirm_payment")]]

    await q.edit_message_text(
        f"📌 Plano: {plan['name']}\n"
        f"💰 Valor: R${plan['price']}\n\n"
        f"🔑 *Chave PIX:*\n`{PIX_KEY}`\n\n"
        f"Após pagar, clique em *Confirmar pagamento*.",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

# ================= CONFIRMAR =================
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_key = context.user_data.get("pending_plan")
    plan = PLANS[plan_key]

    log_payment(q.from_user.id, plan["name"], plan["price"], "pendente")

    kb = [
        [
            InlineKeyboardButton("✅ Aprovar", callback_data=f"approve_{q.from_user.id}_{plan_key}"),
            InlineKeyboardButton("❌ Rejeitar", callback_data=f"reject_{q.from_user.id}")
        ]
    ]

    await context.bot.send_message(
        ADMIN_ID,
        f"💰 *Novo pagamento pendente*\n\n"
        f"👤 {q.from_user.id}\n"
        f"📌 {plan['name']} – R${plan['price']}",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

    await q.edit_message_text("⏳ Pagamento enviado para aprovação.")

# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data.split("_")
    action = data[0]
    user_id = int(data[1])
    plan_key = data[2] if action == "approve" else None

    if action == "approve":
        plan = PLANS[plan_key]
        expires = (
            (datetime.now() + timedelta(days=plan["days"])).isoformat()
            if plan["days"] else None
        )

        save_user(user_id, plan_key, expires)
        log_payment(user_id, plan["name"], plan["price"], "aprovado")

        invite = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)

        await context.bot.send_message(
            user_id,
            f"✅ Pagamento aprovado!\n\n🔓 Acesse o grupo:\n{invite.invite_link}"
        )

        await q.edit_message_text("✅ Aprovado")

    else:
        log_payment(user_id, "-", 0, "rejeitado")
        await context.bot.send_message(user_id, "❌ Pagamento rejeitado.")
        await q.edit_message_text("❌ Rejeitado")

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*), SUM(value) FROM payments WHERE status='aprovado'")
    count, total = cursor.fetchone()
    total = total or 0

    await update.message.reply_text(
        f"👑 *Painel Admin*\n\n"
        f"🧾 Vendas: {count}\n"
        f"💰 Total arrecadado: R${total:.2f}",
        parse_mode="Markdown"
    )

# ================= EXPIRAÇÃO =================
async def expiration_loop(app):
    while True:
        await asyncio.sleep(300)
        now = datetime.now()

        cursor.execute("SELECT user_id, expires_at FROM users WHERE expires_at IS NOT NULL")
        for uid, exp in cursor.fetchall():
            if datetime.fromisoformat(exp) <= now:
                try:
                    await app.bot.ban_chat_member(GROUP_ID, uid)
                    await app.bot.unban_chat_member(GROUP_ID, uid)
                except:
                    pass
                remove_user(uid)

# ================= DAILY REPORT =================
async def daily_report(app):
    while True:
        await asyncio.sleep(86400)
        cursor.execute("SELECT COUNT(*), SUM(value) FROM payments WHERE status='aprovado'")
        count, total = cursor.fetchone()
        total = total or 0

        await app.bot.send_message(
            ADMIN_ID,
            f"📊 *Relatório Diário*\n\n"
            f"🧾 Vendas: {count}\n"
            f"💰 Total: R${total:.2f}",
            parse_mode="Markdown"
        )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(show_plans, pattern="^plans$"))
    app.add_handler(CallbackQueryHandler(buy, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(confirm_payment, pattern="^confirm_payment$"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern="^(approve|reject)_"))

    app.create_task(expiration_loop(app))
    app.create_task(daily_report(app))

    app.run_polling()

if __name__ == "__main__":
    main()
