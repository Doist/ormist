# -*- coding: utf-8 -*-
import pickle
from .utils import (timestamp_to_datetime, datetime_to_timestamp, random_string,
                    utcnow, random_true)

#--- ORM object
class ORM(object):
    pass

orm = ORM()

def configure(redis, prefix):
    """
    configure the ORM
    """
    orm.redis = redis
    orm.prefix = prefix



class ModelManager(object):
    # metaclass ModelBase ensures this object has "model_name", "id_length"
    # and "model" attribute,

    def _key(self, key, *args, **kwargs):
        prefix = orm.prefix
        model_name = self.model_name
        if prefix:
            template = '{0}:{1}:{2}'.format(prefix, model_name, key)
        else:
            template = '{0}:{1}'.format(model_name, key)

        if args or kwargs:
            template = template.format(*args, **kwargs)
        return template

    def full_cleanup(self):
        key = self._key('*')
        keys = orm.redis.keys(key)
        if keys:
            orm.redis.delete(*keys)

    def get(self, _id):
        if random_true(0.01):
            self.expire()
        key = self._key('object:{0}', _id)
        value = orm.redis.get(key)
        if value:
            expire_key = self._key('object:{0}:expire', _id)
            expire_value = orm.redis.get(expire_key)
            expire = timestamp_to_datetime(expire_value)
            if expire and expire < utcnow():
                return None
            attrs = pickle.loads(value)
            return self.model(_id, expire=expire, **attrs)

    def save_instance(self, instance):
        if instance._id is None:
            instance._id = self.reserve_random_id()

        # object itself
        value = pickle.dumps(instance.attrs)

        pipe = orm.redis.pipeline()
        pipe.sadd(self._key('__all__'), instance._id)
        pipe.set(self._key('object:{0}', instance._id), value)
        if instance.expire:
            expire_ts = datetime_to_timestamp(instance.expire)
            pipe.set(self._key('object:{0}:expire', instance._id), expire_ts)
            pipe.zadd(self._key('__expire__'), instance._id, expire_ts)
        pipe.execute()

    def delete_instance(self, instance):
        self.delete_instance_by_id(instance._id)

    def delete_instance_by_id(self, instance_id, pipe=None, apply=True):
        all_key = self._key('__all__')
        expire_key = self._key('__expire__')
        key = self._key('object:{0}', instance_id)
        extra_keys = orm.redis.keys(self._key('object:{0}:*', instance_id))
        if not pipe:
            pipe = orm.redis.pipeline()
        pipe.srem(all_key, instance_id)
        pipe.zrem(expire_key, instance_id)
        pipe.delete(key, *extra_keys)
        if apply:
            pipe.execute()

    def expire(self):
        expire_ts = datetime_to_timestamp(utcnow())
        expire_key = self._key('__expire__')
        remove_ids = orm.redis.zrangebyscore(expire_key, 0, expire_ts)
        if remove_ids:
            pipe = orm.redis.pipeline()
            for _id in remove_ids:
               self.delete_instance_by_id(_id, pipe=pipe, apply=False)
            pipe.execute()

    def reserve_random_id(self, max_attempts=10):
        key = self._key('__all__')
        for _ in xrange(max_attempts):
            value = random_string(self.id_length)
            ret = orm.redis.sadd(key, value)
            if ret != 0:
                return value
        raise RuntimeError('Unable to reserve random id for model "%s"' % self.model_name)

    def all(self):
        all_key = self._key('__all__')
        ids = []
        if orm.redis.exists(all_key):
            ids = orm.redis.smembers(all_key)
        for _id in ids:
            instance = self.get(_id)
            if instance:
                yield instance




class TaggedModelManager(ModelManager):


    def save_instance(self, instance):
        super(TaggedModelManager, self).save_instance(instance)
        if not instance.tags:
            return
        pipe = orm.redis.pipeline()
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

    def delete_instance(self, instance):
        # we have to remove instance from all tags before removing the
        # object itself
        tags_keys = self._key('object:{0}:tags', instance._id)
        tags = orm.redis.smembers(tags_keys)
        pipe = orm.redis.pipeline()
        for tag in tags:
            key = self._key('tags:{0}', tag)
            pipe.srem(key, instance._id)
        self.delete_instance_by_id(instance._id, pipe=pipe, apply=False)
        pipe.execute()

    def get(self, _id):
        instance = super(TaggedModelManager, self).get(_id)
        if instance:
            tags_key = self._key('object:{0}:tags', _id)
            tags = orm.redis.smembers(tags_key) or []
            instance.tags = tags
        return instance

    def find_ids(self, *tags):
        if not tags:
            return []
        keys = []
        for tag in tags:
            key = self._key('tags:{0}', tag)
            keys.append(key)
        return orm.redis.sinter(*keys)

    def find(self, *tags):
        ids = self.find_ids(*tags)
        for _id in ids:
            instance = self.get(_id)
            if instance:
                yield instance


class TaggedAttrsModelManager(TaggedModelManager):

    def __init__(self, exclude_attrs=None):
        self.exclude_attrs = set(exclude_attrs or [])

    def attrs_to_tags(self, attrs):
        tags = []
        for k, v in attrs.iteritems():
            if k not in self.exclude_attrs:
                tags.append(u'{0}:{1}'.format(unicode(k), unicode(v)))
        return tags

    def find(self, **attrs):
        tags = self.attrs_to_tags(attrs)
        for instance in super(TaggedAttrsModelManager, self).find(*tags):
            yield instance

