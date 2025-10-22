from tortoise.models import Model
from tortoise.fields import IntField, CharField, BooleanField, ForeignKeyField

class Category(Model):
    id = IntField(pk=True)
    name = CharField(max_length=100)
    type = CharField(max_length=10)
    deleted = BooleanField(default=False)
    user = ForeignKeyField('models.User', related_name='categories')

    class Meta:
        table = "categories"
