import peewee

db = peewee.SqliteDatabase('TempDB.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Group(BaseModel):
    group_code = peewee.TextField()
    verbose_name = peewee.TextField()

    @classmethod
    def get_all_groups(cls):
        return [x.group_code for x in cls.select()]


class Student(BaseModel):
    student_id = peewee.IntegerField()
    group = peewee.ForeignKeyField(Group, backref='students', null=True)

    @classmethod
    def student_exists(cls, student_id):
        query = cls.select().where(student_id=student_id)
        return query.exists()

# db.create_tables([Group, Student])
