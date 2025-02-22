import discord
from discord.ext import commands
import random
import os

# Grid setup
xaxis = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

# Create an empty 10x10 grid
def create_grid():
    return [['-' for _ in range(10)] for _ in range(10)]

# Print the grid with row labels
def format_grid(grid):
    grid_str = "  " + " ".join(xaxis) + "\n"  # Column labels
    for i, row in enumerate(grid):
        grid_str += rows[i] + " " + " ".join(row) + "\n"  # Row label and row content
    return grid_str

# Convert coordinates like 'A0' to grid indices (row, col)
def convert_coordinates(coord):
    row = coord[0].upper()  # Get the row letter (e.g., 'A')
    col = int(coord[1:])    # Get the column number (e.g., '0')
    return (ord(row) - ord('A'), col)  # Convert row letter to index (0-9)

# Check if a ship can be placed at the given location
def can_place_ship(grid, start_row, start_col, size, orientation):
    if orientation == 'H':  # Horizontal
        if start_col + size > 10:
            return False  # Out of bounds
        for i in range(size):
            if grid[start_row][start_col + i] != '-':
                return False  # Overlapping another ship
    elif orientation == 'V':  # Vertical
        if start_row + size > 10:
            return False  # Out of bounds
        for i in range(size):
            if grid[start_row + i][start_col] != '-':
                return False  # Overlapping another ship
    return True

# Place a ship on the grid
def place_ship(grid, start_row, start_col, size, orientation, ship_symbol):
    if orientation == 'H':  # Horizontal
        for i in range(size):
            grid[start_row][start_col + i] = ship_symbol
    elif orientation == 'V':  # Vertical
        for i in range(size):
            grid[start_row + i][start_col] = ship_symbol

# Randomly place bot's ships
def place_bot_ships(grid):
    ships = {
        'Destroyer': 2,
        'Submarine': 3,
        'Frigate': 3,
        'Battleship': 4,
        'Carrier': 5
    }
    for ship, size in ships.items():
        while True:
            orientation = random.choice(['H', 'V'])
            start_row = random.randint(0, 9)
            start_col = random.randint(0, 9)
            if can_place_ship(grid, start_row, start_col, size, orientation):
                place_ship(grid, start_row, start_col, size, orientation, ship[0])
                break

# Check if a ship is sunk
def is_ship_sunk(grid, ship_symbol):
    for row in grid:
        if ship_symbol in row:
            return False
    return True

# Bot's attack logic
def bot_attack(player_grid, bot_attack_history):
    # If the bot has a recent hit, target nearby cells
    for row, col in bot_attack_history:
        if player_grid[row][col] == 'X':  # Last hit
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # Check adjacent cells
                r, c = row + dr, col + dc
                if 0 <= r < 10 and 0 <= c < 10 and (r, c) not in bot_attack_history:
                    return (r, c)
    # Otherwise, attack randomly
    while True:
        row = random.randint(0, 9)
        col = random.randint(0, 9)
        if (row, col) not in bot_attack_history:
            return (row, col)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="bb ", intents=intents)

# Game state
game_state = {
    "player_grid": None,
    "bot_grid": None,
    "bot_display_grid": None,
    "bot_attack_history": set(),
    "player_attack_history": set(),
    "turn": None,
    "game_active": False
}

# Help command
@bot.command(name="help")
async def help_command(ctx):
    help_message = """
**Battleship Bot Commands:**
- `bb help`: Display game rules and commands.
- `bb start`: Start a new game.
- `bb shoot <coordinate>`: Shoot at a coordinate (e.g., `bb shoot A0`).
- `bb surrender`: Surrender the current game.
    """
    await ctx.send(help_message)

# Start command
@bot.command(name="start")
async def start_game(ctx):
    if game_state["game_active"]:
        await ctx.send("A game is already in progress! Use `bb surrender` to end it.")
        return

    # Initialize grids
    game_state["player_grid"] = create_grid()
    game_state["bot_grid"] = create_grid()
    game_state["bot_display_grid"] = create_grid()
    game_state["bot_attack_history"] = set()
    game_state["player_attack_history"] = set()
    game_state["game_active"] = True

    # Place bot's ships
    place_bot_ships(game_state["bot_grid"])

    # Coin toss to decide who goes first
    game_state["turn"] = random.choice(['player', 'bot'])
    await ctx.send(f"Game started! {game_state['turn'].capitalize()} goes first!")

    if game_state["turn"] == 'bot':
        await bot_turn(ctx)

# Shoot command
@bot.command(name="shoot")
async def shoot(ctx, coord: str):
    if not game_state["game_active"]:
        await ctx.send("No game in progress. Use `bb start` to start a new game.")
        return

    if game_state["turn"] != 'player':
        await ctx.send("It's not your turn!")
        return

    try:
        row, col = convert_coordinates(coord)
        if (row, col) in game_state["player_attack_history"]:
            await ctx.send("You've already attacked this coordinate. Try again.")
            return
        game_state["player_attack_history"].add((row, col))
    except (ValueError, IndexError):
        await ctx.send("Invalid coordinate. Please try again.")
        return

    # Check if the attack hits
    if game_state["bot_grid"][row][col] != '-':
        await ctx.send("Hit!")
        game_state["bot_display_grid"][row][col] = 'X'  # Update bot's display grid
        game_state["bot_grid"][row][col] = 'X'  # Update bot's actual grid
        if is_ship_sunk(game_state["bot_grid"], game_state["bot_grid"][row][col]):
            await ctx.send(f"You sunk the bot's {game_state['bot_grid'][row][col]}!")
    else:
        await ctx.send("Miss!")
        game_state["bot_display_grid"][row][col] = '?'  # Update bot's display grid

    # Check if all bot ships are sunk
    if all(is_ship_sunk(game_state["bot_grid"], ship[0]) for ship in ['Destroyer', 'Submarine', 'Frigate', 'Battleship', 'Carrier']):
        await ctx.send("Congratulations! You sunk all the bot's ships!")
        game_state["game_active"] = False
        return

    # Switch turns
    game_state["turn"] = 'bot'
    await bot_turn(ctx)

# Bot's turn
async def bot_turn(ctx):
    row, col = bot_attack(game_state["player_grid"], game_state["bot_attack_history"])
    game_state["bot_attack_history"].add((row, col))
    await ctx.send(f"Bot attacks: {rows[row]}{col}")

    # Check if the attack hits
    if game_state["player_grid"][row][col] != '-':
        await ctx.send("Hit!")
        game_state["player_grid"][row][col] = 'X'
        if is_ship_sunk(game_state["player_grid"], game_state["player_grid"][row][col]):
            await ctx.send(f"You lost your {game_state['player_grid'][row][col]}!")
    else:
        await ctx.send("Miss!")
        game_state["player_grid"][row][col] = '?'

    # Check if all player ships are sunk
    if all(is_ship_sunk(game_state["player_grid"], ship[0]) for ship in ['Destroyer', 'Submarine', 'Frigate', 'Battleship', 'Carrier']):
        await ctx.send("Oh no! The bot sunk all your ships!")
        game_state["game_active"] = False
        return

    # Switch turns
    game_state["turn"] = 'player'
    await ctx.send("Your turn!")

# Surrender command
@bot.command(name="surrender")
async def surrender(ctx):
    if not game_state["game_active"]:
        await ctx.send("No game in progress.")
        return

    game_state["game_active"] = False
    await ctx.send("You surrendered. Game over!")

# Run the bot
bot.run("BOT_TOKEN")