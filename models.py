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

    @classmethod
    def get_group_full_name(cls, group):
        return cls.select().where(cls.group_code == group).get().verbose_name


class Student(BaseModel):
    student_id = peewee.IntegerField()
    group = peewee.ForeignKeyField(Group, backref='students', null=True)

    @classmethod
    def has_group(cls, student_id):
        student, created = cls.get_or_create(student_id=student_id)
        return getattr(student.group, 'group_code', None)
