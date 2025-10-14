# models/transaction.py
from tortoise.models import Model
from tortoise.fields import IntField, FloatField, CharField, DatetimeField, ForeignKeyField, TextField

class Transaction(Model):
    id = IntField(pk=True)
    amount = FloatField()
    category = ForeignKeyField('models.Category', related_name='transactions', null=True)  # Null если категория удалена
    category_name = CharField(max_length=100, null=True)  # Кэш имени на случай удаления
    type = CharField(max_length=10)  # 'expense' или 'income'
    date = DatetimeField(auto_now_add=True)
    check = TextField(null=True)  # Текст чека или URL фото (для расходов)
    user = ForeignKeyField('models.User', related_name='transactions')

    class Meta:
        table = "transactions"