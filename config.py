import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

BOT_TOKEN = os.getenv('BOT_TOKEN')  # Токен бота из .env
DB_URL = os.getenv('DB_URL', 'sqlite://db.sqlite3')  # URL БД, по умолчанию SQLite

# Другие настройки, если нужно (например, для будущих фич)
AGREEMENT_FILE = 'data/utils/agreement.txt'  # Путь к файлу соглашения
DEFAULT_CATEGORIES_EXPENSE = ['Еда', 'Транспорт', 'Кофейня']  # Базовые категории расходов
DEFAULT_CATEGORIES_INCOME = ['Зарплата', 'Фриланс', 'Другое']  # Базовые категории доходов (добавил для симметрии, по ТЗ для доходов аналогично)