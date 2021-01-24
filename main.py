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
import time
import pytz
from telegram.utils.helpers import mention_markdown

from telegram import Update, constants
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    Filters,
    CallbackContext,
    PicklePersistence
)

heartEmoji = '❤'
starEmojis = [None] * 5
starEmoji = '🌟'
maxStars = 5
dataBase = 'dataBase'
chatIds = 'chatIds'
mainUserId = 'mainUserId'

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


def addStarsToUser(starCountDictionary, starsNumber, user):
    if user in starCountDictionary:
        starCountDictionary[user] += starsNumber
    else:
        starCountDictionary[user] = starsNumber


def treatRoutine(update, context, thisName, otherName) -> None:
    dictName = f'{thisName}Dict'
    dadoName = f'{thisName}Dado'
    otherDictName = f'{otherName}Dict'
    otherDadoName = f'{otherName}Dado'
    chatName = update.message.chat.title
    if dictName not in context.chat_data:
        context.chat_data[dictName] = collections.OrderedDict()
        context.chat_data[dadoName] = False
        logger.info(f'Resetting {thisName} in chat {chatName}')
    if update.message.from_user.id == context.chat_data[mainUserId] \
            and not context.chat_data[dadoName]:
        context.chat_data[otherDictName] = collections.OrderedDict()
        context.chat_data[otherDadoName] = False
        context.chat_data[dadoName] = True
        logger.info(f'{thisName} dado em {chatName}')
    elif update.message.from_user.id != context.chat_data[mainUserId]\
            and context.chat_data[dadoName]\
            and update.message.from_user.id not in context.chat_data[dictName]\
            and len(context.chat_data[dictName]) < maxStars:
        context.chat_data[dictName][update.message.from_user.id] = update.message
        userStarsIndex = maxStars + 1 - len(context.chat_data[dictName])
        update.message.reply_text(starEmoji * userStarsIndex, quote=True)
        logger.info(f'{thisName} {userStarsIndex}')
        addStarsToUser(context.chat_data[dataBase], userStarsIndex, update.message.from_user.id)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def getMainUser(update: Update, context: CallbackContext) -> None:
    if mainUserId in context.chat_data:
        currentUser = update.message.chat.get_member(user_id=context.chat_data[mainUserId]).user
        userMention = mention_markdown(currentUser.id, currentUser.name)
        update.message.reply_markdown(f'O usuário principal é {userMention}')
    else:
        update.message.reply_text('O usuário principal não foi escolhido. Por favor use /start para escolher')


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    logger.info(f'User {update.message.from_user.first_name} Changing Configuration')
    context.bot_data[chatIds].add(update.message.chat.id)
    context.chat_data[dataBase] = {}
    update.message.reply_text('Olá, Por responda uma mensagem do usuário que iniciará o Bom dia para esse chat.')

    return SET_USER


def setMainUser(update: Update, context: CallbackContext) -> int:
    userReplied = update.message.reply_to_message.from_user
    userMention = mention_markdown(user_id=userReplied.id, name=userReplied.name)
    logger.info(f'Setando usuário {userReplied.full_name} como usuário principal.')
    update.message.reply_markdown(f'Setando usuário {userMention} como usuário principal.')
    context.chat_data[mainUserId] = userReplied.id

    return ConversationHandler.END


def skipSetUser(update: Update, context: CallbackContext) -> int:
    if mainUserId in context.chat_data:
        mainUser = update.message.chat.get_member(user_id=context.chat_data[mainUserId]).user
        logger.info(f'Usuário {mainUser.full_name} em {update.message.chat.title} cancelou ação')
        userMention = mention_markdown(user_id=mainUser.id, name=mainUser.name)
        update.message.reply_markdown(f'Ok, Ação cancelada, usuário principal atual é {userMention}')
    else:
        update.message.reply_text(f'Usuário principal não setado.')

    return ConversationHandler.END


def get_placar_markdown(context, chatId):
    """Send a message when the command /help is issued."""
    currentChat = context.bot.get_chat(chatId)
    placarAtual = 'O placar atual é:\n'
    if dataBase in context.chat_data:
        orderedItems = sorted(context.chat_data[dataBase].items(), key=lambda x: x[1], reverse=True)
        for index, entry in enumerate(orderedItems):
            currentUser = currentChat.get_member(user_id=entry[0]).user
            userMention = mention_markdown(currentUser.id, currentUser.name)
            placarAtual += f'{userMention}: {entry[1]} {starEmoji} {(maxStars - index)*heartEmoji} \n'

    return placarAtual


def mostra_placar_agendado(context: CallbackContext) -> None:
    logger.info("Agendado Rodando")
    with open(f'starCount-{time.strftime("%Y%m%d")}.txt', 'w') as starCount:
        for chatId in context.bot_data[chatIds]:
            placarAtual = get_placar_markdown(context, chatId)
            context.bot.send_message(chatId, placarAtual, parse_mode=constants.PARSEMODE_MARKDOWN)
            starCount.write(f'Resultado dessa semana no grupo {context.bot.get_chat(chatId).title}')
            starCount.write(placarAtual)
            context.chat_data[dataBase] = {}


def mostra_placar(update: Update, context: CallbackContext) -> None:
    placarAtual = get_placar_markdown(context, update.message.chat.id)
    update.message.reply_markdown(placarAtual)


def bomdia(update: Update, context: CallbackContext) -> None:
    """Treat Bom Dias."""
    if mainUserId not in context.chat_data:
        logger.info(f"{update.message.from_user.full_name} em {update.message.chat.title} tentando usar bot antes de"
                    "setar usuário")
        update.message.reply_text('Usuário principal não foi escolhido. Por favor use /start para escolher.')
    else:
        logger.info(f"Bom dia de {update.message.from_user.username} em {update.message.chat.title}")
        if isCurrentTimeInRange(dtime.time(5, 0, 0), dtime.time(12, 0, 0)):
            logger.info("Bom dia aceito")
            treatRoutine(update, context, 'bomdia', 'boanoite')


def boanoite(update: Update, context: CallbackContext) -> None:
    """Treat Boa Noites."""
    if mainUserId not in context.chat_data:
        logger.info(f"{update.message.from_user.full_name} em {update.message.chat.title} tentando usar bot antes de"
                    "setar usuário")
        update.message.reply_text('Usuário principal não foi escolhido. Por favor use /start para escolher.')
    else:
        logger.info(f"Boa noite de {update.message.from_user.username} em {update.message.chat.title}")
        if isCurrentTimeInRange(dtime.time(18, 30, 0), dtime.time(4, 0, 0)):
            logger.info("Boa noite aceito")
            treatRoutine(update, context, 'boanoite', 'bomdia')


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    pp = PicklePersistence(filename='pauloEstrelaBot.pickle')
    updater = Updater(setupInfo.TOKEN, persistence=pp, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    if chatIds not in dispatcher.bot_data:
        dispatcher.bot_data[chatIds] = set()

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("mostraplacar", mostra_placar))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+m+ ?d+i+a+', re.IGNORECASE))
                                          & ~Filters.command, bomdia))
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+a+ ?n+o+i+t+e+', re.IGNORECASE))
                                          & ~Filters.command, boanoite))

    dispatcher.add_handler(CommandHandler('usuarioprincipal', getMainUser))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SET_USER: [
                MessageHandler(Filters.reply, setMainUser),
                CommandHandler('skip', skipSetUser)
            ],
        },
        fallbacks=[CommandHandler('skip', skipSetUser)],
    )

    dispatcher.add_handler(conv_handler)
    updater.job_queue.run_daily(mostra_placar_agendado, dtime.time(13, 00, 00,
                                                                   tzinfo=pytz.timezone('America/Sao_Paulo')), [6])
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
