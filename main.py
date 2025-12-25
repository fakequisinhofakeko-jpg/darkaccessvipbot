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

# ================= PLANOS =================
PLANOS = {
    "vip1": {"id": "vip1", "nome": "VIP 1 Mês", "valor": 25.90, "dias": 30},
    "vip3": {"id": "vip3", "nome": "VIP 3 Meses", "valor": 55.90, "dias": 90},
    "vip_vitalicio": {"id": "vip_vitalicio", "nome": "VIP Vitalício", "valor": 119.90, "dias": None},
}

# ================= DADOS =================
pagamentos_pendentes = {}
usuarios_ativos = {}
confirmacoes_enviadas = set()
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
    "🔞 Este grupo contém **conteúdo adulto explícito do tipo Anime**,\n"
    "destinado **exclusivamente a maiores de 18 anos**.\n\n"
    "Ao prosseguir e adquirir o acesso VIP, você declara que:\n\n"
    "✔️ Possui **18 anos ou mais**\n"
    "✔️ Está ciente da **natureza adulta do conteúdo**\n"
    "✔️ Acessa por **livre e espontânea vontade**\n"
    "✔️ Assume total responsabilidade pelo acesso\n\n"
    "🚫 É **terminantemente proibido** o acesso por menores de idade.\n"
    "📵 É proibido **compartilhar, redistribuir ou revender** o conteúdo.\n\n"
    "💳 Pagamento via **PIX**\n"
    "🔒 Acesso **VIP privado e exclusivo**"
    )

    teclado = [
        [InlineKeyboardButton("🔥 VIP 1 Mês", callback_data="plano_vip1")],
        [InlineKeyboardButton("🔥 VIP 3 Meses", callback_data="plano_vip3")],
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
    await verificar_expiracoes(context)

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    plano_id = q.data.replace("plano_", "")
    plano = PLANOS[plano_id]

    ativo = usuarios_ativos.get(uid)
    if ativo and ativo["plano"] == plano_id and (ativo["expira_em"] is None or ativo["expira_em"] > datetime.now()):
        await q.message.reply_text("⚠️ Você já possui esse plano ativo.")
        return

    pagamentos_pendentes[uid] = plano

    # 🔹 TEXTO DO PIX (AJUSTADO COMO VOCÊ PEDIU)
    texto = (
        f"📦 **{plano['nome']}**\n"
        f"💰 Valor: R${plano['valor']}\n\n"
        f"🔑 **PIX Copia e Cola:**\n`{PIX_KEY}`\n\n"
        "📸 **Logo após o pagamento, envie o comprovante**\n"
        "e em seguida toque em **Confirmar pagamento**."
    )

    await q.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Confirmar pagamento", callback_data="confirmar")]]
        ),
        parse_mode="Markdown"
    )

# ================= CONFIRMAR =================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    if uid in confirmacoes_enviadas:
        return

    plano = pagamentos_pendentes.get(uid)
    if not plano:
        await q.message.reply_text("❌ Nenhum pagamento pendente.")
        return

    confirmacoes_enviadas.add(uid)

    teclado = [[
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{uid}"),
        InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{uid}")
    ]]

    await context.bot.send_message(
        ADMIN_ID,
        f"💳 PAGAMENTO PENDENTE\n\n👤 ID: {uid}\n📦 {plano['nome']}\n💰 R${plano['valor']}",
        reply_markup=InlineKeyboardMarkup(teclado)
    )

    await q.message.reply_text("⏳ Pagamento enviado para aprovação.")

# ================= MODERAR =================
async def moderar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    acao, uid = q.data.split("_")
    uid = int(uid)

    plano = pagamentos_pendentes.get(uid)
    if not plano:
        return

    global total_arrecadado, pagamentos_aprovados

    if acao == "aprovar":
        link = await context.bot.create_chat_invite_link(
            GROUP_ID,
            member_limit=1,
            expire_date=int(time.time()) + 600
        )

        expira = None if plano["dias"] is None else datetime.now() + timedelta(days=plano["dias"])
        usuarios_ativos[uid] = {"plano": plano["id"], "expira_em": expira}

        total_arrecadado += plano["valor"]
        pagamentos_aprovados += 1

        await context.bot.send_message(uid, f"✅ Aprovado!\n\n🔗 {link.invite_link}")
    else:
        await context.bot.send_message(uid, "❌ Pagamento rejeitado.")

    pagamentos_pendentes.pop(uid, None)
    confirmacoes_enviadas.discard(uid)

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    teclado = [
        [InlineKeyboardButton("👥 Usuários ativos", callback_data="adm_ativos")],
        [InlineKeyboardButton("⏳ Pagamentos pendentes", callback_data="adm_pendentes")],
        [InlineKeyboardButton("✅ Pagamentos aprovados", callback_data="adm_aprovados")],
        [InlineKeyboardButton("💰 Total arrecadado", callback_data="adm_total")],
        [InlineKeyboardButton("🗑️ Remover usuário", callback_data="adm_remover")],
    ]

    await update.message.reply_text(
        "👑 **Painel Admin**",
        reply_markup=InlineKeyboardMarkup(teclado),
        parse_mode="Markdown"
    )

# ================= CALLBACKS ADMIN =================
async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "adm_remover":
        admin_aguardando_id.add(q.from_user.id)
        await q.message.reply_text("🗑️ Envie o **ID do usuário** para remover.")
        return

    texto = {
        "adm_ativos": f"👥 Ativos: {len(usuarios_ativos)}",
        "adm_pendentes": f"⏳ Pendentes: {len(pagamentos_pendentes)}",
        "adm_aprovados": f"✅ Aprovados: {pagamentos_aprovados}",
        "adm_total": f"💰 Total: R${total_arrecadado:.2f}"
    }.get(q.data, "❌ Opção inválida.")

    await q.message.reply_text(texto)

# ================= REMOVER USUÁRIO =================
async def receber_id_remocao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or update.effective_user.id not in admin_aguardando_id:
        return

    try:
        uid = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ ID inválido.")
        return

    try:
        await context.bot.ban_chat_member(GROUP_ID, uid)
        await context.bot.unban_chat_member(GROUP_ID, uid)
    except:
        pass

    usuarios_ativos.pop(uid, None)
    pagamentos_pendentes.pop(uid, None)
    admin_aguardando_id.discard(update.effective_user.id)

    await update.message.reply_text(f"✅ Usuário `{uid}` removido.", parse_mode="Markdown")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("admin", admin, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
    app.add_handler(CallbackQueryHandler(confirmar, pattern="^confirmar$"))
    app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)_"))
    app.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^adm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_id_remocao))

    app.run_polling()

if __name__ == "__main__":
    main()
