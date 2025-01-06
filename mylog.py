import logging
import datetime
from logging.handlers import RotatingFileHandler


class MyLog():
    def __init__(self, name: str = "undefinedName", level: str = "WARNING") -> None:
        now = datetime.datetime.now()
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.get_level(level))
        self.logger.propagate = False
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        rotating_handler = RotatingFileHandler(f'{name}.log', encoding='utf-8', maxBytes=104857, backupCount=10)
        rotating_handler.setLevel(logging.INFO)
        rotating_handler.setFormatter(formatter)
        # file_handler = logging.FileHandler(f"{name}_{now.strftime('%m%d')}.log", encoding='utf-8')
        # file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)
        self.logger.addHandler(rotating_handler)

    def get_level(self, level):
        if "WARN" in level:
            return logging.WARNING
        elif "INFO" in level:
            return logging.INFO
        elif "ERROR" in level:
            return logging.ERROR
        elif "DEBUG" in level:
            return logging.DEBUG
        elif "CIRTICAL" in level:
            return logging.CRITICAL
        else:
            print(f"what is {level}??")
            return 0
