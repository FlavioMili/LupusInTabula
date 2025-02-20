from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from classes.enums import Role

class Player:
    def __init__(self, user_id, username, role, game=None):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.alive = True
        self.game = game

    def __str__(self):
        return f"{self.username} ({self.role})"

    def die(self):
        self.alive = False

    def sendRoleMessage(self, bot):
        raise NotImplementedError("sendRoleMessage must be implemented by subclasses.")

    def nightAction(self, bot):
        raise NotImplementedError("nightAction must be implemented by subclasses.")

    async def doVote(self, bot):
        buttons = [
            [InlineKeyboardButton(f"{self.game.players[pid].username}", callback_data=f"vote_{pid}")]
            for pid in self.game.playersAlive if pid != self.user_id
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        sent_msg = await bot.send_message(self.user_id, "Scegli chi eliminare:", reply_markup=reply_markup)
        self.vote_message_id = sent_msg.message_id

    async def handleVote(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        voter_id = query.from_user.id
        voted_id = int(query.data.split('_')[1])
        self.game.votes[voter_id] = voted_id
        await query.edit_message_text("Voto registrato!")
    

class Villico(Player):
    def __init__(self, user_id, username, game):
        super().__init__(user_id, username, Role.VILLICO, game)

    def sendRoleMessage(self, bot):
        bot.sendMessage( self.user_id, 
            "Sei un Villico, il tuo unico obbiettivo è sopravvivere e votare l'eliminazione dei lupi.")

    async def nightAction(self, bot, context: ContextTypes.DEFAULT_TYPE):
        await bot.sendMessage(self.user_id, "Questa notte vai a dormire tranquillo.")
        return None
