import discord
import os
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from threading import Thread
from replit import db

prefix = "!lb"
WUAwaiting = False
last_message_ids = ()  # author, message


async def sendLeaderboard(title, db_key, message):
    data = dict(db[db_key])
    leaders = sorted(data.items(), key=lambda x: x[1], reverse=True)
    eb = discord.Embed(title=title, color=discord.Color.blue())
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
            name=f"{position}",
            value=f"<@{int(leaders[i][0])}> with {leaders[i][1]} wins", inline=False)
    await message.channel.send(embed=eb)


async def sendStreakHolders(message):
    data = convert_observed_dict_to_dict(db["streak"])
    lm_user = list(data["LM"].keys())[0]
    wu_user = list(data["WU"].keys())[0]
    lm_streak = data["LM"][str(lm_user)]
    wu_streak = data["WU"][str(wu_user)]
    eb = discord.Embed(title="Current Streak Holders", color=discord.Color.blue())
    eb.add_field(
        name="Waking Up Award",
        value=f"<@{int(wu_user)}> with {wu_streak}🔥",
        inline=False)
    eb.add_field(
        name="Last Message Of The Day",
        value=f"<@{int(lm_user)}> with {lm_streak}🔥",
        inline=False)
    await message.channel.send(embed=eb)


def convert_observed_dict_to_dict(data):
    if isinstance(data, dict):
        return {key: convert_observed_dict_to_dict(value) for key, value in data.items()}
    elif hasattr(data, 'value'):
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


def update_scheduler(scheduler):
    scheduler.start()


async def awardWin(award, db_key, winner_id, channel):
    data = dict(db[db_key])
    if str(winner_id) not in data:
        data[str(winner_id)] = 1
    else:
        data[str(winner_id)] += 1
    db[db_key] = data
    streak = update_streak(True, winner_id)
    winner = f"<@{winner_id}>"
    await channel.send(
        f"{winner} has now won the {award} Award {data[str(winner_id)]} times.     {streak}🔥")


async def find_LM_winner():
    global last_message_ids
    message_id = last_message_ids[1]
    user_id = last_message_ids[0]
    channel = client.get_channel(525730239800672257)  # g e n e r a l 525730239800672257
    message = await channel.fetch_message(message_id)
    await message.add_reaction("🏆")
    winner_id = user_id
    award = "Last Message Of The Day"
    await awardWin(award, "LMscores", winner_id, channel)


class MyClient(discord.Client):

    async def on_ready(self):
        print(f"Logged in as {client.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="#g-e-n-e-r-a-l"))
        scheduler = AsyncIOScheduler(timezone="Europe/London")
        scheduler.add_job(find_LM_winner, "cron", hour=0, minute=0, second=0)
        thread = Thread(target=update_scheduler(scheduler))
        thread.start()

    async def on_message(self, message):
        global WUAwaiting
        global last_message_ids
        if message.channel.id == 525730239800672257:  # 525730239800672257:
            last_message_ids = (message.author.id, message.id)
        if message.author.id == 696828737248952331:
            await message.add_reaction("❤️")
        if message.author == client.user:
            return
        if not WUAwaiting and message.author.id == 748488791471161405:  # WU bot id: 748488791471161405
            WUAwaiting = True
        if WUAwaiting and message.author.id != 748488791471161405 and message.channel.id == 525730239800672257:
            WUAwaiting = False
            await message.add_reaction("🏆")
            winner_id = message.author.id
            award = "Waking Up Early"
            await awardWin(award, "WUscores", winner_id, message.channel)
        if message.content.startswith(prefix):
            messageList = message.content.split()
            if len(messageList) == 1:
                await sendLeaderboard("Waking Up Early Award Leaderboard", "WUscores", message)
                await sendLeaderboard("Last Message Of The Day Leaderboard", "LMscores", message)
            elif len(messageList) == 2 and messageList[1] == "s":
                await sendStreakHolders(message)
            elif len(messageList) == 3:
                moderator_ids = [603142766805123082, 299216822647914499]
                if messageList[1] == "wu" or messageList[1] == "lm":
                    if message.author.id not in moderator_ids:
                        await message.channel.send("L")
                        return
                    winner = messageList[2]
                    winner_id = re.sub("[^0-9]", '', winner)
                    if messageList[1] == "wu":
                        award = "Waking Up Early"
                        db_key = "WUscores"
                    else:
                        award = "Last Message Of The Day"
                        db_key = "LMscores"
                    await awardWin(award, db_key, winner_id, message.channel)


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(os.getenv("TOKEN"))
