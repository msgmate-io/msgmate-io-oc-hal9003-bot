#!/bin/bash


# start the bot process
pymon bot.py -c

# start the server process
if [ "$SEPERATE_SERVER" = "true" ]; then
    python3 -u server.py
fi