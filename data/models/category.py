# models/category.py
from tortoise.models import Model
from tortoise.fields import IntField, CharField, BooleanField, ForeignKeyField

class Category(Model):
    id = IntField(pk=True)
    name = CharField(max_length=100)
    type = CharField(max_length=10)  # 'expense' или 'income'
    deleted = BooleanField(default=False)  # Флаг удаления
    user = ForeignKeyField('models.User', related_name='categories')  # Привязка к пользователю (многопользовательский)

    class Meta:
        table = "categories"