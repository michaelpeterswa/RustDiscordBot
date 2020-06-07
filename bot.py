# Michael Peters

import secrets
import discord
import asyncio
import requests

from discord.ext import commands, tasks

bot = commands.Bot(command_prefix="z-", description="zombieland")

DEBUG = True


def debugPrint(text, val):
    if val:
        print(text)


@bot.event
async def on_ready():
    print("We have logged in as {0.user}".format(bot))
    bot.loop.create_task(get_battlemetrics(secrets.server))


async def get_battlemetrics(server):
    while True:
        r = requests.get("https://api.battlemetrics.com/servers/%s" % server)
        json_data = r.json()
        current_players = json_data["data"]["attributes"]["players"]
        game_name = "%s/50 players online" % current_players
        offline_game_name = "server offline"

        if json_data["data"]["attributes"]["status"] == "online":
            debugPrint(game_name, DEBUG)
            await bot.change_presence(
                activity=discord.Game(name=game_name), status=discord.Status.dnd
            )
        else:
            debugPrint(offline_game_name, DEBUG)
            await bot.change_presence(
                activity=discord.Game(name=offline_game_name), status=discord.Status.dnd
            )
        await asyncio.sleep(60)


@bot.command(pass_context=True)
async def issue(ctx):
    channel = bot.get_channel(secrets.issue_channel_id)
    await channel.send("issue created by {}".format(ctx.message.author.mention))


bot.run(secrets.token)
