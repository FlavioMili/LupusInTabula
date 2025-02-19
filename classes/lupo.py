import config
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from classes.player import Player
from classes.enums import Role

class Lupo(Player):
    def __init__(self, user_id, username, game):
        super().__init__(user_id, username, Role.LUPO, game)

    async def nightAction(self, bot, context: ContextTypes.DEFAULT_TYPE):
        targets = [
            player for player in self.game.players.values() 
            if player.user_id != self.user_id and player.role != Role.LUPO and player.user_id in self.game.playersAlive
        ]
        if not targets:
            await bot.send_message(self.user_id, "Non ci sono bersagli validi per attaccare.")
            return None

        keyboard = [
            [InlineKeyboardButton(target.username, callback_data=f"kill_{target.user_id}")]
            for target in targets
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await bot.send_message(
            self.user_id, 
            "Scegli un giocatore da eliminare:", 
            reply_markup=reply_markup
        )

    async def handleNightAction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        try:
            action, target_id_str = query.data.split('_', 1)
            target_id = int(target_id_str)
        except (ValueError, IndexError):
            await query.edit_message_text("Dati non validi.")
            return

        target = self.game.players.get(target_id)
        if not target or target_id not in self.game.playersAlive:
            await query.edit_message_text("Giocatore non valido o già eliminato.")
            return

        await query.edit_message_text(text=f"Hai scelto il giocatore: @{target.username}")
        if target_id not in self.game.wolf_kills:
            self.game.wolf_kills.append(target_id)
        print(f"[DEBUG] Wolf {self.user_id} set kill target to {target_id}")
