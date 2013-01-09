ormist: yet another Object-to-Redis mapper. Lightweight. Schema-agnostic.
=========================================================================

**ormist** is a object-to-redis mapper: the library helping you to work with
persistent objects and object collections using Redis as a back-end store.

.. image:: https://secure.travis-ci.org/Doist/ormist.png?branch=master
   :alt: Build Status
   :target: https://secure.travis-ci.org/Doist/ormist

Library Features
----------------

- Lightweight: the code is small, model and collection methods strive to work
  the most natural to Redis way.
- Schema agnostic: models don't impose any schema, they are here just to help
  you to arrange instances into collections.
- Tag support: mark models with tags to retrieve subset of collections
  effectively.
- Expiration support: create any model with `expire` argument to ensure it will
  be destroyed in that period of time.
- Familiar: API mimics the same of Django in many ways.

Usage samples
-------------

No boilerplate code or configuration if your Redis listens ``localhost:6379``.

**Example 1.** How to work with sessions.

.. code-block:: python

    >>> class Session(ormist.Verbose, ormist.Model): pass
    >>> sess = Session.objects.create(remote_addr='127.0.0.1', user_id=1)
    <Session id:oprS4JI7jQZf01a3 attrs:{'user_id': 1, 'remote_addr': '127.0.0.1'}>
    >>> sess2 = Session.objects.get('oprS4JI7jQZf01a3')
    >>> sess2.remote_addr
    '127.0.0.1'
    >>> sess2.user_id
    1

**Example 2.** How to work with searchable tags.

.. code-block:: python

    >>> class TodoItem(ormist.Verbose, ormist.TaggedModel): pass
    >>> TodoItem.objects.create('project1', 'project2', text='project1 and project2')
    >>> TodoItem.objects.create('project2', 'project3', text='project2 and project3')
    >>> TodoItem.objects.find('project1').list()
    [<TodoItem id:QCh5rprrmo5AjcpG attrs:{'text': 'project1 and project2'}>]
    >>> TodoItem.objects.find('project2').list()
    [<TodoItem id:YmyUvYSVWW9jqfTz attrs:{'text': 'project2 and project3'}>,
     <TodoItem id:QCh5rprrmo5AjcpG attrs:{'text': 'project1 and project2'}>]
    >>> TodoItem.objects.find('project2', 'project3').list()
    >>> [<TodoItem id:YmyUvYSVWW9jqfTz attrs:{'text': 'project2 and project3'}>]
    >>>TodoItem.objects.find('project4').list()
    []

**Example 3.** How to work with searchable attributes.

.. code-block:: python

    >>> User.objects.create(name='John', age=30, department_id=1)
    >>> User.objects.create(name='Mary', age=25, department_id=1)

    # find by name
    >>> User.objects.find(name='John').list()
    [<User id:lu8uFHOuKYhvHX09 attrs:{'department_id': 1, 'age': 30, 'name': 'John'}>]

    # find by department
    >>> User.objects.find(department_id=1).list()
    [<User id:lu8uFHOuKYhvHX09 attrs:{'department_id': 1, 'age': 30, 'name': 'John'}>,
     <User id:OuS5PuV3ufO3nXuR attrs:{'department_id': 1, 'age': 25, 'name': 'Mary'}>]

    # find by name and department
    User.objects.find(name='Mary', department_id=1).list()
    [<User id:OuS5PuV3ufO3nXuR attrs:{'department_id': 1, 'age': 25, 'name': 'Mary'}>]

    # How it actually works: we just build tags on the fly
    >>> john = User.objects.find(name='John')[0]
    >>> john.tags
    [u'department_id:1', u'name:John', u'age:30']
