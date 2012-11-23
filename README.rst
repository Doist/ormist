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
