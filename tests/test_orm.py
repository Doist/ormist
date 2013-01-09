# -*- coding: utf-8 -*-
import datetime
import mock
import pytest
import ormist


ormist.setup_redis('default', 'localhost', 6379, db=0)
ormist.setup_redis('db1', 'localhost', 6379, db=1)


class User(ormist.Model):
    pass

class Book(ormist.TaggedModel):
    pass

class User2(ormist.Model):
    # the same user, but stored in the db1
    system = 'db1'
    model_name = 'user'

class TaggedUser(ormist.TaggedAttrsModel):
    objects = ormist.TaggedAttrsModelManager(['name', ])


def setup_function(function):
    User.objects.full_cleanup()
    Book.objects.full_cleanup()
    TaggedUser.objects.full_cleanup()
    User2.objects.full_cleanup()


def teardown_function(function):
    User.objects.full_cleanup()
    Book.objects.full_cleanup()
    TaggedUser.objects.full_cleanup()
    User2.objects.full_cleanup()


def pytest_funcarg__user(request):
    user = User(1234, name='John Doe', age=30)
    user.save()
    request.addfinalizer(user.delete)
    return user


def pytest_funcarg__user_db1(request):
    user = User(1234, name='John Doe', age=30)
    user.save('db1')
    request.addfinalizer(lambda: user.delete(system='db1'))
    return user

def pytest_funcarg__user2(request):
    user = User2(1234, name='John Doe', age=30)
    user.save()
    request.addfinalizer(lambda: user.delete())
    return user

def pytest_funcarg__book(request):
    tags = ['foo', 'bar']
    book = Book(1234, tags=tags, title='How to Foo and Bar')
    book.save()
    request.addfinalizer(book.delete)
    return book


def pytest_funcarg__tagged_user(request):
    user = TaggedUser(1234, name='John Doe', age=30)
    user.save()
    request.addfinalizer(user.delete)
    return user


def pytest_funcarg__tags(request):
    return ['foo', 'bar']


#--- Basic functionality of models

def test_save_and_get(user):
    same_user = User.objects.get(1234)
    assert same_user.name == 'John Doe'
    assert same_user.age == 30


def test_manager_create():
    user = User.objects.create(name='John Doe', age=30)
    same_user = User.objects.get(user._id)
    assert same_user.name == 'John Doe'
    assert same_user.age == 30


def test_get_none():
    assert User.objects.get(1234) is None


def test_update(user):
    user.set(name='Just Joe', gender='male')
    user.unset('age')
    user.save()
    same_user = User.objects.get(1234)
    assert same_user.name == 'Just Joe'
    assert same_user.gender == 'male'
    with pytest.raises(AttributeError):
        same_user.age


def test_get_all(user):
    users = list(User.objects.all())
    assert users == [user, ]


def test_delete(user):
    user.delete()
    user_count = len(list(User.objects.all()))
    assert user_count == 0


#--- Test for tagged models

def test_delete_objects_cleans_up_tags(book, tags):
    book.delete()
    assert len(Book.objects.find_ids(tags[0])) == 0
    assert len(Book.objects.find_ids(tags[1])) == 0


def test_tags_save_delete(book, tags):
    same_book = Book.objects.get(book._id)
    assert set(same_book.tags) == set(tags)


def test_tags_find(book, tags):
    books = list(Book.objects.find('foo'))
    assert books == [book, ]
    books = list(Book.objects.find('bar'))
    assert books == [book, ]
    books = list(Book.objects.find('foo', 'bar'))
    assert books == [book, ]


def test_tags_remove(book, tags):
    book.tags = ['foo', ]  # we removed the tag "bar"
    book.save()
    books = list(Book.objects.find('bar'))
    assert books == []
    books = list(Book.objects.find('foo'))
    assert books == [book, ]

#--- Test for tagged attrs models


def test_tagged_attrs_find(tagged_user):
    users = list(TaggedUser.objects.find(age=30))
    assert users == [tagged_user, ]
    assert set(users[0].tags) == set(tagged_user.tags)


def test_exclude_tags(tagged_user):
    """
    test that TaggedUser._exclude_attrs works

    We don't tags for attributes, whose names are listed in _exclude_attrs
    property of the model
    """
    users = list(TaggedUser.objects.find(name='John Doe'))
    assert users == []


def test_delete_tagged_model_removes_tags():
    user = TaggedUser(age=20, name='John Doe')
    user.save()
    user.delete()
    users = list(TaggedUser.objects.find(age=20))
    assert users == []

#--- Test objects with no id

def test_auto_id():
    user = User(name='Foo bar')
    assert user._id is None
    user.save()
    assert user._id is not None
    user.delete()

def test_auto_id_failed_random():
    with mock.patch('ormist.managers.random_string') as random_string:
        random_string.return_value = '1234'
        user = User(name='Foo bar')
        user.save()
        with pytest.raises(RuntimeError):
            User(name='Foo bar').save()
        user.delete()

#--- Test expire

def test_expire_saves_attribute(user):
    with mock.patch('ormist.utils.utcnow') as utcnow:
        utcnow.return_value = datetime.datetime(2012, 1, 1)
        user.set_expire(datetime.timedelta(days=10))
    user.save()
    with mock.patch('ormist.managers.utcnow') as utcnow:
        utcnow.return_value = datetime.datetime(2012, 1, 1)
        same_user = User.objects.get(user._id)
    assert same_user.expire == datetime.datetime(2012, 1, 11)


def test_expire_removes_object_do_expire(user):
    user.set_expire(0)  # expire in 0 seconds
    user.save()
    with mock.patch('ormist.managers.random_true') as random_true:
        random_true.return_value = True
        assert User.objects.get(user._id) is None
        assert list(User.objects.all()) == []


def test_expire_removes_object_do_not_expire(user):
    user.set_expire(0)  # expire in 0 seconds
    user.save()
    with mock.patch('ormist.managers.random_true') as random_true:
        random_true.return_value = False
        assert User.objects.get(user._id) is None
        assert list(User.objects.all()) == []


def test_ttl(user):
    assert user.ttl() is None
    user.set_expire(10)
    assert user.ttl() > 0
    user.set_expire(datetime.datetime(2012, 1, 1)) # in the past
    assert user.ttl() == 0


def test_different_systems(user_db1):
    # nothing is saved in default db
    assert User.objects.get(user_db1._id) is None
    # the record is in the 1st database
    assert User.objects.get(user_db1._id, system='db1') == user_db1

def test_automatic_system_choice(user2):
    # we can get saved user from the correct system in different manners
    assert User2.objects.get(user2._id) == user2
    assert User2.objects.get(user2._id, system='db1') == user2
    assert User2.objects.get(user2._id, system='default') == None
