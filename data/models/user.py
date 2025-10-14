from tortoise.models import Model
from tortoise.fields import IntField, BooleanField, FloatField

class User(Model):
    id = IntField(pk=True)  # Telegram ID как primary key
    agreement_accepted = BooleanField(default=False)  # Согласие с политикой
    clean_chat = BooleanField(default=True)  # Очистка чата на каждом шаге (по выбору)
    balance = FloatField(default=0.0)  # Текущий баланс (обновляем при транзакциях)

    class Meta:
        table = "users"