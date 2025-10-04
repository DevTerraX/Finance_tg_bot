import sqlite3
import datetime

conn = sqlite3.connect('finance_bot.db')
cursor = conn.cursor()

def init_db():
    # Создание таблиц
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        amount REAL,
        category TEXT,
        wallet TEXT,
        note TEXT,
        date DATETIME
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        emoji TEXT,
        kind TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        target_amount REAL,
        current_amount REAL,
        limit_category TEXT,
        limit_amount REAL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        default_currency TEXT,
        reminder_time TEXT,
        pin TEXT,
        chat_id INTEGER
    )
    ''')
    
    # Добавление столбца chat_id если отсутствует
    cursor.execute("PRAGMA table_info(settings)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'chat_id' not in columns:
        cursor.execute("ALTER TABLE settings ADD COLUMN chat_id INTEGER")
    
    # Дефолтные данные
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO settings (id, default_currency, reminder_time, pin, chat_id) VALUES (1, '₽', '22:00', NULL, NULL)")
    
    cursor.execute("INSERT OR IGNORE INTO wallets (name) VALUES ('Наличные'), ('Карта')")
    cursor.execute("INSERT OR IGNORE INTO categories (name, emoji, kind) VALUES ('Еда', '🍔', 'expense'), ('Заправка', '⛽', 'expense'), ('Магазин', '🛒', 'expense'), ('Развлечения', '🎮', 'expense')")
    cursor.execute("INSERT OR IGNORE INTO categories (name, emoji, kind) VALUES ('Зарплата', '💼', 'income'), ('Подарок', '🎁', 'income'), ('Лотерея', '🎲', 'income')")
    
    conn.commit()

def add_transaction(type_, amount, category, wallet, note=None):
    cursor.execute("INSERT INTO transactions (type, amount, category, wallet, note, date) VALUES (?, ?, ?, ?, ?, ?)",
                   (type_, amount, category, wallet, note, datetime.datetime.now()))
    conn.commit()

def get_balance():
    cursor.execute("SELECT SUM(CASE WHEN type='income' THEN amount ELSE 0 END) - SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) FROM transactions")
    return cursor.fetchone()[0] or 0

def get_summary(period):
    today = datetime.date.today()
    if period == 'day':
        start = end = today
    elif period == 'week':
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
    else:
        start = today.replace(day=1)
        end = (start + datetime.timedelta(days=31)).replace(day=1) - datetime.timedelta(days=1)
    
    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='expense' AND date BETWEEN ? AND ? GROUP BY category", (start, end + datetime.timedelta(days=1)))
    expenses = cursor.fetchall()
    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='income' AND date BETWEEN ? AND ? GROUP BY category", (start, end + datetime.timedelta(days=1)))
    incomes = cursor.fetchall()
    return expenses, incomes

def get_category_summary(category):
    cursor.execute("SELECT type, SUM(amount) FROM transactions WHERE category = ? GROUP BY type", (category,))
    return cursor.fetchall()

def get_wallet_summary(wallet):
    cursor.execute("SELECT type, SUM(amount) FROM transactions WHERE wallet = ? GROUP BY type", (wallet,))
    return cursor.fetchall()

def add_wallet(name):
    try:
        cursor.execute("INSERT INTO wallets (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Уже существует

def delete_wallet(name):
    cursor.execute("DELETE FROM wallets WHERE name = ?", (name,))
    conn.commit()

def get_wallets():
    cursor.execute("SELECT name FROM wallets")
    return [row[0] for row in cursor.fetchall()]

def add_category(name, emoji, kind):
    try:
        cursor.execute("INSERT INTO categories (name, emoji, kind) VALUES (?, ?, ?)", (name, emoji, kind))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def delete_category(name):
    cursor.execute("DELETE FROM categories WHERE name = ?", (name,))
    conn.commit()

def get_categories(kind):
    cursor.execute("SELECT emoji, name FROM categories WHERE kind IN (?, 'both')", (kind,))
    return cursor.fetchall()

def set_reminder_time(time_):
    cursor.execute("UPDATE settings SET reminder_time = ? WHERE id=1", (time_,))
    conn.commit()

def set_pin(pin):
    cursor.execute("UPDATE settings SET pin = ? WHERE id=1", (pin,))
    conn.commit()

def get_pin():
    cursor.execute("SELECT pin FROM settings WHERE id=1")
    result = cursor.fetchone()
    return result[0] if result else None

def add_goal(description, target_amount, limit_category=None, limit_amount=None):
    cursor.execute("INSERT INTO goals (description, target_amount, current_amount, limit_category, limit_amount) VALUES (?, ?, 0, ?, ?)", (description, target_amount, limit_category, limit_amount))
    conn.commit()

def get_goals():
    cursor.execute("SELECT * FROM goals")
    return cursor.fetchall()