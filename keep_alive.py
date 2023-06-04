from flask import Flask, render_template, send_from_directory
from threading import Thread
from replit import db
import requests
import os
from functools import lru_cache


def convert_observed_dict_to_dict(data):
    if isinstance(data, dict):
        return {key: convert_observed_dict_to_dict(value) for key, value in data.items()}
    elif hasattr(data, "value"):
        return convert_observed_dict_to_dict(data.value)
    else:
        return data


@lru_cache(maxsize=128)
def get_user_info(user_id):
    headers = {
        "Authorization": f"Bot {os.getenv('TOKEN')}"
    }
    response = requests.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        username = user_data["username"]
        discriminator = user_data["discriminator"]
        profile_picture = f"https://cdn.discordapp.com/avatars/{user_id}/{user_data['avatar']}.png"
        return {"username": username + "#" + discriminator, "profile_picture": profile_picture}
    return None


app = Flask(" ")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory('static', filename)


@app.route("/wakingup")
def wakingup():
    last_message_scores = dict(db["WUscores"])
    sorted_scores = sorted(last_message_scores.items(), key=lambda x: x[1], reverse=True)
    users_info = []
    for user_id, score in sorted_scores:
        user_info = get_user_info(user_id)
        if user_info:
            users_info.append((user_info["username"], user_info["profile_picture"], score))
    return render_template("leaderboard.html", leaderboard=users_info, title="Waking Up Early Award")


@app.route("/lastmessage")
def lastmessage():
    last_message_scores = dict(db["LMscores"])
    sorted_scores = sorted(last_message_scores.items(), key=lambda x: x[1], reverse=True)
    users_info = []
    for user_id, score in sorted_scores:
        user_info = get_user_info(user_id)
        if user_info:
            users_info.append((user_info["username"], user_info["profile_picture"], score))
    return render_template("leaderboard.html", leaderboard=users_info, title="Last Message Of The Day Award")


@app.route("/streaks")
def streaks():
    return convert_observed_dict_to_dict(db["streak"])


def run():
    app.run(host="0.0.0.0", port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()
