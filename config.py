import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DB_URL = os.getenv('DB_URL', 'sqlite://db.sqlite3')

AGREEMENT_FILE = 'data/utils/agreement.txt'
DEFAULT_CATEGORIES_EXPENSE = ['Еда', 'Транспорт', 'Кофейня']
DEFAULT_CATEGORIES_INCOME = ['Зарплата', 'Фриланс', 'Другое']
