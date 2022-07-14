import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (RequestAPIError, APIStatusCodeError,
                        TelegramMessageError, HomeworkStatusError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 5
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info(
            f'Пробуем отправить сообщение в чат {TELEGRAM_CHAT_ID}: {message}'
        )
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramMessageError:
        raise TelegramMessageError('Ошибка отправки сообщения в телеграм')
    else:
        logger.info(
            f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}: {message}'
        )


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        logger.info('Делаем запрос к API')
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except RequestAPIError as error:
        raise RequestAPIError(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise APIStatusCodeError(f'Ошибка {homework_statuses.status_code}')
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Ошибка ключей словаря')
    if not isinstance(response.get('homeworks'), list):
        raise KeyError(
            'В ответе от API под ключом "homeworks" пришел не список.'
            f' response = {response}.'
        )
    return response.get('homeworks')


def parse_status(homework):
    """Извлекает из информации о домашней работе - статус этой работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise HomeworkStatusError(
            f'Неизвестный статус работы: {homework_status}'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        sys.exit('Отсутствуют одна или несколько переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 3600*24*30
    STATUS = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            homework = check_response(response)
            if len(homework) != 0:
                message = parse_status(homework[0])
                if message != STATUS:
                    send_message(bot, message)
                    STATUS = message
            else:
                logger.debug('Отсутствие в ответе новых статусов ')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            raise Exception(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter(
        '%(asctime)s, %(levelname)s, %(message)s'
    )
    handler.setFormatter(formatter)
    main()
