from enum import Enum

class GameState(Enum):
    WAITING = "Waiting"
    NIGHT = "Night"
    DISCUSSING = "Discussing"
    VOTING = "Voting"
    ENDED = "Ended"

class Role(Enum):
    VILLICO = "Villico"
    VEGGENTE = "Veggente"
    LUPO = "Lupo"

    def __str__(self): 
        return {
            Role.VILLICO: "🧑🌾 Paesano",
            Role.LUPO: "🐺 Lupo",
            Role.VEGGENTE: "🔮 Veggente"
        }[self]

