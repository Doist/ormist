# -*- coding: utf-8 -*-
import pickle
import redis
from .utils import (timestamp_to_datetime, datetime_to_timestamp, random_string,
                    utcnow, random_true)
from .compat import xrange, b, u


#--- Systems related ----------------------------------------------

SYSTEMS = {
    'default': redis.Redis(host='localhost', port=6379)
}

def setup_redis(name, host=None, port=None, **kw):
    """
    Setup a redis system.

    :param name: The name of the system
    :param host: The host of the redis installation
    :param port: The port of the redis installation
    :param redis: It's a special keyword. If you don't want to use standard
                  :class:`redis.Redis` and have your own pre-configured
                  object, feel free to pass it as a "redis" parameter
    :param \*\*kw: Any additional keyword arguments to be passed to
                  :class:`redis.Redis`.

    Example::

        setup_redis('stats_redis', 'localhost', 6380)
        mark_event('active', 1, system='stats_redis')
    """
    redis_instance = kw.pop('redis', None)
    if not redis_instance:
        redis_instance = redis.Redis(host=host, port=port, **kw)
    SYSTEMS[name] = redis_instance


def get_redis(system='default'):
    """
    Get a redis-py client instance with entry `system`.

    :param :system The name of the system, extra systems can be setup via `setup_redis`
    """
    return SYSTEMS[system]



class ModelManager(object):
    # metaclass ModelBase ensures this object has "model_name", "id_length"
    # and "model" attribute,

    def _key(self, key, *args, **kwargs):
        key = u(key)
        prefix = 'ormist'
        model_name = self.model_name
        template = '{0}:{1}:{2}'.format(prefix, model_name, key)

        if args or kwargs:
            template = template.format(*args, **kwargs)
        return b(template)

    def full_cleanup(self, system='default'):
        key = self._key('*')
        keys = get_redis(system).keys(key)
        if keys:
            get_redis(system).delete(*keys)

    def get(self, _id, system='default'):
        _id = u(_id)
        if random_true(0.01):
            self.expire()
        key = self._key('object:{0}', _id)
        value = get_redis(system).get(key)
        if value:
            expire_key = self._key('object:{0}:expire', _id)
            expire_value = get_redis(system).get(expire_key)
            expire = timestamp_to_datetime(expire_value)
            if expire and expire < utcnow():
                return None
            attrs = pickle.loads(value)
            return self.model(_id, expire=expire, **attrs)

    def save_instance(self, instance, system='default'):
        if instance._id is None:
            instance._id = self.reserve_random_id(system=system)

        # object itself
        value = pickle.dumps(instance.attrs)

        pipe = get_redis(system).pipeline()
        pipe.sadd(self._key('__all__'), instance._id)
        pipe.set(self._key('object:{0}', instance._id), value)
        if instance.expire:
            expire_ts = datetime_to_timestamp(instance.expire)
            pipe.set(self._key('object:{0}:expire', instance._id), expire_ts)
            pipe.zadd(self._key('__expire__'), instance._id, expire_ts)
        pipe.execute()

    def delete_instance(self, instance, system='default'):
        self.delete_instance_by_id(instance._id, system=system)

    def delete_instance_by_id(self, instance_id, pipe=None, apply=True,
                              system='default'):
        instance_id = u(instance_id)
        all_key = self._key('__all__')
        expire_key = self._key('__expire__')
        key = self._key('object:{0}', instance_id)
        extra_keys = get_redis(system).keys(self._key('object:{0}:*', instance_id))
        if not pipe:
            pipe = get_redis(system).pipeline()
        pipe.srem(all_key, instance_id)
        pipe.zrem(expire_key, instance_id)
        pipe.delete(key, *extra_keys)
        if apply:
            pipe.execute()

    def expire(self, system='default'):
        expire_ts = datetime_to_timestamp(utcnow())
        expire_key = self._key('__expire__')
        remove_ids = get_redis(system).zrangebyscore(expire_key, 0, expire_ts)
        if remove_ids:
            pipe = get_redis(system).pipeline()
            for _id in remove_ids:
               self.delete_instance_by_id(_id, pipe=pipe, apply=False,
                                          system=system)
            pipe.execute()

    def reserve_random_id(self, max_attempts=10, system='default'):
        key = self._key('__all__')
        for _ in xrange(max_attempts):
            value = random_string(self.id_length)
            ret = get_redis(system).sadd(key, value)
            if ret != 0:
                return value
        raise RuntimeError('Unable to reserve random id for model "%s"' % self.model_name)

    def all(self, system='default'):
        all_key = self._key('__all__')
        ids = []
        if get_redis(system).exists(all_key):
            ids = get_redis(system).smembers(all_key)
        for _id in ids:
            instance = self.get(_id, system='default')
            if instance:
                yield instance




class TaggedModelManager(ModelManager):


    def save_instance(self, instance, system='default'):
        super(TaggedModelManager, self).save_instance(instance, system=system)
        if not instance.tags:
            return
        pipe = get_redis(system).pipeline()
        tags_key = self._key('object:{0}:tags', instance._id)
        pipe.sadd(tags_key, *instance.tags)
        for tag in instance.tags:
            key = self._key('tags:{0}', tag)
            pipe.sadd(key, instance._id)
        for tag_to_rm in set(instance._saved_tags) - set(instance.tags):
            key = self._key('tags:{0}', tag_to_rm)
            pipe.srem(key, instance._id)
        pipe.execute()
        instance._saved_tags = instance.tags

    def delete_instance(self, instance, system='default'):
        # we have to remove instance from all tags before removing the
        # object itself
        tags_keys = self._key('object:{0}:tags', u(instance._id))
        tags = get_redis(system).smembers(tags_keys)
        pipe = get_redis(system).pipeline()
        for tag in tags:
            key = self._key('tags:{0}', u(tag))
            pipe.srem(key, instance._id)
        self.delete_instance_by_id(instance._id, pipe=pipe, apply=False,
                                   system=system)
        pipe.execute()

    def get(self, _id, system='default'):
        instance = super(TaggedModelManager, self).get(_id, system=system)
        if instance:
            tags_key = self._key('object:{0}:tags', u(_id))
            tags = get_redis(system).smembers(u(tags_key)) or []
            instance.tags = [u(tag) for tag in tags]
        return instance

    def find_ids(self, *tags, **kw):
        system = kw.get('system', 'default')
        if not tags:
            return []
        keys = []
        for tag in tags:
            key = self._key('tags:{0}', tag)
            keys.append(u(key))
        return get_redis(system).sinter(*keys)

    def find(self, *tags, **kw):
        system = kw.get('system', 'default')
        ids = self.find_ids(system=system, *tags)
        for _id in ids:
            instance = self.get(_id, system=system)
            if instance:
                yield instance


class TaggedAttrsModelManager(TaggedModelManager):

    def __init__(self, exclude_attrs=None):
        self.exclude_attrs = set(exclude_attrs or [])

    def attrs_to_tags(self, attrs):
        tags = []
        for k, v in attrs.items():
            if k not in self.exclude_attrs:
                tags.append(u'{0}:{1}'.format(u(k), u(v)))
        return tags

    def find(self, **attrs):
        system = attrs.pop('system', 'default')
        tags = self.attrs_to_tags(attrs)
        for instance in super(TaggedAttrsModelManager, self).find(system=system, *tags):
            yield instance

