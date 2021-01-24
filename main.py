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
import os.path
import datetime as dtime
from datetime import datetime
import time
import pytz
import pickle
from telegram.utils.helpers import mention_markdown

from telegram import Update, constants
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    Filters,
    CallbackContext
)

heartEmoji = '❤'
starEmojis = [None] * 5
starEmojis[4] = 5*'🌟'
starEmojis[3] = 4*'🌟'
starEmojis[2] = 3*'🌟'
starEmojis[1] = 2*'🌟'
starEmojis[0] = '🌟'
maxStars = 5
starCountFile = 'starCount.pickle'
userNamesFile = 'userFile.pickle'
dataBase = 'dataBase'
userMap = 'userMap'
chatIds = 'chatIds'
mainUserName = 'mainUserName'

SET_USER, CANCEL = range(2)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def isCurrentTimeInRange(startTime, end):
    currentTime = datetime.now().time()
    if startTime <= end:
        return startTime <= currentTime <= end
    else:
        return startTime <= currentTime or currentTime <= end


def loadPickleFile(fileName):
    loadDataBase = {}
    if os.path.isfile(fileName):
        with open(fileName, 'rb') as starCount:
            loadDataBase = pickle.load(starCount)
    return loadDataBase


def saveToPickleFile(starCountDict):
    with open(starCountFile, 'wb') as starCount:
        pickle.dump(starCountDict, starCount)


def addStarsToUser(starCountDictionary, starsNumber, user):
    if user in starCountDictionary:
        starCountDictionary[user] += starsNumber
    else:
        starCountDictionary[user] = starsNumber
    saveToPickleFile(starCountDictionary)


def addUserToMap(userMapDict, user):
    if user.id not in userMapDict:
        userMapDict[user.id] = user.first_name
        with open(userNamesFile, 'wb') as usersFile:
            pickle.dump(userMapDict, usersFile)


def treatRoutine(update, context, thisName, otherName) -> None:
    dictName = f'{thisName}{update.message.chat.id}Dict'
    dadoName = f'{thisName}{update.message.chat.id}Dado'
    otherDictName = f'{otherName}{update.message.chat.id}Dict'
    otherDadoName = f'{otherName}{update.message.chat.id}Dado'
    mainUser = f'{mainUserName}{update.message.chat.id}'
    if dictName not in context.bot_data:
        context.bot_data[dictName] = collections.OrderedDict()
        context.bot_data[dadoName] = False
        context.bot_data[chatIds].add(update.message.chat.id)
        logger.info(f'Resetting {dictName}')
    if update.message.from_user.username == context.bot_data[mainUser] and not context.bot_data[dadoName]:
        context.bot_data[otherDictName] = collections.OrderedDict()
        context.bot_data[otherDadoName] = False
        context.bot_data[dadoName] = True
        logger.info(dadoName)
    elif update.message.from_user.username != context.bot_data[mainUser] and context.bot_data[dadoName]:
        if update.message.from_user.id not in context.bot_data[dictName]:
            context.bot_data[dictName][update.message.from_user.id] = update.message
            if context.bot_data[dadoName]:
                userStarsIndex = maxStars - len(context.bot_data[dictName])
                update.message.reply_text(starEmojis[userStarsIndex], quote=True)
                logger.info(f'{thisName} {userStarsIndex + 1}')
                addStarsToUser(context.bot_data[dataBase], userStarsIndex + 1, update.message.from_user.id)
                addUserToMap(context.bot_data[userMap], update.message.from_user)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    logger.info(f'User {update.message.from_user.first_name} Changing Configuration')
    update.message.reply_text('Olá, Por favor marque o usuário que iniciará o Bom dia para esse chat.')

    return SET_USER


def setMainUser(update: Update, context: CallbackContext) -> int:
    mainUser = f'{mainUserName}{update.message.chat.id}'
    userMentioned = update.message.text.replace('@', '')
    #userMention = mention_markdown(user_id=userMentioned.id, name=userMentioned.name)
    logger.info(f'Setando usuário {userMentioned} como usuário principal.')
    update.message.reply_markdown(f'Setando usuário {userMentioned} como usuário principal.')
    context.bot_data[mainUser] = userMentioned

    return ConversationHandler.END


def skipSetUser(update: Update, context: CallbackContext) -> int:
    mainUser = f'{mainUserName}{update.message.chat.id}'
    logger.info(f'Usuário {update.message.from_user.username} em {update.message.chat.title} cancelou ação')
    currentUser = context.bot_data[mainUser] if mainUser in context.bot_data else 'Nenhum'
    update.message.reply_text(f'Ok, Ação cancelada, usuário principal atual é {currentUser}')

    return ConversationHandler.END


def get_placar_markdown(context):
    """Send a message when the command /help is issued."""
    placarAtual = 'O placar atual é:\n'
    orderedItems = sorted(context.bot_data[dataBase].items(), key=lambda x: x[1], reverse=True)
    for index, entry in enumerate(orderedItems):
        userMention = mention_markdown(entry[0], context.bot_data[userMap][entry[0]])
        placarAtual += f'{userMention}: {entry[1]} {starEmojis[0]} {(maxStars - index)*heartEmoji} \n'

    return placarAtual


def mostra_placar_agendado(context: CallbackContext) -> None:
    logger.info("Agendado Rodando")
    for chatId in context.bot_data[chatIds]:
        placarAtual = get_placar_markdown(context)
        context.bot.send_message(chatId, placarAtual, parse_mode=constants.PARSEMODE_MARKDOWN)
    with open(f'starCount-{time.strftime("%Y%m%d")}.pickle', 'wb') as starCount:
        pickle.dump(context.bot_data[dataBase], starCount)
    with open(f'userMap-{time.strftime("%Y%m%d")}.pickle', 'wb') as userMapFile:
        pickle.dump(context.bot_data[userMap], userMapFile)
    context.bot_data[userMap] = {}
    context.bot_data[dataBase] = {}


def mostra_placar(update: Update, context: CallbackContext) -> None:
    placarAtual = get_placar_markdown(context)
    update.message.reply_markdown(placarAtual)


def bomdia(update: Update, context: CallbackContext) -> None:
    """Treat Bom Dias."""
    mainUser = f'{mainUserName}{update.message.chat.id}'
    if mainUser not in context.bot_data:
        logger.info(f"{update.message.from_user.username} em {update.message.chat.title} tentando usar bot antes de"
                    "setar usuário")
        update.message.reply_text('Usuário principal não foi escolhido. Por favor use /start para escolher.')
    else:
        logger.info(f"Bom dia de {update.message.from_user.username} em {update.message.chat.title}")
        if isCurrentTimeInRange(dtime.time(5, 0, 0), dtime.time(12, 0, 0)):
            logger.info("Bom dia aceito")
            treatRoutine(update, context, 'bomdia', 'boanoite')


def boanoite(update: Update, context: CallbackContext) -> None:
    """Treat Boa Noites."""
    mainUser = f'{mainUserName}{update.message.chat.id}'
    if mainUser not in context.bot_data:
        logger.info(f"{update.message.from_user.username} em {update.message.chat.title} tentando usar bot antes de setar usuário")
        update.message.reply_text('Usuário principal não foi escolhido. Por favor use /start para escolher.')
    else:
        logger.info(f'Usuário principal é {context.bot_data[mainUser]}')
        logger.info(f"Boa noite de {update.message.from_user.username} em {update.message.chat.title}")
        if isCurrentTimeInRange(dtime.time(18, 30, 0), dtime.time(4, 0, 0)):
            logger.info("Boa noite aceito")
            treatRoutine(update, context, 'boanoite', 'bomdia')


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(setupInfo.TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    dispatcher.bot_data[chatIds] = set()
    dispatcher.bot_data[dataBase] = loadPickleFile(starCountFile)
    dispatcher.bot_data[userMap] = loadPickleFile(userNamesFile)

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("mostraplacar", mostra_placar))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+m+ ?d+i+a+', re.IGNORECASE)) & ~Filters.command, bomdia))
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+a+ ?n+o+i+t+e+', re.IGNORECASE)) & ~Filters.command, boanoite))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SET_USER: [
                MessageHandler(Filters.entity(constants.MESSAGEENTITY_MENTION) | Filters.entity(constants.MESSAGEENTITY_TEXT_MENTION), setMainUser),
                CommandHandler('skip', skipSetUser)
            ],
        },
        fallbacks=[CommandHandler('skip', skipSetUser)],
    )

    dispatcher.add_handler(conv_handler)
    updater.job_queue.run_daily(mostra_placar_agendado, dtime.time(13, 00, 00, tzinfo=pytz.timezone('America/Sao_Paulo')), [6])
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
