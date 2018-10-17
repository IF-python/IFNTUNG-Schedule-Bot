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
    def get_group(cls, group_code):
        return cls.select().where(cls.group_code == group_code).get()

    @classmethod
    def get_group_full_name(cls, group):
        return cls.get_group(group).verbose_name

    @classmethod
    def get_group_by_code(cls, group_code):
        return cls.get_group(group_code)


class Student(BaseModel):
    student_id = peewee.IntegerField()
    group = peewee.ForeignKeyField(Group, backref='students', null=True)

    @classmethod
    def has_group(cls, student_id):
        student, created = cls.get_or_create(student_id=student_id)
        return getattr(student.group, 'group_code', None)

    @classmethod
    def set_group(cls, group_code, student_id):
        student, created = cls.get_or_create(student_id=student_id)
        student.group = Group.get_group_by_code(group_code)
        student.save()

    @classmethod
    def get_group_desc(cls, student_id):
        group = cls.has_group(student_id)
        if group:
            return {'code': group, 'name': Group.get_group_full_name(group)}
