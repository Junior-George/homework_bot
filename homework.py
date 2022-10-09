import time
import requests
import telegram
import os
from http import HTTPStatus

import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """ Отправляем сообщение в телегу, когда изменился статус домашки """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('отправлено сообщение в телеграм')
    except Exception as error:
        logger.error(error)


def get_api_answer(current_timestamp) -> dict:
    """ Отправляем запрос на ЯП """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    api_result = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if api_result.status_code != HTTPStatus.OK:
        logger.error(f'получен ответ от ЯП{api_result.status_code}')
        raise Exception('Не получилось сделать запрос к API')
    else:
        return api_result.json()


def check_response(response):
    """ Проверяем полученый ответ от ЯП """
    logger.debug("Проверка ответа API на корректность")
    response_hw = response['homeworks']
    if type(response_hw) is not list:
        raise Exception('Неправильный формат')
    if len(response_hw) == 0:
        logger.error(" В этом списке пусто")
    return response_hw


def parse_status(homework):
    """Возвращает статус домашней работы."""
    if 'homework_name' not in homework:
        logger.error('Key homework_name does not exist')
    if type(homework) == dict:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Wrong status of homework')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """ Проверяем наличие токенов """
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID is not None:
        logger.info('токены на месте')
        return True
    else:
        logger.critical('Не хватает переменных(токенов)')
        return False


def main():
    """Основная логика работы бота."""

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while check_tokens():
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                status = parse_status(homework)
                send_message(bot, status)
            else:
                logger.debug('Ответ от сервера получен. Статус не изменился.')

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
