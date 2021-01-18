#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0116
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import setupInfo
import collections
import re
import datetime as dtime
from datetime import datetime

from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

starEmojis = [None] * 5
starEmojis[4]=4*'🌟'
starEmojis[3]=3*'🌟'
starEmojis[2]=2*'🌟'
starEmojis[1]='🌟'
starEmojis[0]='⭐️'
maxStars = 5

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def isCurrentTimeInRange(start, end):
    currentTime = datetime.now().time()
    if start <= end:
        return start <= currentTime <= end
    else:
        return start <= currentTime or currentTime <= end


def treatRoutine(update, context, thisName, otherName) -> None:
    dictName = f'{thisName}{update.message.chat.id}Dict'
    dadoName = f'{thisName}{update.message.chat.id}Dado'
    otherDictName = f'{otherName}{update.message.chat.id}Dict'
    otherDadoName = f'{otherName}{update.message.chat.id}Dado'
    if (dictName not in context.bot_data):
        context.bot_data[dictName] = collections.OrderedDict()
        context.bot_data[dadoName] = False
        logger.info(f'Resetting {dictName}')
    if(update.message.from_user.username == 'P4cvaz' and not context.bot_data[dadoName]):
        context.bot_data[otherDictName] = collections.OrderedDict()
        context.bot_data[otherDadoName] = False
        context.bot_data[dadoName] = True
        logger.info(dadoName)
        for index, userId in enumerate(context.bot_data[dictName]):
            context.bot_data[dictName][userId].reply_text(starEmojis[maxStars - index - 1], quote=True)
            logger.info(f'{thisName}{maxStars - index - 1}')
    elif(update.message.from_user.username != 'P4cvaz'):
        if(update.message.from_user.id not in context.bot_data[dictName]):
            context.bot_data[dictName][update.message.from_user.id] = update.message
            if(context.bot_data[dadoName]):
                update.message.reply_text(starEmojis[maxStars - len(context.bot_data[dictName])], quote=True)
                logger.info(f'{thisName}{maxStars - len(context.bot_data[dictName])}')
    if(context.bot_data[dadoName] and len(context.bot_data[dictName]) == maxStars):
        context.bot_data[dictName] = collections.OrderedDict()
        context.bot_data[dadoName] = False

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def bomdia(update: Update, context: CallbackContext) -> None:
    """Treat Bom Dias."""
    if isCurrentTimeInRange(dtime.time(4,0,0), dtime.time(12,0,0)):
        treatRoutine(update, context, 'bomdia', 'boanoite')

def boanoite(update: Update, context: CallbackContext) -> None:
    """Treat Boa Noites."""
    if isCurrentTimeInRange(dtime.time(17,0,0), dtime.time(4,0,0)):
        treatRoutine(update, context, 'boanoite', 'bomdia')

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(setupInfo.TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+m+ +d+i+a+', re.IGNORECASE)) & ~Filters.command, bomdia))
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+a+ +n+o+i+t+e+', re.IGNORECASE)) & ~Filters.command, boanoite))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
