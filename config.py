from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')  # Используем имя переменной окружения
DB_PATH = os.getenv('DB_PATH', 'sqlite://finance_bot.db')

print(f"TOKEN: {TOKEN}")  # Для отладки
print(f"DB_PATH: {DB_PATH}")  # Для отладки