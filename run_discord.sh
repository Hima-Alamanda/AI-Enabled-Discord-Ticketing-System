#!/bin/bash

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi


pip3 install discord.py python-dotenv

python3 discord_bot.py

 