import os
import time
import requests
import logging
import telegram

from sys import exit
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

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
    """Отправляем сообщение в телегу, когда изменился статус домашки."""
    logger.info('Начинаем отправлять сообщение в телегу')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise Exception(error)
    else:
        logger.info('отправлено сообщение в телеграм')


def get_api_answer(current_timestamp) -> dict:
    """Отправляем запрос на ЯП."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    api_result = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if api_result.status_code != HTTPStatus.OK:
        logger.error(f'получен ответ от ЯП{api_result.status_code}')
        raise Exception('Не получилось сделать запрос к API')
    return api_result.json()


def check_response(response):
    """Проверяем полученый ответ от ЯП."""
    logger.debug("Проверка ответа API на корректность")
    response_hw = response['homeworks']
    if not isinstance(response_hw, list):
        raise Exception('Неправильный формат')
    if len(response_hw) == 0:
        raise Exception('Список response_hw пустой')
    return response_hw


def parse_status(homework):
    """Возвращает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа homework_name в homework')
    if isinstance(homework, dict):
        homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('Нет ключа status в homework')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Wrong status of homework')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем наличие токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical('отсутствуют токены')
        exit()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                try:
                    status = parse_status(homework)
                    send_message(bot, status)
                except Exception as error:
                    logger.error(f"Ошибка - {error}")
            else:
                logger.debug('Ответ от сервера получен. Статус не изменился.')

            current_timestamp = int(time.time())

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
