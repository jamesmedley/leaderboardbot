# shell: python user_performance/count_wins.py

import discord
import pytz
import json
import os
from replit import db

TOKEN = os.getenv("TOKEN")
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"Logged in as {client.user.name} ({client.user.id})")
    print(db["WU_scores"])
    # await find_waking_up_winners()
    # await find_last_message_winners()
    # analyse_data("wu_wins.json")
    # update_database_with_counted_wins()


def get_uk_time(msg):
    utc_time = msg.created_at.replace(tzinfo=pytz.UTC)
    uk_time = utc_time.astimezone(pytz.timezone("Europe/London"))
    return uk_time


async def find_last_message_winners():
    print("Scanning messages...")
    CHANNEL_ID = 525730239800672257
    STARTING_MESSAGE_ID = 695758099709034527
    channel = client.get_channel(CHANNEL_ID)
    message = await channel.fetch_message(STARTING_MESSAGE_ID)
    data = {}
    prev_message = message
    async for msg in message.channel.history(limit=91635, after=message):
        if get_uk_time(msg).date() > get_uk_time(prev_message).date():
            if prev_message.author.id not in data:
                data[prev_message.author.id] = [str(get_uk_time(prev_message).date())]
            else:
                data[prev_message.author.id].append(str(get_uk_time(prev_message).date()))
        prev_message = msg

    print(data)
    data_json = json.dumps(data)
    with open("user_performance/lm_wins.json", "w") as file:
        file.write(data_json)

    print(data)


async def find_waking_up_winners():
    print("Scanning messages...")
    CHANNEL_ID = 525730239800672257
    STARTING_MESSAGE_ID = 748674557812015216
    channel = client.get_channel(CHANNEL_ID)
    message = await channel.fetch_message(STARTING_MESSAGE_ID)
    data = {}
    prev_message = message
    async for msg in message.channel.history(limit=65386, after=message):
        if prev_message.author.id == 748488791471161405:
            if msg.author.id not in data:
                data[msg.author.id] = [str(get_uk_time(msg).date())]
            else:
                data[msg.author.id].append(str(get_uk_time(msg).date()))
        prev_message = msg

    data_json = json.dumps(data)
    with open("user_performance/wu_wins.json", "w") as file:
        file.write(data_json)

    print(data)


def convert_dict(dictionary):
    new_dict = {}
    for key, value in dictionary.items():
        new_dict[key] = (value, len(value))
    return new_dict


def update_database_with_counted_wins():
    with open("user_performance/wu_wins.json", "r") as file:
        wu = json.load(file)

    with open("user_performance/lm_wins.json", "r") as file:
        lm = json.load(file)

    wu_json = convert_dict(wu)
    lm_json = convert_dict(lm)

    db["WU_scores"] = wu_json
    db["LM_scores"] = lm_json

    return


def analyse_data(file):
    with open(file, "r") as file:
        data = json.load(file)
        print(data)
    for key in data:
        print(key, len(data[key]))


client.run(TOKEN)
