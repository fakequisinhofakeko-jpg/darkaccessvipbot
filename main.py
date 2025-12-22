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

================= ADMIN =================

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
"👑 Painel Admin",
reply_markup=InlineKeyboardMarkup(teclado),
parse_mode="Markdown"
)

================= CALLBACKS ADMIN =================

async def admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
q = update.callback_query
await q.answer()

if q.data == "adm_remover":
admin_aguardando_id.add(q.from_user.id)
await q.message.reply_text("🗑️ Envie o ID do usuário para remover.")
return

texto = {
"adm_ativos": f"👥 Ativos: {len(usuarios_ativos)}",
"adm_pendentes": f"⏳ Pendentes: {len(pagamentos_pendentes)}",
"adm_aprovados": f"✅ Aprovados: {pagamentos_aprovados}",
"adm_total": f"💰 Total: R${total_arrecadado:.2f}"
}.get(q.data, "❌ Opção inválida.")

await q.message.reply_text(texto)

================= REMOVER USUÁRIO =================

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

await update.message.reply_text(f"✅ Usuário {uid} removido.", parse_mode="Markdown")

================= MAIN =================

def main():
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(escolher_plano, pattern="^plano_"))
app.add_handler(CallbackQueryHandler(confirmar, pattern="^confirmar$"))
app.add_handler(CallbackQueryHandler(moderar, pattern="^(aprovar|rejeitar)"))
app.add_handler(CallbackQueryHandler(admin_callbacks, pattern="^adm"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_id_remocao))

app.run_polling()

if name == "main":
main()
