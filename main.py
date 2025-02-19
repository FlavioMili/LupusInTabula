import logging
import os
from dotenv import load_dotenv
import config
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from handlers.commandsHandler import ( newGame, joinGame, quitGame, 
    button, forceStartGame)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Il token del bot non si trova nel file .env")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("newgame", newGame))
    application.add_handler(CommandHandler("join", joinGame))
    application.add_handler(CommandHandler("quit", quitGame))
    application.add_handler(CommandHandler("startgame", forceStartGame))
    application.add_handler(CallbackQueryHandler(button, pattern="^join$"))

    logger.info("Bot avviato con successo")
    application.run_polling()

if __name__ == '__main__':
    main()
