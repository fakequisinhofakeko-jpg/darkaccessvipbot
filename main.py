import asyncio
import os
import asyncio
import requests
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
    ContextTypes
)
async def verificador_automatico(app):
    while True:
        await asyncio.sleep(60)  # verifica a cada 1 minuto

        for user_id, info in list(pagamentos.items()):
            if info["status"] == "pending":
                dados = verificar_pagamento(info["payment_id"])

                if dados.get("status") == "approved":
                    info["status"] = "approved"
                    expira = datetime.now() + timedelta(days=info["dias"])

                    try:
                        await app.bot.unban_chat_member(GROUP_ID, user_id)
                        await app.bot.send_message(
                            chat_id=user_id,
                            text=(
                                "✅ *Pagamento aprovado automaticamente!*\n\n"
                                f"📌 Plano: {info['plano']}\n"
                                f"⏰ Expira em: {expira.strftime('%d/%m/%Y')}"
                            ),
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print("Erro ao liberar acesso:", e)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

pagamentos = {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("📌 Planos", callback_data="planos")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")]
    ]
    await update.message.reply_text(
        "🔥 *Dark Access VIP*\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= PLANOS =================
async def planos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [
        [InlineKeyboardButton("💎 1 Mês - R$24,90", callback_data="vip_1m")],
        [InlineKeyboardButton("🔥 3 Meses - R$64,90", callback_data="vip_3m")],
        [InlineKeyboardButton("👑 Vitalício - R$149,90", callback_data="vip_vip")]
    ]
    await update.callback_query.message.reply_text(
        "📌 Escolha seu plano:",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# ================= PIX =================
def criar_pix(valor, descricao):
    url = "https://api.mercadopago.com/v1/payments"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "transaction_amount": valor,
        "description": descricao,
        "payment_method_id": "pix",
        "payer": {"email": "cliente@vip.com"}
    }
    r = requests.post(url, json=data, headers=headers)
    return r.json()

async def gerar_pix(update: Update, plano, valor, dias):
    user_id = update.callback_query.from_user.id
    pagamento = criar_pix(valor, plano)

    pagamentos[user_id] = {
        "payment_id": pagamento["id"],
        "plano": plano,
        "valor": valor,
        "dias": dias,
        "status": "pending"
    }

    texto = (
        f"💳 *Pagamento PIX*\n\n"
        f"📌 Plano: {plano}\n"
        f"💰 Valor: R${valor}\n\n"
        f"`{pagamento['point_of_interaction']['transaction_data']['qr_code']}`"
    )

    teclado = [
        [InlineKeyboardButton("🔄 Verificar pagamento", callback_data="verificar")]
    ]

    await update.callback_query.message.reply_text(
        texto,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

# ================= VERIFICAR PAGAMENTO =================
def verificar_pagamento(payment_id):
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    return requests.get(url, headers=headers).json()

async def verificar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id

    if user_id not in pagamentos:
        await update.callback_query.message.reply_text("❌ Nenhum pagamento encontrado.")
        return

    info = pagamentos[user_id]
    dados = verificar_pagamento(info["payment_id"])

    if dados["status"] == "approved":
        await liberar_acesso(update, context, info)
    else:
        await update.callback_query.message.reply_text(
            "⏳ Pagamento ainda não aprovado.\nStatus: pending"
        )

# ================= LIBERAR ACESSO =================
async def liberar_acesso(update, context, info):
    user_id = update.callback_query.from_user.id
    expira = datetime.now() + timedelta(days=info["dias"])

    await context.bot.unban_chat_member(GROUP_ID, user_id)

    await update.callback_query.message.reply_text(
        f"✅ *Pagamento aprovado!*\n\n"
        f"📌 Plano: {info['plano']}\n"
        f"⏰ Expira em: {expira.strftime('%d/%m/%Y')}",
        parse_mode="Markdown"
    )

# ================= CALLBACKS =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "planos":
        await planos(update, context)

    elif data == "vip_1m":
        await gerar_pix(update, "VIP 1 Mês", 24.9, 30)

    elif data == "vip_3m":
        await gerar_pix(update, "VIP 3 Meses", 64.9, 90)

    elif data == "vip_vip":
        await gerar_pix(update, "VIP Vitalício", 149.9, 3650)

    elif data == "verificar":
        await verificar(update, context)

# ================= MAIN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))

print("🤖 Bot online com sucesso!")
app.run_polling()
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callbacks))

app.create_task(verificador_automatico(app))

print("🤖 Bot online com verificação automática!")
app.run_polling()
