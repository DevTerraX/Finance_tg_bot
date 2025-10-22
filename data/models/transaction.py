from tortoise.models import Model
from tortoise.fields import (
    IntField,
    FloatField,
    CharField,
    DatetimeField,
    ForeignKeyField,
    TextField
)

class Transaction(Model):
    id = IntField(pk=True)
    amount = FloatField()
    category = ForeignKeyField('models.Category', related_name='transactions', null=True)
    category_name = CharField(max_length=100, null=True)
    type = CharField(max_length=10)
    date = DatetimeField(auto_now_add=True)
    check = TextField(null=True)
    check_photo_path = CharField(max_length=255, null=True)
    user = ForeignKeyField('models.User', related_name='transactions')

    class Meta:
        table = "transactions"
