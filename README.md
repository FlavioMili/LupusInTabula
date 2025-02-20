# Lupus in Tabula Game

A Telegram bot version of the popular social deduction game **Lupus in Tabula** (also known as **Werewolf**). This project uses Python and the `python-telegram-bot` library to simulate the game where players take on different roles, including villagers, werewolves, and special characters (Currently only the seer is available). Players must deduce who the werewolves are before they eliminate all villagers.

## Project Structure

- `main.py`: Entry point of the bot, responsible for initializing the game and processing commands.
- `config.py`: Contains some messages or timers to be changed
- `handlers/`: Contains the logic for handling user commands such as starting a game, voting, etc.
- `classes/`: Contains game classes:
  - `Game`: Manages the game state, players, and logic.
  - `Player`: Represents each player and their role in the game.
    - `Roles classes`: Represent the role with their Night Actions
- `enum.py`: Defines game states and roles (e.g., Werewolf, Villager).

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/lupus-in-tabula.git
   cd lupus-in-tabula
   ```


2. Install dependencies:
   ```bash
    pip install -r requirements.txt
    ```

3. Set up your telegram bot3. 
- Create a bot on Telegram via BotFather.
- Add your bot token in the .env file (or directly in your code).
- Run the bot:

   ```bash
    python main.py
    ```

## How to Play

Start a Game: Users can start a new game by typing `/newgame`.

Join the Game: Players join by typing `/join`.

Game starts: after TEMPO_ATTESA_INIZIO seconds the last player who wrote `/join` or after someone wrote `/startgame` to force the start

Night Phase: All special roles can perform their night actions

Day Phase: After the night phase, players vote to eliminate a suspected werewolf using the buttons in private chat

Winning: The game ends when either all werewolves are eliminated (villagers win) or the werewolves eliminate enough villagers to take control (werewolves win).

## Features

Game Roles: Assigns players different roles including Werewolves, Villagers, Seer, and in future possibly more.

Multiple Phases: Night and Day phases with different actions.

Player Voting: Players vote to eliminate suspected werewolves during the Day phase.

## Possible Future Updates
- Adding new special roles
- Adding translations
- Adding settings in chat

