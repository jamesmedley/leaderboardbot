import discord
import json
import os
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from threading import Thread

prefix = "!lb"
WUAwaiting = False
last_message_ids = ()  # author, message


class MyClient(discord.Client):

    async def find_LM_winner(self):
        global last_message_ids
        message_id = last_message_ids[1]
        user_id = last_message_ids[0]
        channel = client.get_channel(525730239800672257)  # g e n e r a l 525730239800672257
        message = await channel.fetch_message(message_id)
        await message.add_reaction("🏆")
        winner_id = user_id
        winner = f"<@{winner_id}>"
        with open("LMscores.json", "r") as f:
            data = json.load(f)
            if str(winner_id) not in data:
                data[str(winner_id)] = 1
            else:
                data[str(winner_id)] += 1
        f.close()
        streak = self.update_streak(True, winner_id)
        await channel.send(
            f"{winner} has now won the Last Message Of The Day Award {data[str(winner_id)]} times.     {streak}🔥")
        with open("LMscores.json", "w") as f:
            json.dump(data, f, indent=0)
        f.close()

    async def on_ready(self):
        print(f"Logged in as {client.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="#g-e-n-e-r-a-l"))
        scheduler = AsyncIOScheduler(timezone="Europe/London")
        scheduler.add_job(self.find_LM_winner, 'cron', hour=0, minute=0, second=0)
        thread = Thread(target=self.updatescheduler(scheduler))
        thread.start()

    def updatescheduler(self, scheduler):
        scheduler.start()

    def update_streak(self, lm, winner_id):
        with open("streak.json", "r") as f:
            data = json.load(f)
        f.close()
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

        with open("streak.json", "w") as f:
            json.dump(data, f, indent=0)
        f.close()
        if lm:
            return data["LM"][str(winner_id)]
        else:
            return data["WU"][str(winner_id)]

    async def on_message(self, message):
        global WUAwaiting
        global last_message_ids
        if message.channel.id == 525730239800672257:  # 525730239800672257:
            last_message_ids = (message.author.id, message.id)

        if message.author.id == 696828737248952331:
            await message.add_reaction("❤️")

        if message.author == client.user:
            return

        if WUAwaiting == False and message.author.id == 748488791471161405:  # WU bot id: 748488791471161405
            WUAwaiting = True

        if WUAwaiting == True and message.author.id != 748488791471161405 and message.channel.id == 525730239800672257:
            WUAwaiting = False
            await message.add_reaction("🏆")
            winner_id = message.author.id
            winner = f"<@{winner_id}>"
            with open("WUscores.json", "r") as f:
                data = json.load(f)
                if str(winner_id) not in data:
                    data[str(winner_id)] = 1
                else:
                    data[str(winner_id)] += 1
            f.close()
            streak = self.update_streak(False, winner_id)
            await message.channel.send(
                f"{winner} has now won the Waking Up Early Award {data[str(winner_id)]} times.     {streak}🔥"
            )
            with open("WUscores.json", "w") as f:
                json.dump(data, f, indent=0)
            f.close()
        if message.content.startswith(prefix):
            messageList = message.content.split()
            if len(messageList) == 3:
                if messageList[1] == "wu":
                    if message.author.id != 603142766805123082 and message.author.id != 299216822647914499:
                        await message.channel.send(
                            "u gotta be moderator to use this pal...")
                        return
                    winner = messageList[2]
                    winner_id = re.sub('[^0-9]', '', winner)
                    with open("WUscores.json", "r") as f:
                        data = json.load(f)
                        if str(winner_id) not in data:
                            data[str(winner_id)] = 1
                        else:
                            data[str(winner_id)] += 1
                    f.close()
                    streak = self.update_streak(False, winner_id)
                    await message.channel.send(
                        f"{winner} has now won the Waking Up Early Award {data[str(winner_id)]} times.     {streak}🔥")
                    with open("WUscores.json", "w") as f:
                        json.dump(data, f, indent=0)
                    f.close()
                    return
                elif messageList[1] == "lm":
                    if message.author.id != 603142766805123082 and message.author.id != 299216822647914499:
                        await message.channel.send(
                            "u gotta be moderator to use this pal...")
                        return
                    winner = messageList[2]
                    winner_id = re.sub('[^0-9]', '', winner)
                    with open("LMscores.json", "r") as f:
                        data = json.load(f)
                        if str(winner_id) not in data:
                            data[str(winner_id)] = 1
                        else:
                            data[str(winner_id)] += 1
                    f.close()
                    streak = self.update_streak(True, winner_id)
                    await message.channel.send(
                        f"{winner} has now won the Last Message Of The Day Award {data[str(winner_id)]} times.     {streak}🔥"
                    )
                    with open("LMscores.json", "w") as f:
                        json.dump(data, f, indent=0)
                    f.close()
                    return
                else:
                    return

            if len(messageList) == 2:
                if messageList[1] == "s":
                    with open("streak.json", "r") as f:
                        data = json.load(f)
                    f.close()
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
                        name=f"Last Message Of The Day",
                        value=f"<@{int(lm_user)}> with {lm_streak}🔥",
                        inline=False)
                    await message.channel.send(embed=eb)
                    return

            with open("WUscores.json", "r") as f:
                data = json.load(f)
                f.close()
                leaders = sorted(data.items(), key=lambda x: x[1], reverse=True)
                eb = discord.Embed(title="Waking Up Early Award Leaderboard",
                                   color=discord.Color.blue())
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
                        value=f"<@{int(leaders[i][0])}> with {leaders[i][1]} wins",
                        inline=False)
                await message.channel.send(embed=eb)
            with open("LMscores.json", "r") as f:
                data = json.load(f)
                f.close()
                leaders = sorted(data.items(), key=lambda x: x[1], reverse=True)
                eb = discord.Embed(title="Last Message Of The Day Leaderboard",
                                   color=discord.Color.blue())
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
                        value=f"<@{int(leaders[i][0])}> with {leaders[i][1]} wins",
                        inline=False)
                await message.channel.send(embed=eb)


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)
client.run(os.getenv("TOKEN"))