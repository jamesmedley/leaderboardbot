import discord
import os
import re
import requests
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from replit import db
import asyncio


prefix = "!lb"
wua_waiting = False
last_message_ids = ()  # author, message


async def sendStreakHolders(message, user_info):
    data = convert_observed_dict_to_dict(db["streak"])
    lm_user = list(data["LM"].keys())[0]
    wu_user = list(data["WU"].keys())[0]
    lm_streak = data["LM"][str(lm_user)]
    wu_streak = data["WU"][str(wu_user)]
    eb = discord.Embed(title="**Current Streak Holders**",
                       color=discord.Color.from_rgb(255, 88, 62),
                       url="https://en.wikipedia.org/wiki/Among_Us",
                       timestamp=datetime.datetime.utcnow())
    eb.add_field(
        name="**Waking Up Award**",
        value=f"<@{int(wu_user)}> with **{wu_streak}**🔥",
        inline=False)
    eb.add_field(
        name="**Last Message Of The Day**",
        value=f"<@{int(lm_user)}> with **{lm_streak}**🔥",
        inline=False)
    eb.set_footer(text=user_info[0], icon_url=user_info[1])
    eb.set_thumbnail(url=user_info[2])
    await message.channel.send(embed=eb)


def convert_observed_dict_to_dict(data):
    if isinstance(data, dict):
        return {key: convert_observed_dict_to_dict(value) for key, value in data.items()}
    elif hasattr(data, "value"):
        return convert_observed_dict_to_dict(data.value)
    else:
        return data


def update_streak(lm, winner_id):
    data = convert_observed_dict_to_dict(db["streak"])
    if lm:
        if list(data["LM"].keys())[0] == str(winner_id):
            data["LM"][str(winner_id)] += 1
        else:
            data["LM"] = {str(winner_id): 1}
    else:
        if list(data["WU"].keys())[0] == str(winner_id):
            data["WU"][str(winner_id)] += 1
        else:
            data["WU"] = {str(winner_id): 1}

    db["streak"] = data
    if lm:
        return data["LM"][str(winner_id)]
    else:
        return data["WU"][str(winner_id)]


def start_scheduler(scheduler):
    scheduler.start()


async def awardWin(award, db_key, winner_id, channel, lm):
    data = dict(db[db_key])
    if str(winner_id) not in data:
        data[str(winner_id)] = 1
    else:
        data[str(winner_id)] += 1
    db[db_key] = data
    streak = update_streak(lm, winner_id)
    winner = f"<@{winner_id}>"
    await channel.send(
        f"{winner} has now won the {award} Award **{data[str(winner_id)]}** times.     **{streak}**🔥")


async def find_LM_winner():
    global last_message_ids
    message_id = last_message_ids[1]
    user_id = last_message_ids[0]
    channel = client.get_channel(525730239800672257)  # g e n e r a l 525730239800672257
    message = await channel.fetch_message(message_id)
    await message.add_reaction("🏆")
    award = "Last Message Of The Day"
    await awardWin(award, "LMscores", user_id, channel, True)


def leaderboard_embed(title, db_key, user_info):
    data = dict(db[db_key])
    leaders = sorted(data.items(), key=lambda x: x[1], reverse=True)
    eb = discord.Embed(title=f"**{title}**",
                       color=discord.Color.from_rgb(255, 88, 62),
                       url="https://en.wikipedia.org/wiki/Among_Us",
                       timestamp=datetime.datetime.utcnow())
    for i in range(min(10, len(leaders))):
        position = str(int(i + 1))
        if position == "1":
            position = "1st 🥇"
        elif position == "2":
            position = "2nd 🥈"
        elif position == "3":
            position = "3rd 🥉"
        else:
            position = position + "th"
        eb.add_field(
            name=f"**{position}**",
            value=f"<@{int(leaders[i][0])}> with **{leaders[i][1]}** wins", inline=False)
    eb.set_footer(text=user_info[0], icon_url=user_info[1])
    eb.set_thumbnail(url=user_info[2])
    return eb


async def sendLeaderboard(title, db_key, message, user_info):
    eb = leaderboard_embed(title, db_key, user_info)
    options = [
        discord.SelectOption(label="Waking Up Early Award Leaderboard", value="1", emoji="🌇", default=True),
        discord.SelectOption(label="Last Message Of The Day Leaderboard", value="2", emoji="🌃", default=False)
    ]

    select = discord.ui.Select(
        placeholder="🌇 Waking Up Early Award Leaderboard 🌇",
        options=options,
        custom_id="select_menu",
    )

    view = discord.ui.View()
    view.add_item(select)

    await message.channel.send(embed=eb, view=view)


class MyClient(discord.Client):

    async def on_interaction(self, interaction):
        if isinstance(interaction, discord.Interaction) and interaction.data["custom_id"] == "select_menu":
            user_info = [await self.get_user_username(interaction.user.id),
                         await self.get_user_pfp(interaction.user.id),
                         await self.get_user_pfp(895026694757445694)]
            selected_option = interaction.data["values"][0]
            if selected_option == "1":
                embed = leaderboard_embed("🌇 Waking Up Early Award Leaderboard 🌇", "WUscores", user_info)
                placeholder = "🌇 Waking Up Early Award Leaderboard 🌇"
            elif selected_option == "2":
                embed = leaderboard_embed("🌃 Last Message Of The Day Leaderboard 🌃", "LMscores", user_info)
                placeholder = "🌃 Last Message Of The Day Leaderboard 🌃"
            else:
                embed = leaderboard_embed("🌇 Waking Up Early Award Leaderboard 🌇", "WUscores", user_info)
                placeholder = "🌇 Waking Up Early Award Leaderboard 🌇"

            select = discord.ui.Select(
                placeholder=placeholder,
                options=[
                    discord.SelectOption(label="Waking Up Early Award Leaderboard", value="1", emoji="🌇",
                                         default=selected_option == "1"),
                    discord.SelectOption(label="Last Message Of The Day Leaderboard", value="2", emoji="🌃",
                                         default=selected_option == "2")
                ],
                custom_id="select_menu",
            )

            view = discord.ui.View()
            view.add_item(select)

            await interaction.response.edit_message(embed=embed, view=view)

    async def get_user_pfp(self, user_id):
        user = await self.fetch_user(user_id)
        pfp_url = str(user.avatar)
        return pfp_url

    async def get_user_username(self, user_id):
        user = await self.fetch_user(user_id)
        username = f"{user.name}#{user.discriminator}"
        return username

    async def on_ready(self):
        print(f"Logged in as {client.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="#g-e-n-e-r-a-l"))
        scheduler = AsyncIOScheduler(timezone="Europe/London")
        scheduler.add_job(find_LM_winner, "cron", hour=1, minute=5, second=15)
        loop = asyncio.get_running_loop()
        loop.call_soon(start_scheduler, scheduler)
        return

    async def on_message(self, message):
        global wua_waiting
        global last_message_ids
        if message.channel.id == 525730239800672257:  # 525730239800672257:
            last_message_ids = (message.author.id, message.id)
        if message.author.id == 696828737248952331:
            await message.add_reaction("❤️")
        if message.author == client.user:
            return
        if not wua_waiting and message.author.id == 748488791471161405:  # WU bot id: 748488791471161405
            wua_waiting = True
        if wua_waiting and message.author.id != 748488791471161405 and message.channel.id == 525730239800672257:
            wua_waiting = False
            await message.add_reaction("🏆")
            winner_id = message.author.id
            award = "Waking Up Early"
            await awardWin(award, "WUscores", winner_id, message.channel, False)
        if message.content.startswith(prefix):
            user_info = [await self.get_user_username(message.author.id), await self.get_user_pfp(message.author.id),
                         await self.get_user_pfp(895026694757445694)]
            messageList = message.content.split()
            if len(messageList) == 1:
                await sendLeaderboard("🌇 Waking Up Early Award Leaderboard 🌇", "WUscores", message, user_info)
            elif len(messageList) == 2 and messageList[1] == "s":
                await sendStreakHolders(message, user_info)
            elif len(messageList) == 3:
                moderator_ids = [603142766805123082, 299216822647914499]
                if messageList[1] == "wu" or messageList[1] == "lm":
                    if message.author.id not in moderator_ids:
                        api_key = os.getenv("GIPHY")
                        response = requests.get(f"https://api.giphy.com/v1/gifs/random?api_key={api_key}&tag=clown")
                        if response.status_code == 200:
                            data = response.json()
                            if "data" in data and "url" in data["data"]:
                                gif_url = data["data"]["url"]
                                await message.channel.send(gif_url)
                            else:
                                await message.channel.send("dont be naughty!")
                        else:
                            await message.channel.send("dont be naughty!")
                        return
                    winner = messageList[2]
                    winner_id = re.sub("[^0-9]", "", winner)
                    if len(str(winner_id)) != 18:
                        await message.channel.send(f"Invalid User ID: {winner}")
                        return
                    if messageList[1] == "wu":
                        award = "Waking Up Early"
                        db_key = "WUscores"
                        lm = False
                    else:
                        award = "Last Message Of The Day"
                        db_key = "LMscores"
                        lm = True
                    await awardWin(award, db_key, winner_id, message.channel, lm)


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(os.getenv("TOKEN"))
