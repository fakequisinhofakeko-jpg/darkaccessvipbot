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
GROUP_ID = -1003325505558
PIX_KEY = "d506a3da-1aab-4dd3-8655-260b48e04bfa"

START_IMAGE_URL = "https://i.postimg.cc/X7tcHPD0/images.jpg"
PENDENTE_TTL = 15 * 60  # 15 minutos

# ================= PLANOS =================
PLANOS = {
    "vip1": {
        "id": "vip1",
        "nome": "VIP 1 Mês",
        "valor": 35.00,
        "dias": 30
    },
    "vip_vitalicio": {
        "id": "vip_vitalicio",
        "nome": "VIP Vitalício",
        "valor": 45.00,
        "dias": None
    },
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}
comprovantes_recebidos = set()
total_arrecadado = 0.0
pagamentos_aprovados = 0

# ================= UTIL =================
def is_admin(update: Update):
    return update.effective_user.id == ADMIN_ID


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
        "🔞 Conteúdo adulto explícito\n"
        "🔒 Área VIP privada\n\n"
        "💳 Pagamento via **PIX**\n"
        "📸 Envie o comprovante\n"
        "⚠️ Confirmações sem pagamento serão rejeitadas"
    )

    teclado = [
    [InlineKeyboardButton("🔥 VIP 1 Mês — R$35", callback_data="plano_vip1")],
    [InlineKeyboardButton("💎 VIP Vitalício — R$45", callback_data="plano_vip_vitalicio")],
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
    plano = PLANOS[q.data.replace("plano_", "")]

    pagamentos_pendentes[uid] = {
        "plano": plano,
        "created_at": time.time()
    }

    await q.message.reply_text(
        f"📦 **{plano['nome']}**\n"
        f"💰 Valor: R${plano['valor']}\n\n"
        f"🔑 **PIX:**\n`{PIX_KEY}`\n\n"
        "📸 Envie o comprovante aqui no chat\n"
        "⚠️ O botão de confirmação só aparecerá após o envio.",
        parse_mode="Markdown"
    )

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

    if not dados or uid not in comprovantes_recebidos:
        await q.message.reply_text("❌ Envie o comprovante primeiro.")
        return

    plano = dados["plano"]
    user = q.from_user
    nome = user.full_name
    username = f"@{user.username}" if user.username else "(sem @)"

    await context.bot.send_message(
        ADMIN_ID,
        f"🚨 NOVO PAGAMENTO\n\n"
        f"👤 {nome} {username}\n"
        f"🆔 {uid}\n"
        f"📦 {plano['nome']}\n"
        f"💰 R${plano['valor']}",
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{uid}"),
                InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{uid}")
            ]]
        )
    )

    await q.message.reply_text("⏳ Enviado para aprovação.")

# ================= MODERAR =================
async def moderar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    acao, uid = q.data.split("_")
    uid = int(uid)
    plano = pagamentos_pendentes[uid]["plano"]

    if acao == "aprovar":
        link = await context.bot.create_chat_invite_link(GROUP_ID, member_limit=1)
        expira = None if plano["dias"] is None else datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[uid] = {"plano": plano["id"], "expira_em": expira}
        await context.bot.send_message(uid, f"✅ Acesso liberado\n🔗 {link.invite_link}")
    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")

    pagamentos_pendentes.pop(uid, None)
    comprovantes_recebidos.discard(uid)
    await q.message.edit_reply_markup(None)

# ================= PAINEL ADM =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return

    await update.message.reply_text(
        f"👑 PAINEL ADM\n\n"
        f"👥 Ativos: {len(usuarios_ativos)}\n"
        f"⏳ Pendentes: {len(pagamentos_pendentes)}\n"
        f"💰 Total: R${total_arrecadado:.2f}\n"
        f"✅ Aprovados: {pagamentos_aprovados}"
    )

async def clientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    texto = "👥 CLIENTES ATIVOS\n\n"
    for uid, d in usuarios_ativos.items():
        texto += f"{uid} — expira {d['expira_em']}\n"
    await update.message.reply_text(texto or "Nenhum cliente.")

async def pendentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    texto = "⏳ PENDENTES\n\n"
    for uid, d in pagamentos_pendentes.items():
        texto += f"{uid} — {d['plano']['nome']}\n"
    await update.message.reply_text(texto or "Nenhum pendente.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    msg = " ".join(context.args)
    for uid in usuarios_ativos:
        try:
            await context.bot.send_message(uid, f"📢 {msg}")
        except:
            pass
    await update.message.reply_text("📢 Mensagem enviada.")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("admin", admin, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("clientes", clientes, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("pendentes", pendentes, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("broadcast", broadcast, filters=filters.ChatType.PRIVATE))

    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="^confirmar$"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, receber_comprovante))

    app.run_polling()

if __name__ == "__main__":
    main()
