import config
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from classes.player import Player
from classes.enums import Role

class Veggente(Player):
    def __init__(self, user_id, username, game):
        super().__init__(user_id, username, Role.VEGGENTE, game)

    def revealRole(self, target):
        return f"{self.username} vede che @{target.username} e' un {target.role}"

    async def nightAction(self, bot, context: ContextTypes.DEFAULT_TYPE):
        buttons = [
            [InlineKeyboardButton(player.username, callback_data=f"see_{pid}")]
            for pid, player in self.game.players.items() if pid != self.user_id and pid in self.game.playersAlive
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await bot.send_message(
            self.user_id,
            "Scegli un giocatore da controllare per scoprire il suo ruolo:",
            reply_markup=reply_markup
        )

    async def handleNightAction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        try:
            action, target_id_str = query.data.split('_', 1)
        except ValueError:
            await query.edit_message_text("Dati non validi.")
            return

        target_id = int(target_id_str)
        target = self.game.players.get(target_id)
        self.game.seer_vision[self.user_id] = target_id  
        await query.edit_message_text(f"Hai scelto di osservare @{target.username}. Scoprirai il suo ruolo domani mattina.")
