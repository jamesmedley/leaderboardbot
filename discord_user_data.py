import requests
from functools import lru_cache
import os


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
    return {"username": f"{response.status_code} error", "profile_picture": None}
