from collections import Counter
from classes.enums import GameState, Role
from classes.lupo import Lupo
from classes.veggente import Veggente
from classes.player import Villico
import random
import config
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import Forbidden

class Game:
    def __init__(self, chat_id, application, game_handler):
        self.application = application
        self.game_handler = game_handler
        self.application.add_handler(CallbackQueryHandler(self.handleNightCallback, pattern="^(kill|see)_"))
        self.application.add_handler(CallbackQueryHandler(self.handleVotes, pattern="^vote_"))
        self.job_queue = application.job_queue
        self.chat_id = chat_id
        self.players = {}
        self.playersAlive = []
        self.votes = {}
        self.wolf_kills = []
        self.seer_vision = {}
        self.state = GameState.WAITING
        self.join_message = None  

    async def addPlayer(self, user_id, username):
        try:
            if user_id not in self.players.keys():
                await self.application.bot.send_message(user_id, "Benvenuto nel gioco! Preparati per iniziare.")
        except Forbidden:
            print(f"Impossibile inviare messaggio privato a {user_id}, rimuovendo dal gioco.")
            return False

        if len(self.players) < 10 and user_id not in self.players:
            self.players[user_id] = {'username': username, 'role': None}
            print(f"{username} entra in partita, partecipanti: {len(self.players)}")
            if len(self.players) >= config.MIN_GIOCATORI and self.state == GameState.WAITING:
                self.startTimer(self.startGame, config.TEMPO_ATTESA_INIZIO)
                # print(f"Timer avviato, {config.TEMPO_ATTESA_INIZIO} secondi da ora")
            return True
        return False

    async def removePlayer(self, user_id):
        if user_id in self.players:
            del self.players[user_id]
            self.playersAlive = [p for p in self.playersAlive if p != user_id]
            return True
        return False

    async def assignRoles(self):
        players_ids = list(self.players.keys())
        num_players = len(players_ids)
        numLupi = max(1, num_players // 4)
        numVeggenti = 1 if num_players >= 5 else 0  

        roles = ([Role.LUPO] * numLupi +
                 [Role.VEGGENTE] * numVeggenti +
                 [Role.VILLICO] * (num_players - numLupi - numVeggenti))
        random.shuffle(players_ids)
        random.shuffle(roles)

        wolf_ids = []
        
        for uid, role in zip(players_ids, roles):
            username = self.players[uid]['username']
            if role == Role.LUPO:
                self.players[uid] = Lupo(uid, username, self)
                wolf_ids.append(uid)
            elif role == Role.VEGGENTE:
                self.players[uid] = Veggente(uid, username, self)
            else:
                self.players[uid] = Villico(uid, username, self)

        for uid, player in self.players.items():
            try:
                if uid in wolf_ids:
                    wolf_usernames = [f"@{self.players[wid].username}" for wid in wolf_ids if wid != uid]
                    if wolf_usernames:
                        wolf_message = f"Sei un {player.role}! Ogni notte scegliete un bersaglio da eliminare."
                        wolf_message += "\nI tuoi compagni lupi sono:\n" + "\n".join(wolf_usernames)
                    else:
                        wolf_message = f"Sei un {player.role}!"
                    await self.application.bot.send_message(uid, wolf_message)
                else:
                    await self.application.bot.send_message(uid, f"Sei un {player.role}")
            except Forbidden:
                self.removePlayer(uid)

    async def startGame(self, context=None):
        if self.state == GameState.WAITING and len(self.players) >= config.MIN_GIOCATORI:
            await self.assignRoles()
            self.playersAlive = set(self.players.keys())
            self.state = GameState.NIGHT
            await self.sendMessage(config.MSG_GIOCO_INIZIATO)
            await self.nightPhase()
            return True
        else:
            print(f"Errore Stato: {self.state}, Giocatori: {len(self.players)}")
            return False

    # Usato per debugging nel caso in cui un giocatore blocchi il bot
    async def sendMessage(self, text):
        try:
            await self.application.bot.send_message(self.chat_id, text)
        except Forbidden:
            print(f"Impossibile inviare messaggio a {self.chat_id} - Bot bloccato.")

    async def nightPhase(self):
        self.state = GameState.NIGHT
        await self.sendMessage(config.MSG_NOTTE)
        for uid in self.playersAlive:
            player = self.players[uid]
            try:
                await player.nightAction(self.application.bot, None)
            except NotImplementedError:
                await self.application.bot.send_message(uid, "Questa notte vai a dormire tranquillo.")
                print(f"ruolo {player.role} non implemetato")

        self.startTimer(self.dayPhase, config.TEMPO_NOTTE)

    async def handleNightCallback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        # Check per giocatori che hanno una chat precedente a questa con bottoni
        if user_id not in self.players: 
            await query.answer("Non sei un giocatore attivo.", show_alert=True)
            return
        player = self.players[user_id]
        await player.handleNightAction(update, context)

    async def dayPhase(self):
        self.state = GameState.DISCUSSING

        # Night actions
        if self.wolf_kills:
            counter = Counter(self.wolf_kills)
            sorted_victims = sorted(counter.items(), key=lambda x: x[1], reverse=True)
            victim_id, _ = sorted_victims[0]  
            await self.eliminatePlayer(victim_id)
            victim = self.players.get(victim_id)
            await self.sendMessage(f"@{victim.username} e' stato mangiato dai lupi! Era un {victim.role}.")
        else:
            await self.sendMessage("Questa notte i lupi sono rimasti a digiuno.")

        for seer_id, target_id in self.seer_vision.items():
            seer = self.players.get(seer_id)
            target = self.players.get(target_id)
            if seer and target:
                if seer.user_id not in self.playersAlive:
                    await self.application.bot.send_message(seer.user_id, f"Sei stato eliminato prima di poter vedere il ruolo di @{target.username}")
                else:
                    await self.application.bot.send_message(seer.user_id, f"Hai avuto una visione: @{target.username} e' un {target.role}.")
        self.seer_vision.clear()

        if self.checkGameOver():
            await self.endGame()
        else:
            await self.sendMessage("E' arrivato il mattino, discutete chi cacciare")
            self.startTimer(self.votingPhase, config.TEMPO_DISCUSSIONE)

    async def votingPhase(self):
        print("Voting Phase started")
        self.state = GameState.VOTING
        self.votes = {}  

        for player_id in self.playersAlive:
            await self.players[player_id].doVote(self.application.bot)
        self.startTimer(self.endVotingPhase, config.TEMPO_VOTAZIONE)

    async def endVotingPhase(self, context=None):
        print("Voting Phase ended")
        for player_id in self.playersAlive:
            if player_id not in self.votes:
                player = self.players[player_id]
                if hasattr(player, 'vote_message_id'):
                    try:
                        await self.application.bot.edit_message_text(
                            "Non hai fatto in tempo a votare",
                            chat_id=player.user_id,
                            message_id=player.vote_message_id
                        )
                    except Exception as e:
                        print(f"Error editing vote message for {player.user_id}: {e}")
        
        if not self.votes:
            await self.sendMessage("Nessun voto espresso. Nessuno viene eliminato.")
            await self.nightPhase()
            return
        vote_counts = {}
        for voted_id in self.votes.values():
            vote_counts[voted_id] = vote_counts.get(voted_id, 0) + 1

        most_voted = max(vote_counts, key=vote_counts.get)
        max_votes = vote_counts[most_voted]
        tied_players = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        if len(tied_players) > 1:
            await self.sendMessage("Pareggio nei voti. Nessuno viene eliminato.")
        else:
            victim = self.players.get(most_voted)
            if victim:
                await self.eliminatePlayer(most_voted)
                await self.sendMessage(f"@{victim.username} e' stato eliminato per decisione del villaggio! Era un {victim.role}")

        if self.checkGameOver():
            await self.endGame()
        else:
            await self.nightPhase()

    async def handleVotes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        voter_id = query.from_user.id
        voted_id = int(query.data.split('_')[1])

        if voter_id in self.playersAlive and voted_id in self.playersAlive:
            self.votes[voter_id] = voted_id
            await query.answer("Voto registrato!")

            voter = self.players[voter_id]
            voted = self.players[voted_id]

            await query.edit_message_text(f"Hai votato per @{voted.username}.")
            vote_message = f"@{voter.username} ha votato per eliminare @{voted.username}!"
            await self.application.bot.send_message(self.chat_id, vote_message)
        else:
            await query.answer("Voto non valido!", show_alert=True)


    async def eliminatePlayer(self, player_id):
        print(f"Eliminating player: {player_id}")  
        if player_id in self.players:
            player = self.players[player_id]
            player.die()
            self.playersAlive.remove(player_id)
            print(f"Player {player_id} eliminated successfully.")
            # await self.application.bot.send_message(self.chat_id, f"@{player.username} e' stato eliminato dal gioco.")
            try:
                await self.application.bot.send_message(player_id, "Sei stato eliminato dal gioco.")
            except Exception as e:
                print(f"Error sending private message to {player_id}: {e}")
        else:
            print(f"Error: Player {player_id} not found.")

    def checkGameOver(self):
        wolves_count = sum(1 for pid in self.playersAlive if self.players[pid].role == Role.LUPO)
        villagers_count = len(self.playersAlive) - wolves_count
        return wolves_count == 0 or wolves_count >= villagers_count

    async def endGame(self):
        if any(player.role == Role.LUPO for player in self.players.values() if player.user_id in self.playersAlive):
            await self.application.bot.send_message(self.chat_id, "I lupi hanno vinto!")
        else:
            await self.application.bot.send_message(self.chat_id, "I paesani hanno vinto!")
        if self.chat_id in self.game_handler.games:
            del self.game_handler.games[self.chat_id]

        await self.application.bot.send_message(self.chat_id, "Il gioco e' terminato. Puoi iniziare una nuova partita!")

    def startTimer(self, func, duration):
        async def wrapper(context: ContextTypes.DEFAULT_TYPE):
            await func()
        return self.job_queue.run_once(wrapper, duration)
