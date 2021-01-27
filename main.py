#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=W0613, C0116
# type: ignore[union-attr]
# This program is dedicated to the public domain under the CC0 license.

"""
Bot to give a decreasing number of stars to Group members when they answer the greeting of a "main"
user.
The stars number for first repondent changes with the number of group members, limited to 5 stars.
A weekly scoreboard is kept for all users that were given stars.
Usage:

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


def isGreetingReplied(chat_data: dict) -> bool:
    return len(chat_data[f'{boaNoiteName}Dict']) > 0\
            or len(chat_data[f'{bomDiaName}Dict']) > 0


def removeChat(context: CallbackContext, chatId: int) -> None:
    logger.error(f'Cannot Get user in chat {chatId}')
    context.bot_data[chatIds].remove(chatId)
    del context.dispatcher.chat_data[chatId]


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
        userStarsIndex = context.chat_data[numStars] - len(context.chat_data[dictName])
        userStarsIndex = min(userStarsIndex, maxStars)
        context.chat_data[dictName][update.message.from_user.id] = update.message.reply_text(
                starEmoji * userStarsIndex, quote=True)
        logger.info(f'{thisName} {userStarsIndex}')
        addStarsToUser(context.chat_data[dataBase], userStarsIndex, update.message.from_user.id)


def start(update: Update, context: CallbackContext) -> int:
    """Send a message when the command /start is issued."""
    logger.info(f'User {update.message.from_user.first_name} Changing Configuration')
    context.bot_data[chatIds].add(update.message.chat.id)
    if dataBase not in context.chat_data:
        context.chat_data[dataBase] = {}
    update.message.reply_text(
        'Olá, Por responda uma mensagem do usuário que iniciará o Bom dia para esse chat.')

    return SET_USER


def getMainUser(update: Update, context: CallbackContext) -> None:
    if bIsBotStarted(context.chat_data):
        currentUser = update.message.chat.get_member(user_id=context.chat_data[mainUserId]).user
        userMention = mention_markdown(currentUser.id, currentUser.name)
        update.message.reply_markdown(f'O usuário principal é {userMention}')
    else:
        update.message.reply_text(
            'O usuário principal não foi escolhido. Por favor use /start para escolher')


def setStarsNumber(chatData: dict, memberCount: int) -> None:
    chatData[numStars] = min(memberCount - 2, maxStars)


def setMainUser(update: Update, context: CallbackContext) -> int:
    userReplied = update.message.reply_to_message.from_user
    userMention = mention_markdown(user_id=userReplied.id, name=userReplied.name)
    logger.info(f'Setando usuário {userReplied.full_name} como usuário principal.')
    update.message.reply_markdown(f'Setando usuário {userMention} como usuário principal.')
    context.chat_data[mainUserId] = userReplied.id
    memberCount = update.message.chat.get_members_count()
    logger.info(f'Initial Member count in "{update.message.chat.title}" is {memberCount}')
    setStarsNumber(context.chat_data, memberCount)

    return ConversationHandler.END


def skipSetUser(update: Update, context: CallbackContext) -> int:
    if mainUserId in context.chat_data:
        mainUser = update.message.chat.get_member(user_id=context.chat_data[mainUserId]).user
        logger.info(f'Usuário {mainUser.full_name} em {update.message.chat.title} cancelou ação')
        userMention = mention_markdown(user_id=mainUser.id, name=mainUser.name)
        update.message.reply_markdown(
            f'Ok, Ação cancelada, usuário principal atual é {userMention}')
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
            placarAtual += f'{userMention}: {entry[1]} {starEmoji}' \
                           f' {(currentChatData[numStars] - index)*heartEmoji} \n'

    return placarAtual


def mostra_placar_agendado(context: CallbackContext) -> None:
    logger.info("Agendado Rodando")
    with open(f'starCount-{datetime.now().strftime("%Y%m%d")}.txt', 'w') as starCount:
        tempChat = context.bot_data[chatIds].copy()
        for chatId in tempChat:
            placarAtual = ''
            try:
                placarAtual = get_placar_markdown(context, chatId)
            except error.Unauthorized:
                removeChat(context, chatId)
                continue
            context.bot.send_message(chatId, placarAtual, parse_mode=constants.PARSEMODE_MARKDOWN)
            starCount.write(
                f'Resultado dessa semana no grupo {context.bot.get_chat(chatId).title}\n')
            starCount.write(placarAtual)
            if chatId in context.dispatcher.chat_data:
                context.dispatcher.chat_data[chatId][dataBase] = {}


def zeraGreeting(context: CallbackContext) -> None:
    tempSet = context.bot_data[chatIds].copy()
    for chatId in tempSet:
        currentChatData = context.dispatcher.chat_data[chatId]
        dictName = f'{context.job.context}Dict'
        dadoName = f'{context.job.context}Dado'
        currentChatData[dictName] = collections.OrderedDict()
        currentChatData[dadoName] = False


def mostra_placar(update: Update, context: CallbackContext) -> None:
    placarAtual = get_placar_markdown(context, update.message.chat.id)
    update.message.reply_markdown(placarAtual)


def bomdia(update: Update, context: CallbackContext) -> None:
    """Treat Bons Dias."""
    isTimeInRange = isCurrentTimeInRange(dtime.time(5, 0, 0), dtime.time(11, 59, 59))
    treatGreeting(update, context, bomDiaName, isTimeInRange)


def boanoite(update: Update, context: CallbackContext) -> None:
    """Treat Boas Noites."""
    isTimeInRange = isCurrentTimeInRange(dtime.time(18, 30, 0), dtime.time(3, 59, 59))
    treatGreeting(update, context, boaNoiteName, isTimeInRange)


def treatGreeting(update: Update, context: CallbackContext, name: str, isTimeInRange: bool) -> None:
    if mainUserId not in context.chat_data:
        logger.info(
            f'{update.message.from_user.full_name} em {update.message.chat.title} tentando usar bot'
            f' antes de setar usuário')
        update.message.reply_text(
            'Usuário principal não foi escolhido. Por favor use /start para escolher.')
    else:
        logger.info(
            f'Saudação de {update.message.from_user.username} em {update.message.chat.title}')
        if isTimeInRange:
            logger.info("Boa noite aceito")
            treatRoutine(update, context, name)


def sendMembersChangedMessage(context: CallbackContext, chatId, newStarsNum):
    try:
        context.bot.send_message(chatId,
                                 f'Número de Participantes alterado.'
                                 f' Nova quantidade máxima de {starEmoji}s é {newStarsNum}')
    except error.Unauthorized:
        removeChat(context, chatId)


def editStarMessages(context: CallbackContext, newMemberCount: int):
    dictKeyName = ''
    if context.chat_data[f'{boaNoiteName}Dado']:
        dictKeyName = boaNoiteName
    elif context.chat_data[f'{bomDiaName}Dado']:
        dictKeyName = bomDiaName
    for index, key in enumerate(context.chat_data[f'{dictKeyName}Dict']):
        newUserStarsCount = context.chat_data[numStars] - index
        context.chat_data[f'{dictKeyName}Dict'][key].edit_text(newUserStarsCount * starEmoji)
        deltaStars = newUserStarsCount - context.chat_data[numStars]
        context.chat_data[dataBase][key] += deltaStars


def treatMemberNumChange(context: CallbackContext, memberCount: int, chatId: int) -> None:
    setStarsNumber(context.chat_data, memberCount)
    if bIsGreetingGiven(context.chat_data) and isGreetingReplied(context.chat_data):
        editStarMessages(context, memberCount)
    sendMembersChangedMessage(context, chatId, context.chat_data[numStars])


def newChatMembers(update: Update, context: CallbackContext) -> None:
    memberCount = update.message.chat.get_members_count()
    logger.info(f'New chat Member(s) in {update.message.chat.title}')
    if bIsBotStarted(context.chat_data) and context.chat_data[numStars] < 5:
        treatMemberNumChange(context, memberCount, update.message.chat.id)


def userLeft(update: Update, context: CallbackContext) -> None:
    try:
        logger.info(f'Chat Member Left in {update.message.chat.title}')
        memberCount = update.message.chat.get_members_count()
        if bIsBotStarted(context.chat_data) and memberCount <= maxStars + 2:
            treatMemberNumChange(context, memberCount, update.message.chat.id)
    except error.Unauthorized:
        removeChat(context, update.message.chat.id)


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
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(
                re.compile(r'b+o+m+ ?d+i+a+', re.IGNORECASE)) & ~Filters.command, bomdia))
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(
                re.compile(r'b+o+a+ ?n+o+i+t+e+', re.IGNORECASE)) & ~Filters.command, boanoite))
    dispatcher.add_handler(
        MessageHandler(
            Filters.status_update.new_chat_members, newChatMembers))
    dispatcher.add_handler(
        MessageHandler(
            Filters.status_update.left_chat_member, userLeft))

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

    updater.job_queue.run_daily(
        mostra_placar_agendado,
        dtime.time(13, 00, 00, tzinfo=pytz.timezone('America/Sao_Paulo')), [6])
    updater.job_queue.run_daily(
        zeraGreeting,
        dtime.time(12, 00, 00, tzinfo=pytz.timezone('America/Sao_Paulo')), context=bomDiaName)
    updater.job_queue.run_daily(
        zeraGreeting,
        dtime.time(4, 00, 00, tzinfo=pytz.timezone('America/Sao_Paulo')), context=boaNoiteName)
    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
