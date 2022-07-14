class RequestAPIError(Exception):
    """Вызывается, при ошибке запроса к основному API"""
    pass


class APIStatusCodeError(Exception):
    """Вызывается, при получении неверного статускода"""
    pass


class TelegramMessageError(Exception):
    """Вызывается, при ошибке отправки сообщения в телеграмм"""
    pass


class HomeworkStatusError(Exception):
    """Вызывается, при неизвестном статусе работы"""
    pass
