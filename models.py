import peewee

db = peewee.SqliteDatabase('TempDB.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Group(BaseModel):
    group_code = peewee.TextField()
    verbose_name = peewee.TextField()


class Student(BaseModel):
    student_id = peewee.IntegerField()
    group = peewee.ForeignKeyField(Group, backref='students')
