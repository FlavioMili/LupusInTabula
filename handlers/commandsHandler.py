from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from classes.enums import GameState, Role
from handlers.gameHandlers import GameHandler
import config
import asyncio

gameHandler = GameHandler()

async def newGame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in gameHandler.games:
        await update.message.reply_text("Partita gia' in corso")
        return
    if update.effective_chat.type == 'private':
        await update.message.reply_text("Puoi iniziare una partita solo in un gruppo")
        return

    gameHandler.newGame(chat_id, context.application)
    keyboard = [[InlineKeyboardButton("Partecipa!", callback_data="join")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    join_msg = await update.message.reply_text(
        f"Nuova partita iniziata, premi il pulsante per partecipare.\nMin: {config.MIN_GIOCATORI} giocatori, Max: {config.MAX_GIOCATORI} giocatori",
        reply_markup=reply_markup
    )
    gameHandler.games[chat_id].join_message_id = join_msg.message_id  

    def start_game_job(job_context):
        job_context.application.create_task(gameHandler.games[chat_id].startGame())

    gameHandler.games[chat_id].startTimer(start_game_job, 0)

async def joinGame(update: Update, context: ContextTypes.DEFAULT_TYPE, from_button=False):
    if from_button:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.first_name
    else:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name

    if chat_id not in gameHandler.games:
        response_text = "Nessuna partita in corso, usa /newgame per iniziarne una"
    else:
        game = gameHandler.games[chat_id]
        if game.state != GameState.WAITING:
            response_text = "La partita e' gia' iniziata"
        elif await game.addPlayer(user_id, username):
            response_text = f"@{username} si e' unito al gioco\nGiocatori: {len(game.players)}/10"
        else:
            response_text = f"@{username} non puoi unirti in questo momento. Inizia una chat privata con il bot e riprova."

    if from_button:
        await context.bot.send_message(chat_id, response_text)
    else:
        await update.message.reply_text(response_text)

async def quitGame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        username = query.from_user.username or query.from_user.first_name
    else:
        return  

    if chat_id not in gameHandler.games:
        response_text = "Nessuna partita in corso, usa /newgame per iniziarne una"
    else:
        game = gameHandler.games[chat_id]
        if game.state != GameState.WAITING:
            response_text = "La partita e' gia' iniziata"
        elif game.removePlayer(user_id):
            response_text = f"@{username} ha lasciato la partita\nGiocatori: {len(game.players)}/10"
        else:
            response_text = "Non puoi uscire dalla partita"

    if update.message:
        await update.message.reply_text(response_text)
    elif update.callback_query:
        await context.bot.send_message(chat_id, response_text)

async def forceStartGame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    print(f"Force start requested for chat {chat_id}")
    
    if chat_id not in gameHandler.games:
        print(f"No game found for chat {chat_id}")
        await update.message.reply_text("Nessuna partita in corso, usa /newgame per iniziarne una")
        return
        
    game = gameHandler.games[chat_id]
    print(f"Game state: {game.state}, Players: {len(game.players)}")
    
    if game.state != GameState.WAITING:
        print(f"Game already started, state: {game.state}")
        await update.message.reply_text("La partita e' gia' iniziata")
        return
        
    if len(game.players) < config.MIN_GIOCATORI:
        print(f"Not enough players: {len(game.players)}/{config.MIN_GIOCATORI}")
        await update.message.reply_text(f"Non ci sono abbastanza giocatori per iniziare, minimo {config.MIN_GIOCATORI} giocatori richiesti.")
        return

    print("Attempting to start game...")
    if await game.startGame():
        print("Game started successfully")

        if hasattr(game, "join_message_id"):
            try:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=game.join_message_id,
                    text="La partita e' iniziata!",
                )
            except Exception as e:
                print(f"Errore nella modifica del messaggio di partecipazione: {e}")
    else:
        print("Failed to start game")
        await update.message.reply_text("Impossibile avviare la partita.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await joinGame(update, context, from_button=True)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    print(f"[DEBUG] Received callback data: {data}")

    chat_id = query.message.chat.id
    if chat_id in gameHandler.games:
        game = gameHandler.games[chat_id]
        if data.startswith("kill_"):
            if game.state == GameState.NIGHT:
                wolf_player = game.players.get(query.from_user.id)
                if wolf_player and wolf_player.role == Role.LUPO:
                    print(f"[DEBUG] Wolf {wolf_player.username} is making their choice")
                    await wolf_player.handleNightAction(update, context)
                    
                    if game.night_timer:
                        game.night_timer.schedule_removal()
                        game.night_timer = None
                    
                    print(f"[DEBUG] Wolf kill target set to: {game.wolf_kill}")
                    await asyncio.sleep(3) 
                    await game.dayPhase()
                else:
                    await query.answer("Non sei un lupo!", show_alert=True)
        elif data.startswith("see_"):
            if game.state == GameState.NIGHT:
                target_id = int(data.split("_")[1])
                game.night_actions['seer_vision'] = target_id
                await query.answer("Vision ricevuta")
                target = game.players.get(target_id)
                if target:
                    await query.edit_message_text(f"Hai scelto di controllare @{target.username}")
        elif data.startswith("vote_"):
            if game.state == GameState.VOTING:
                await game.handleVotes(update, context)
