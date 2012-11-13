# -*- coding: utf-8 -*-
"""
ORM -- object-to-redis mapper

.. code-block:: python

    from oauthist import orm

    r = redis.Redis()
    orm.configure(r, prefix='foo')

    class User(orm.Model):
        pass

    user = User(1234, name='John Doe', age=30)
    user.save()
    # created two records
    # foo:user:__all__ with set (1234)
    # foo:user:object:1234 with {name: 'John Doe', 'age': 30}

    user = User.get(1234)
    # returns the same user object as it was

    user.unset('age')
    user.set(name='Just John', gender='male')
    user.save()
    # alters the same object by removing "age", adding "gender" and changing "name" fields

    users = User.objects.all()
    # return all users we have


    class Book(orm.TaggedModel):
        pass

    book = Book(1234, tags=['compsci', 'python', 'programming'], title='Dive into Python')
    book.save()
    # creates the record
    # foo:book:__all__ with set (1234)
    # foo:book:object:1234 with {title: 'Dive into python'}
    # foo:book:object:1234:tags with set (compsci, python, programming)
    # foo:book:tags:compsci with set (1234)
    # foo:book:tags:python with set (1234)
    # foo:book:tags:programming with set (1234)

    books = Book.filter(tags=['compsci', 'python'])
    # this addtional method returns the list of one item

    class User2(orm.TaggedAttrsModel):
        pass

    # this is a shortcut, which just adds a tag to every attribute you write
    # in the database

"""
from .managers import *
from .models import *
from .utils import *
