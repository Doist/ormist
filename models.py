# -*- coding: utf-8 -*-
import re
from .managers import ModelManager, TaggedModelManager, TaggedAttrsModelManager
from .utils import expire_to_datetime

#--- Metaclass magic

class ModelBase(type):
    """
    Metaclass for Model and its subclasses

    Used to set up a manager for model. Class constructor searches
    for model_manager instance and adds the reference to
    """
    def __new__(cls, name, parents, attrs):
        model_manager = attrs.pop('objects', None)
        if not model_manager:
            parent_mgrs = filter(None, [getattr(p, 'objects', None) for p in parents])
            mgr_class = parent_mgrs[0].__class__
            model_manager = mgr_class()
        attrs['objects'] = model_manager
        model_manager.model_name = attrs.pop('model_name', to_underscore(name))
        model_manager.id_length = attrs.pop('id_length', 16)
        ret = type.__new__(cls, name, parents, attrs)
        model_manager.model = ret
        return ret

def to_underscore(name):
    """
    Helper function converting CamelCase to underscore: camel_case
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()



class Model(object):
    """
    Base model class
    """
    __metaclass__ = ModelBase
    objects = ModelManager()


    def __init__(self, _id=None, expire=None, **attrs):
        if _id is not None:
            _id = str(_id)
        self._id = _id
        self.attrs = attrs
        self.expire = expire_to_datetime(expire)

    def __getattr__(self, attr):
        try:
            return self.attrs[attr]
        except KeyError as e:
            raise AttributeError(e)

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return self._id == other._id

    def __repr__(self):
        return '<%s id:%s>' % (self.__class__.__name__, self._id)

    def set_expire(self, expire):
        self.expire = expire_to_datetime(expire)

    def save(self):
        self.objects.save_instance(self)

    def delete(self):
        self.objects.delete_instance(self)

    def set(self, **kwargs):
        self.attrs.update(**kwargs)

    def unset(self, *args):
        for arg in args:
            self.attrs.pop(arg, None)




class TaggedModel(Model):
    """
    Model with tags support
    """

    objects = TaggedModelManager()

    def __init__(self, _id=None, tags=None, **kwargs):
        super(TaggedModel, self).__init__(_id, **kwargs)
        self.tags = tags or []
        self._saved_tags = self.tags

class TaggedAttrsModel(TaggedModel):

    objects = TaggedAttrsModelManager(exclude_attrs=[])

    def __init__(self, _id=None, **attrs):
        tags = self.objects.attrs_to_tags(attrs)
        super(TaggedAttrsModel, self).__init__(_id, tags, **attrs)

    def set(self, **kwargs):
        super(TaggedAttrsModel, self).set(**kwargs)
        self.tags = self.objects.attrs_to_tags(self.attrs)

    def unset(self, *args):
        super(TaggedAttrsModel, self).unset(*args)
        self.tags = self.objects.attrs_to_tags(self.attrs)
