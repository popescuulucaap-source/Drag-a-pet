import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from aiohttp import web
from discord import app_commands

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["DISCORD_TOKEN"]
API_KEY = os.environ["API_KEY"]
PORT = int(os.getenv("PORT", "8080"))
DATA_FILE = Path(os.getenv("DATA_FILE", "data/guilds.json"))
RARITIES = ("Basic", "Common", "Uncommon", "Rare", "Legendary", "Divine")
BEST_PET = "Sugar Dragon"

def load_data():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, indent=2), encoding="utf-8")
    tmp.replace(DATA_FILE)

config = load_data()
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

class SetupView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = str(guild_id)
        self.channel_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text], placeholder="Choose the spawn notification channel")
        self.channel_select.callback = self.choose_channel
        self.add_item(self.channel_select)
        self.role_select = discord.ui.RoleSelect(placeholder="Choose a role for this rarity (optional)")
        self.role_select.callback = self.choose_role
        self.add_item(self.role_select)
        self.rarity_select = discord.ui.Select(placeholder="Choose which rarity that role is for", options=[
            discord.SelectOption(label=r, value=r) for r in RARITIES])
        self.rarity_select.callback = self.choose_rarity
        self.add_item(self.rarity_select)
        self.selected_rarity = "Divine"

    async def choose_channel(self, interaction: discord.Interaction):
        g = config.setdefault(self.guild_id, {"roles": {}})
        g["channel_id"] = self.channel_select.values[0].id
        save_data()
        await interaction.response.send_message(f"Notifications will go to {self.channel_select.values[0].mention}.", ephemeral=True)

    async def choose_rarity(self, interaction: discord.Interaction):
        self.selected_rarity = self.rarity_select.values[0]
        await interaction.response.send_message(f"Selected **{self.selected_rarity}**. Now choose its role below.", ephemeral=True)

    async def choose_role(self, interaction: discord.Interaction):
        g = config.setdefault(self.guild_id, {"roles": {}})
        role = self.role_select.values[0]
        g.setdefault("roles", {})[self.selected_rarity] = role.id
        save_data()
        await interaction.response.send_message(f"{self.selected_rarity} notifications will ping {role.mention}.", ephemeral=True)

@tree.command(name="setup", description="Choose the channel and rarity roles for pet spawn alerts")
@app_commands.checks.has_permissions(manage_guild=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Choose a notification channel, then choose a rarity and its role. You can repeat the role selection to configure each rarity.",
        view=SetupView(interaction.guild_id), ephemeral=True)

@tree.command(name="help", description="Explain Drag a Pet notifications")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**Drag a Pet alerts**\n`/setup` lets a server manager select the alert channel and configure roles by rarity. "
        "The game server reports newly spawned pets to this bot. When Sugar Dragon spawns, the bot posts **THE BEST PET SPAWNED** and pings @everyone.",
        ephemeral=True)

@tree.error
async def command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = "Only a server manager can configure the bot." if isinstance(error, app_commands.MissingPermissions) else "That command failed; please try again."
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)

async def handle_spawn(request: web.Request):
    if request.headers.get("Authorization") != f"Bearer {API_KEY}":
        raise web.HTTPUnauthorized()
    try:
        body = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text="Expected JSON")
    pet = str(body.get("pet", ""))
    rarity = str(body.get("rarity", ""))
    if not pet or rarity not in RARITIES:
        raise web.HTTPBadRequest(text="Provide pet and valid rarity")
    day_key = str(body.get("dayKey", ""))[:64]
    sent = 0
    for gid, settings in config.items():
        channel = bot.get_channel(settings.get("channel_id"))
        if channel is None:
            continue
        role_id = settings.get("roles", {}).get(rarity)
        mention = f"<@&{role_id}> " if role_id else ""
        best = pet.casefold() == BEST_PET.casefold()
        text = ("@everyone **THE BEST PET SPAWNED** — Sugar Dragon!" if best else f"{mention}A **{rarity}** pet spawned: **{pet}**")
        allowed = discord.AllowedMentions(everyone=best, roles=not best)
        try:
            await channel.send(text, allowed_mentions=allowed)
            sent += 1
        except discord.HTTPException:
            logging.exception("Failed to send spawn alert to guild %s", gid)
    return web.json_response({"ok": True, "sent": sent, "dayKey": day_key})

async def start_http():
    app = web.Application()
    app.router.add_post("/spawn", handle_spawn)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()

@bot.event
async def on_ready():
    await tree.sync()
    logging.info("Logged in as %s", bot.user)

async def main():
    await start_http()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
