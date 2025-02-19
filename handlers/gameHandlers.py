from telegram import Update
from classes.enums import GameState
from classes.game import Game
from classes.player import Villico
from classes.veggente import Veggente
from classes.lupo import Lupo

class GameHandler:
    def __init__(self):
        self.games = {}
    
    def newGame(self, chat_id, application):
        self.games[chat_id] = Game(chat_id, application)

    def getGame(self, chat_id):
        return self.games.get(chat_id, None) 

    async def startGame(self, chat_id):  
        game = self.getGame(chat_id)
        if game: 
            if await game.startGame():  
                return True
        return False

    async def addPlayer(self, chat_id, user_id, username):  
        game = self.getGame(chat_id)
        if game: 
            if await game.addPlayer(user_id, username): 
                return True
        return False

    async def removePlayer(self, chat_id, user_id):  
        game = self.getGame(chat_id)
        if game:
            if await game.removePlayer(user_id):
                return True
        return False
