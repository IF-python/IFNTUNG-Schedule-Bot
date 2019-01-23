import os

import peewee
from playhouse.db_url import connect

import utils

database_proxy = peewee.Proxy()
db = connect(os.environ.get('DB_URL'))
database_proxy.initialize(db)


class BaseModel(peewee.Model):
    class Meta:
        database = database_proxy


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
    extend = peewee.BooleanField(default=False)
    notify = peewee.BooleanField(default=False)
    notify_time = peewee.TimeField(null=True)

    @classmethod
    def get_notify_time(cls, student_id):
        student, created = cls.get_student(student_id)
        return student.notify_time

    @classmethod
    def get_user_notify_status(cls, student_id):
        student, created = cls.get_student(student_id)
        return student.notify

    @classmethod
    def trigger_notify(cls, student_id):
        student, created = cls.get_student(student_id)
        student.notify = not student.notify
        student.save()
        return student.notify

    @classmethod
    def set_notify_time(cls, student_id, time):
        student, created = cls.get_student(student_id)
        student.notify_time = time
        student.save()

    @classmethod
    def at_time(cls, time):
        return cls.select().where((cls.notify_time == time) & cls.notify)

    @classmethod
    def get_student(cls, student_id):
        student, created = cls.get_or_create(student_id=student_id)
        if created:
            utils.track(str(student_id), 'New student')
        return student, created

    @classmethod
    def get_extend_flag(cls, user_id):
        student, created = cls.get_student(user_id)
        return student.extend

    @classmethod
    def reset_extended_flag(cls, user_id):
        student, created = cls.get_student(user_id)
        student.extend = not student.extend
        student.save()

    @classmethod
    def has_group(cls, student_id):
        student, created = cls.get_student(student_id)
        return getattr(student.group, 'group_code', None)

    @classmethod
    def set_group(cls, group_code, student_id):
        student, created = cls.get_student(student_id)
        student.group = Group.get_group_by_code(group_code)
        student.save()

    @classmethod
    def get_group_desc(cls, student_id):
        group = cls.has_group(student_id)
        return {'code': group, 'name': Group.get_group_full_name(group)}


db.create_tables([Group, Student], safe=True)
