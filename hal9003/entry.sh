#!/bin/bash


# start the bot process
pymon bot.py -c &

# start the api process
python3 -u api.py