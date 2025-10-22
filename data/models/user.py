from tortoise.models import Model
from tortoise.fields import (
    IntField,
    BooleanField,
    FloatField,
    CharField,
    DatetimeField
)

class User(Model):
    id = IntField(pk=True)
    agreement_accepted = BooleanField(default=False)
    clean_chat = BooleanField(default=True)
    balance = FloatField(default=0.0)
    name = CharField(max_length=255, default='')
    currency = CharField(max_length=8, default='₽')
    timezone = CharField(max_length=64, default='Europe/Moscow')
    date_format = CharField(max_length=32, default='DD.MM.YYYY')
    daily_reminder_enabled = BooleanField(default=False)
    reminder_time = CharField(max_length=5, default='20:00')
    created_at = DatetimeField(auto_now_add=True)
    last_reminder_sent = DatetimeField(null=True)

    class Meta:
        table = "users"
