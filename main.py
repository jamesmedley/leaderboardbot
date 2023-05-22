from time import sleep
import datetime
import os
from keep_alive import keep_alive

restart_timer = 5


def start_script():
    print("starting")
    with open("logs.txt", "a") as file:
        file.write(f"RUNNING, {datetime.datetime.now()}\n")
    os.system('python bot.py')
    handle_crash()


def handle_crash():
    with open("logs.txt", "a") as file:
        file.write(f"CRASH, {datetime.datetime.now()}\n")
    sleep(restart_timer)

    start_script()


keep_alive()
start_script()
