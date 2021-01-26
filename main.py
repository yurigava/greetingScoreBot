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

from typing import List

import setupInfo
import collections
import re
import datetime as dtime
from datetime import datetime
import time
import pytz
from telegram.utils.helpers import mention_markdown

from telegram import Update, constants, error, User
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    Filters,
    CallbackContext,
    PicklePersistence,
)

heartEmoji = '❤'
starEmojis = [None] * 5
starEmoji = '🌟'
maxStars = 5
minStars = 2
numStars = 'numStars'
dataBase = 'dataBase'
chatIds = 'chatIds'
mainUserId = 'mainUserId'
boaNoiteName = 'boanoite'
bomDiaName = 'bomdia'
usersBalance = 'usersBalance'

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


def bIsBotStarted(chat_data: dict) -> bool:
    return all(key in chat_data for key in [mainUserId, numStars])


def bIsGreetingGiven(chat_data: dict) -> bool:
    dadoNames = [f'{thisName}Dado' for thisName in [bomDiaName, boaNoiteName]]
    return any(key in chat_data and chat_data[key] for key in dadoNames)


def getNonBotCount(users: List[User]) -> int:
    return len([member for member in users if not member.is_bot])


def treatRoutine(update, context, thisName) -> None:
    dictName = f'{thisName}Dict'
    dadoName = f'{thisName}Dado'
    chatName = update.message.chat.title
    if dictName not in context.chat_data:
        context.chat_data[dictName] = collections.OrderedDict()
        context.chat_data[dadoName] = False
        logger.info(f'Resetting {thisName} in chat {chatName}')
    if update.message.from_user.id == context.chat_data[mainUserId] \
            and not context.chat_data[dadoName]:
        context.chat_data[dadoName] = True
        logger.info(f'{thisName} dado em {chatName}')
    elif update.message.from_user.id != context.chat_data[mainUserId]\
            and context.chat_data[dadoName]\
            and update.message.from_user.id not in context.chat_data[dictName]\
            and len(context.chat_data[dictName]) < context.chat_data[numStars]:
        context.chat_data[dictName][update.message.from_user.id] = update.message
        userStarsIndex = context.chat_data[numStars] + 1 - len(context.chat_data[dictName])
        update.message.reply_text(starEmoji * userStarsIndex, quote=True)
        logger.info(f'{thisName} {userStarsIndex}')
        addStarsToUser(context.chat_data[dataBase], userStarsIndex, update.message.from_user.id)


def getMainUser(update: Update, context: CallbackContext) -> None:
    if bIsBotStarted(context.chat_data):
        currentUser = update.message.chat.get_member(user_id=context.chat_data[mainUserId]).user
        userMention = mention_markdown(currentUser.id, currentUser.name)
        update.message.reply_markdown(f'O usuário principal é {userMention}')
    else:
        update.message.reply_text('O usuário principal não foi escolhido. Por favor use /start para escolher')


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    logger.info(f'User {update.message.from_user.first_name} Changing Configuration')
    context.bot_data[chatIds].add(update.message.chat.id)
    if dataBase not in context.chat_data:
        context.chat_data[dataBase] = {}
    update.message.reply_text('Olá, Por responda uma mensagem do usuário que iniciará o Bom dia para esse chat.')

    return SET_USER


def setMainUser(update: Update, context: CallbackContext) -> int:
    userReplied = update.message.reply_to_message.from_user
    userMention = mention_markdown(user_id=userReplied.id, name=userReplied.name)
    logger.info(f'Setando usuário {userReplied.full_name} como usuário principal.')
    update.message.reply_markdown(f'Setando usuário {userMention} como usuário principal.')
    context.chat_data[mainUserId] = userReplied.id
    memberCount = getNonBotCount(update.message.new_chat_members)
    logger.info(f'Initial Member count in "{update.message.chat.title}" is {memberCount}')
    context.chat_data[numStars] = memberCount - 1 if memberCount <= maxStars else maxStars
    context.chat_data[usersBalance] = 0

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


def get_placar_markdown(context: CallbackContext, chatId: int) -> str:
    """Send a message when the command /help is issued."""
    placarAtual = ''
    currentChatData = context.dispatcher.chat_data[chatId]
    if dataBase in currentChatData:
        placarAtual = 'O placar atual é:\n'
        orderedItems = sorted(currentChatData[dataBase].items(), key=lambda x: x[1], reverse=True)
        for index, entry in enumerate(orderedItems):
            currentUserMember = context.bot.get_chat_member(chat_id=chatId, user_id=entry[0])
            currentUser = currentUserMember.user
            userMention = mention_markdown(currentUser.id, currentUser.name)
            placarAtual += f'{userMention}: {entry[1]} {starEmoji} {(currentChatData[numStars] - index)*heartEmoji} \n'

    return placarAtual


def mostra_placar_agendado(context: CallbackContext) -> None:
    logger.info("Agendado Rodando")
    with open(f'starCount-{time.strftime("%Y%m%d")}.txt', 'w') as starCount:
        for chatId in context.bot_data[chatIds]:
            placarAtual = ''
            try:
                placarAtual = get_placar_markdown(context, chatId)
            except error.Unauthorized:
                logger.error(f'Cannot Get user in chat {chatId}')
                del context.bot_data[chatIds][chatId]
                del context.dispatcher.chat_data[chatId]
                continue
            context.bot.send_message(chatId, placarAtual, parse_mode=constants.PARSEMODE_MARKDOWN)
            starCount.write(f'Resultado dessa semana no grupo {context.bot.get_chat(chatId).title}\n')
            starCount.write(placarAtual)
            if chatId in context.dispatcher.chat_data:
                context.dispatcher.chat_data[chatId][dataBase] = {}


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
            treatRoutine(update, context, bomDiaName)


def addStars(chat_data: dict, numOfNewMembers: int) -> bool:
    bChanged = False
    if chat_data[numStars] < maxStars:
        chat_data[numStars] += numOfNewMembers
        chat_data[numStars] = maxStars if chat_data[numStars] > maxStars else chat_data[numStars]
        bChanged = True

    return bChanged


def removeStars(chat_data: dict, numOfNewMembers: int) -> bool:
    bChanged = False
    if chat_data[numStars] > minStars:
        chat_data[numStars] -= numOfNewMembers
        chat_data[numStars] = minStars if chat_data[numStars] < minStars else chat_data[numStars]
        bChanged = True

    return bChanged


def sendMembersChangedMessage(context: CallbackContext, chatId, newStarsNum):
    try:
        context.bot.send_message(chatId,
                                 f'Número de Participantes alterado.'
                                 f' Nova quantidade máxima de {starEmoji}s é {newStarsNum}')
    except error.Unauthorized:
        logger.error(f'Cannot Get user in chat {chatId}')
        del context.bot_data[chatIds][chatId]
        del context.dispatcher.chat_data[chatId]


def updateStarCount(context: CallbackContext, chatId):
    currentChatData = context.dispatcher.chat_data[chatId]
    if currentChatData[usersBalance] < 0:
        if removeStars(currentChatData, currentChatData[usersBalance] * -1):
            sendMembersChangedMessage(context, chatId, currentChatData[numStars])
    elif currentChatData[usersBalance] > 0:
        if addStars(currentChatData, currentChatData[usersBalance]):
            sendMembersChangedMessage(context, chatId, currentChatData[numStars])


def zeraGreeting(context: CallbackContext) -> None:
    for chatId in context.bot_data[chatIds]:
        currentChatData = context.dispatcher.chat_data[chatId]
        otherDictName = f'{context.job.context}Dict'
        otherDadoName = f'{context.job.context}Dado'
        currentChatData[otherDictName] = collections.OrderedDict()
        currentChatData.chat_data[otherDadoName] = False
        if bIsBotStarted(currentChatData):
            updateStarCount(context, chatId)


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
            treatRoutine(update, context, boaNoiteName)


def newChatMembers(update: Update, context: CallbackContext) -> None:
    if bIsBotStarted(context.chat_data):
        numOfNewMembers = getNonBotCount(update.message.new_chat_members)
        if bIsGreetingGiven(context.chat_data) and len(context.chat_data[dataBase]) > 0:
            logger.info(f'{numOfNewMembers} New chat Member(s) in {update.message.chat.title}')
            context.chat_data[usersBalance] += numOfNewMembers
        elif addStars(context.chat_data, numOfNewMembers):
            sendMembersChangedMessage(context, update.message.chat.id, context.chat_data[numStars])


def userLeft(update: Update, context: CallbackContext) -> None:
    if bIsBotStarted(context.chat_data):
        if bIsGreetingGiven(context.chat_data) and len(context.chat_data[dataBase]) > 0:
            logger.info(f'Chat Member Left in {update.message.chat.title}')
            context.chat_data[usersBalance] -= 1
        elif removeStars(context.chat_data, 1):
            sendMembersChangedMessage(context, update.message.chat.id, context.chat_data[numStars])


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
    dispatcher.add_handler(CommandHandler('mostraplacar', mostra_placar))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+m+ ?d+i+a+', re.IGNORECASE))
                                          & ~Filters.command, bomdia))
    dispatcher.add_handler(MessageHandler(Filters.regex(re.compile(r'b+o+a+ ?n+o+i+t+e+', re.IGNORECASE))
                                          & ~Filters.command, boanoite))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, newChatMembers))
    dispatcher.add_handler(MessageHandler(Filters.status_update.left_chat_member, userLeft))

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
    updater.job_queue.run_daily(zeraGreeting, dtime.time(12, 1, 00,
                                                         tzinfo=pytz.timezone('America/Sao_Paulo')), context=bomDiaName)
    updater.job_queue.run_daily(zeraGreeting, dtime.time(4, 1, 00,
                                                         tzinfo=pytz.timezone('America/Sao_Paulo')),
                                context=boaNoiteName)
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
