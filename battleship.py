import discord
from discord.ext import commands
import random
import os
from keep_alive import keep_alive

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
intents.message_content = True  # Enable the message_content intent
bot = commands.Bot(command_prefix="bb ", intents=intents)

# Game state for each user
game_states = {}

# Initialize game state for a user
def initialize_game_state(user_id):
    game_states[user_id] = {
        "player_grid": create_grid(),
        "bot_grid": create_grid(),
        "bot_display_grid": create_grid(),
        "bot_attack_history": set(),
        "player_attack_history": set(),
        "turn": None,
        "game_active": False,
        "placing_ships": False,
        "ships_to_place": {
            'Destroyer': 2,
            'Submarine': 3,
            'Frigate': 3,
            'Battleship': 4,
            'Carrier': 5
        },
        "current_ship": None
    }

# Helper function to display both grids
async def display_grids(ctx, user_id):
    player_str = "Your Grid:\n```" + format_grid(game_states[user_id]["player_grid"]) + "```"
    bot_str = "Bot Grid:\n```" + format_grid(game_states[user_id]["bot_display_grid"]) + "```"
    await ctx.send(player_str)
    await ctx.send(bot_str)

# Help command
@bot.command(name="!help")
async def help_command(ctx):
    help_message = """
**Battleship Bot Commands:**
- bb !help: Display game rules and commands.
- bb !start: Start a new game.
- bb !place <ship> <orientation> <coordinate>: Place a ship (e.g., bb !place Destroyer H A0).
- bb !shoot <coordinate>: Shoot at a coordinate (e.g., bb !shoot A0).
- bb !surrender: Surrender the current game.
    """
    await ctx.send(help_message)

# Start command
@bot.command(name="!start")
async def start_game(ctx):
    user_id = ctx.author.id

    if user_id in game_states and game_states[user_id]["game_active"]:
        await ctx.send("A game is already in progress! Use bb !surrender to end it.")
        return

    # Initialize game state for the user
    initialize_game_state(user_id)

    # Place bot's ships
    place_bot_ships(game_states[user_id]["bot_grid"])

    # Display the empty player grid (bot grid remains hidden)
    await ctx.send("Game started! Here is your empty grid:")
    await ctx.send("```" + format_grid(game_states[user_id]["player_grid"]) + "```")
    await ctx.send("Place your ships using the bb !place <ship> <orientation> <coordinate> command.")
    await ctx.send("Example: bb !place Destroyer H A0 (or bb !place d H A0).")
    await ctx.send("Available ships: Destroyer (2), Submarine (3), Frigate (3), Battleship (4), Carrier (5).")

    # Set game state
    game_states[user_id]["game_active"] = True
    game_states[user_id]["placing_ships"] = True

# Place command
@bot.command(name="!place")
async def place_ship_command(ctx, ship: str, orientation: str, coord: str):
    user_id = ctx.author.id

    if user_id not in game_states or not game_states[user_id]["game_active"] or not game_states[user_id]["placing_ships"]:
        await ctx.send("You can only place ships at the start of the game.")
        return

    # Map first letters to full ship names
    ship_map = {
        'd': 'Destroyer',
        's': 'Submarine',
        'f': 'Frigate',
        'b': 'Battleship',
        'c': 'Carrier'
    }

    # Convert first letter to full ship name if necessary
    if len(ship) == 1 and ship.lower() in ship_map:
        ship = ship_map[ship.lower()]
    else:
        ship = ship.capitalize()

    orientation = orientation.upper()

    if ship not in game_states[user_id]["ships_to_place"]:
        await ctx.send(f"Invalid ship. Available ships: {', '.join(game_states[user_id]['ships_to_place'].keys())}.")
        return

    if orientation not in ['H', 'V']:
        await ctx.send("Invalid orientation. Use 'H' for horizontal or 'V' for vertical.")
        return

    try:
        row, col = convert_coordinates(coord)
        size = game_states[user_id]["ships_to_place"][ship]
        if can_place_ship(game_states[user_id]["player_grid"], row, col, size, orientation):
            place_ship(game_states[user_id]["player_grid"], row, col, size, orientation, ship[0])
            del game_states[user_id]["ships_to_place"][ship]  # Remove the ship from the list
            await ctx.send(f"{ship} placed successfully!")
            # Display player's grid after each placement
            await ctx.send("Your Grid:\n```" + format_grid(game_states[user_id]["player_grid"]) + "```")
        else:
            await ctx.send("Invalid placement. Ship overlaps or goes out of bounds.")
            return
    except (ValueError, IndexError):
        await ctx.send("Invalid coordinate. Please try again.")
        return

    # Check if all ships are placed
    if not game_states[user_id]["ships_to_place"]:
        game_states[user_id]["placing_ships"] = False
        await ctx.send("All ships placed! The game will now begin.")
        # Display both grids (the bot grid will be hidden)
        await display_grids(ctx, user_id)
        # Coin toss to decide who goes first
        game_states[user_id]["turn"] = random.choice(['player', 'bot'])
        await ctx.send(f"Coin toss result: {game_states[user_id]['turn'].capitalize()} goes first!")
        if game_states[user_id]["turn"] == 'bot':
            await bot_turn(ctx, user_id)

# Shoot command
@bot.command(name="!shoot")
async def shoot(ctx, coord: str):
    user_id = ctx.author.id

    if user_id not in game_states or not game_states[user_id]["game_active"]:
        await ctx.send("No game in progress. Use bb !start to start a new game.")
        return

    if game_states[user_id]["placing_ships"]:
        await ctx.send("You must place all your ships first!")
        return

    if game_states[user_id]["turn"] != 'player':
        await ctx.send("It's not your turn!")
        return

    try:
        row, col = convert_coordinates(coord)
        if (row, col) in game_states[user_id]["player_attack_history"]:
            await ctx.send("You've already attacked this coordinate. Try again.")
            return
        game_states[user_id]["player_attack_history"].add((row, col))
    except (ValueError, IndexError):
        await ctx.send("Invalid coordinate. Please try again.")
        return

    # Check if the attack hits
    if game_states[user_id]["bot_grid"][row][col] != '-':
        await ctx.send("Hit!")
        game_states[user_id]["bot_display_grid"][row][col] = 'X'  # Update bot's display grid
        # Mark hit on bot's actual grid
        hit_symbol = game_states[user_id]["bot_grid"][row][col]
        game_states[user_id]["bot_grid"][row][col] = 'X'
        if is_ship_sunk(game_states[user_id]["bot_grid"], hit_symbol):
            await ctx.send(f"You sunk the bot's {hit_symbol}!")
    else:
        await ctx.send("Miss!")
        game_states[user_id]["bot_display_grid"][row][col] = '?'  # Update bot's display grid

    # Redisplay both grids after player's turn
    await display_grids(ctx, user_id)

    # Check if all bot ships are sunk
    if all(is_ship_sunk(game_states[user_id]["bot_grid"], ship[0]) for ship in ['Destroyer', 'Submarine', 'Frigate', 'Battleship', 'Carrier']):
        await ctx.send("Congratulations! You sunk all the bot's ships!")
        game_states[user_id]["game_active"] = False
        return

    # Switch turns to bot
    game_states[user_id]["turn"] = 'bot'
    await bot_turn(ctx, user_id)

# Bot's turn
async def bot_turn(ctx, user_id):
    row, col = bot_attack(game_states[user_id]["player_grid"], game_states[user_id]["bot_attack_history"])
    game_states[user_id]["bot_attack_history"].add((row, col))
    await ctx.send(f"Bot attacks: {rows[row]}{col}")

    # Check if the attack hits
    if game_states[user_id]["player_grid"][row][col] != '-':
        await ctx.send("Hit!")
        hit_symbol = game_states[user_id]["player_grid"][row][col]
        game_states[user_id]["player_grid"][row][col] = 'X'
        if is_ship_sunk(game_states[user_id]["player_grid"], hit_symbol):
            await ctx.send(f"You lost your {hit_symbol}!")
    else:
        await ctx.send("Miss!")
        game_states[user_id]["player_grid"][row][col] = '?'

    # Redisplay both grids after bot's turn
    await display_grids(ctx, user_id)

    # Check if all player ships are sunk
    if all(is_ship_sunk(game_states[user_id]["player_grid"], ship[0]) for ship in ['Destroyer', 'Submarine', 'Frigate', 'Battleship', 'Carrier']):
        await ctx.send("Oh no! The bot sunk all your ships!")
        game_states[user_id]["game_active"] = False
        return

    # Switch turns back to player
    game_states[user_id]["turn"] = 'player'
    await ctx.send("Your turn!")

# Surrender command
@bot.command(name="!surrender")
async def surrender(ctx):
    user_id = ctx.author.id

    if user_id not in game_states or not game_states[user_id]["game_active"]:
        await ctx.send("No game in progress.")
        return

    # Reset the game state for the user
    initialize_game_state(user_id)
    await ctx.send("You surrendered. Game over!")

# Run the bot
my_secret = os.environ['TOKEN']
keep_alive()
bot.run(my_secret)
