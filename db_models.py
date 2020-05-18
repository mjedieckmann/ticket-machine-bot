from peewee import *

database = MySQLDatabase('nli', **{'charset': 'utf8', 'sql_mode': 'PIPES_AS_CONCAT', 'use_unicode': True, 'user': 'root', 'password': 'mysql'})

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class ConfirmFrame(BaseModel):
    frame = CharField(null=True)
    id_confirm_frame = AutoField(column_name='idConfirmFrame')
    target = CharField(null=True)

    class Meta:
        table_name = 'ConfirmFrame'

class Discount(BaseModel):
    discount = DecimalField(null=True)
    id_discount = AutoField(column_name='idDiscount')
    name = CharField(null=True)
    synonym = CharField(null=True)

    class Meta:
        table_name = 'Discount'

class InformFrame(BaseModel):
    attribute = CharField(null=True)
    frame = CharField(null=True)
    id_inform_frame = AutoField(column_name='idInformFrame')
    target = CharField(null=True)
    verb = CharField()

    class Meta:
        table_name = 'InformFrame'

class SemanticFrame(BaseModel):
    id_semantic_frame = AutoField(column_name='idSemanticFrame')
    name = CharField()
    theme = CharField(null=True)

    class Meta:
        table_name = 'SemanticFrame'

class Phrase(BaseModel):
    frame = ForeignKeyField(column_name='frame', field='id_semantic_frame', model=SemanticFrame)
    id_phrase = AutoField(column_name='idPhrase')
    phrase = CharField()

    class Meta:
        table_name = 'Phrase'

class QueryFrame(BaseModel):
    frame = CharField(null=True)
    id_query_frame = AutoField(column_name='idQueryFrame')
    query_type = CharField(column_name='queryType', null=True)
    target = CharField(null=True)
    verb = CharField()

    class Meta:
        table_name = 'QueryFrame'

class Slot(BaseModel):
    id_slot = AutoField(column_name='idSlot')
    isfilled = CharField(constraints=[SQL("DEFAULT '0'")], null=True)
    name = CharField(null=True, unique=True)

    class Meta:
        table_name = 'Slot'

class Ticket(BaseModel):
    id_ticket = AutoField(column_name='idTicket')
    name = CharField()
    price = DecimalField(null=True)
    synonym = CharField(null=True)

    class Meta:
        table_name = 'Ticket'

class Zone(BaseModel):
    id_zone = AutoField(column_name='idZone')
    increase = DecimalField(null=True)
    name = CharField(unique=True)

    class Meta:
        table_name = 'Zone'

class TicketPrice(BaseModel):
    id_ticket_price = AutoField(column_name='idTicketPrice')
    price = DecimalField()
    ticket = ForeignKeyField(column_name='ticket', field='id_ticket', model=Ticket)
    zone = ForeignKeyField(column_name='zone', field='id_zone', model=Zone)

    class Meta:
        table_name = 'TicketPrice'

