from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from datetime import datetime, timedelta
import time

# ================= CONFIG =================
BOT_TOKEN = "8444138111:AAGuhgOzBtMsrNRQ1Zj2_pKuquMXi7jcHGo"
ADMIN_ID = 1208316553
GROUP_ID = -1003513694224
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

START_IMAGE_URL = "https://crooked-pink-lw2jbcf2ie-06nqwkliyr.edgeone.dev/0c4c705a6047a4fcb4d85b8d2f27660c.jpg"

PENDENTE_TTL = 15 * 60  # 15 minutos

# ================= PLANOS =================
PLANOS = {
    "vip1": {"id": "vip1", "nome": "VIP 1 Mês", "valor": 25.90, "dias": 30},
    "vip6": {"id": "vip6", "nome": "VIP 6 Meses", "valor": 55.90, "dias": 90},
    "vip_vitalicio": {"id": "vip_vitalicio", "nome": "VIP Vitalício", "valor": 99.90, "dias": None},
}

# ================= DADOS =================
pagamentos_pendentes = {}      # uid -> {plano, created_at}
usuarios_ativos = {}
confirmacoes_enviadas = set()
comprovantes_recebidos = set()
total_arrecadado = 0.0
pagamentos_aprovados = 0
admin_aguardando_id = set()

# ================= UTIL =================
async def verificar_expiracoes(context):
    agora = datetime.now()
    for uid, dados in list(usuarios_ativos.items()):
        if dados["expira_em"] and dados["expira_em"] <= agora:
            try:
                await context.bot.ban_chat_member(GROUP_ID, uid)
                await context.bot.unban_chat_member(GROUP_ID, uid)
            except:
                pass
            usuarios_ativos.pop(uid, None)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await verificar_expiracoes(context)

    texto = (
        "⚠️ **AVISO DE CONTEÚDO ADULTO (+18)**\n\n"
        "🔞 Conteúdo adulto explícito do tipo Anime\n\n"
        "💳 Pagamento via **PIX**\n"
        "📸 Envie o comprovante\n"
        "⚠️ Confirmações sem pagamento serão rejeitadas"
    )

    teclado = [
        [InlineKeyboardButton("🔥 VIP 1 Mês", callback_data="plano_vip1")],
        [InlineKeyboardButton("🔥 VIP 6 Meses", callback_data="plano_vip6")],
        [InlineKeyboardButton("💎 VIP Vitalício", callback_data="plano_vip_vitalicio")],
    ]

    await update.message.reply_photo(
        photo=START_IMAGE_URL,
        caption=texto,
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= ESCOLHER PLANO =================
async def escolher_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    plano_id = q.data.replace("plano_", "")
    plano = PLANOS[plano_id]

    pagamentos_pendentes[uid] = {
        "plano": plano,
        "created_at": time.time()
    }

    texto = (
        f"📦 **{plano['nome']}**\n"
        f"💰 Valor: R${plano['valor']}\n\n"
        f"🔑 **PIX:**\n`{PIX_KEY}`\n\n"
        "📸 **Envie o comprovante aqui no chat**\n"
        "⚠️ O botão de confirmação só aparecerá após o envio."
    )

    await q.message.reply_text(texto, parse_mode="Markdown")

# ================= RECEBER COMPROVANTE =================
async def receber_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in pagamentos_pendentes:
        return

    comprovantes_recebidos.add(uid)

    await update.message.reply_text(
        "📸 Comprovante recebido.\nAgora clique para confirmar.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar")]]
        )
    )

# ================= CONFIRMAR =================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    dados = pagamentos_pendentes.get(uid)

    if not dados:
        await q.message.reply_text("❌ Pedido expirado ou inexistente.")
        return

    if uid not in comprovantes_recebidos:
        await q.message.reply_text("📸 Envie o comprovante primeiro.")
        return

    if time.time() - dados["created_at"] > PENDENTE_TTL:
        pagamentos_pendentes.pop(uid, None)
        comprovantes_recebidos.discard(uid)
        await q.message.reply_text("⏳ Pedido expirado. Gere outro.")
        return

    plano = dados["plano"]

    teclado = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{uid}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{uid}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"🚨 NOVO PAGAMENTO\n\n👤 ID: {uid}\n📦 {plano['nome']}\n💰 R${plano['valor']}",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

    await q.message.reply_text("⏳ Enviado para aprovação.")

# ================= MODERAR =================
async def moderar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    acao, uid = q.data.split("_")
    uid = int(uid)
    dados = pagamentos_pendentes.get(uid)

    if not dados:
        await q.message.reply_text("⚠️ Pedido já encerrado.")
        return

    plano = dados["plano"]
    global total_arrecadado, pagamentos_aprovados

    if acao == "aprovar":
        link = await context.bot.create_chat_invite_link(
            GROUP_ID, member_limit=1, expire_date=int(time.time()) + 600
        )

        expira = None if plano["dias"] is None else datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[uid] = {"plano": plano["id"], "expira_em": expira}

        total_arrecadado += plano["valor"]
        pagamentos_aprovados += 1

        await context.bot.send_message(uid, f"✅ Aprovado!\n🔗 {link.invite_link}")
        await q.message.reply_text("✅ Pedido aprovado.")
    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")
        await q.message.reply_text("❌ Pedido rejeitado.")

    await q.message.edit_reply_markup(reply_markup=None)

    pagamentos_pendentes.pop(uid, None)
    comprovantes_recebidos.discard(uid)
    confirmacoes_enviadas.discard(uid)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="^confirmar$"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))

    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, receber_comprovante))

    app.run_polling()

if __name__ == "__main__":
    main()
