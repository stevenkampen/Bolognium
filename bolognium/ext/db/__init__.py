#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging, sys
import bolognium
from google.appengine.ext import ndb
from google.appengine.ext.ndb.model import put_multi_async, put_multi, Rollback, Key, get_multi, get_multi_async

from google.appengine.api import memcache
from google.appengine.api import datastore_errors
from google.appengine.runtime import apiproxy_errors
from google.appengine.ext import deferred
from google.appengine.api.labs import taskqueue

import filters
from filters import FilterError

import os, sys, decimal, datetime, hashlib, time, random, string, inspect

model_dict = {}

def setup_models():
  """The list containing models that failed to load initially"""
  _delayed_load = []
  _retry_counts = {}
  """Models that were successfully loaded"""
  _loaded = []

  """This method handles the actual importing and screwing around"""
  def load(model_name):
    """Count it"""
    if not _retry_counts.get(model_name, None):
      _retry_counts[model_name] = 0
    _retry_counts[model_name] += 1

    try:
      """Try to import the module"""
      module = __import__(u'model.%s' % model_name, \
          globals(), locals(), [''], -1)

      """Capitalize the name (u'some_model' >>> u'SomeModel'). """
      model_name = bolognium.ext.utils.camel_case(model_name)

      """Get the actual model class from the module"""
      try:
        _model = module.__dict__[model_name]
      except KeyError:
        raise Exception(u'Class \'%s\' did not exist in model file: %s.py.' 
          % (model_name, module.__name__))

    except Exception, e:
      """ImportError. Should Not Raise"""
      logging.warn(u'Model \'%s\' raised %s Exception. MSG \'%s\'. Retries: %d.' 
        % (model_name, e.__class__.__name__, e, _retry_counts[model_name]))
      if _retry_counts[model_name] > 10:
        raise

    else:
      """Success"""
      _loaded.append(model_name)
      try:
        _x = globals()[model_name]
      except KeyError:
        globals()[model_name] = globals()[u'model_dict'][model_name] = _model
        #must return True if loads
        return True
    #else returns False
    return False

  """get all model names by listing the models directory
  and checking names against some basic conditions. If a model
  fails to load due to dependancies, add to a list to load later.
  """
  for filename in os.listdir('model'):
    module = None
    model_name = None
    if not filename.startswith("_"):
      if filename.endswith(".py"):
        model_name = filename[:-3]
        if model_name and model_name not in _loaded:
          if not load(model_name):
            _delayed_load.append(model_name)
            

  """Some models couldn't load because of dependencies so 
  iterate over the list until they're all done."""
  while len(_delayed_load):
    for index,item in enumerate(_delayed_load):
      if load(item) == True:
        #loaded. delete from list
        del _delayed_load[index]

class Property(ndb.model.Property):
  _whitelisted = False
  def __init__(self, whitelisted=False, *args, **kwargs):

    """Indicates if visible in client side output."""
    self._whitelisted = whitelisted

    super(Property, self).__init__(*args, **kwargs)

class UserProperty(Property, ndb.model.UserProperty):
  pass

class GeoPtProperty(Property, ndb.model.GeoPtProperty):
  pass

class GenericProperty(Property, ndb.model.GenericProperty):
  pass

class LocalStructuredProperty(Property, ndb.model.LocalStructuredProperty):
  def _get_for_client_side(self, instance=None, **kwargs):
    val = self._get_value(entity=instance)
    if val:
      try:
        val = val.to_client_side()
      except Exception, e:
        val = None
    return val

class StructuredProperty(Property, ndb.model.StructuredProperty):
  def _get_for_client_side(self, instance=None, **kwargs):
    val = self._get_value(entity=instance)
    if val:
      try:
        val = val.to_client_side()
      except Exception, e:
        val = None
    return val

  def _validate(self, value):
    #return value
    return super(StructuredProperty, self)._validate(value)

class ComputedProperty(Property, ndb.model.ComputedProperty):
  pass

class KeyProperty(Property, ndb.model.KeyProperty):
  def _get_for_client_side(self, instance=None, recursion_level=1, **kwargs):
    val = self._get_value(entity=instance)
    if val:
      if recursion_level > 0:
        try:
          val = val.get()
          val = val.to_client_side(recursion_level=recursion_level-1)
        except Exception, e:
          val = None
      else:
          val = val.id()
    return val

class BlobKeyProperty(Property, ndb.model.BlobKeyProperty):
  def _get_for_client_side(self, instance=None, recursion_level=1, **kwargs):
    val = self._get_value(entity=instance)
    return str(val)

class TextProperty(Property, ndb.model.TextProperty):
  pass

class PostBodyProperty(TextProperty):
  pass

class JsonProperty(TextProperty):
  def _get_for_client_side(self, instance=None, **kwargs):
    val = bolognium.ext.utils.json.loads(val)
    return self.get_loaded_data(self, instance)

  def get_loaded_data(self, instance):
    val = self._get_value(entity=instance)
    val = bolognium.ext.utils.json.loads(val)
    return val

class StringProperty(Property, ndb.model.StringProperty):
  pass

class UnderscoredSlugProperty(StringProperty):
  pass

class SlugProperty(StringProperty):
  pass

class NameProperty(Property, ndb.model.StringProperty):
  pass

class CountryCodeProperty(StringProperty):
  pass

class UINameProperty(StringProperty):
  pass

class EmailProperty(StringProperty):
  pass

class PhoneNumberProperty(StringProperty):
  pass

class DomainNameProperty(StringProperty):
  pass

class LinkProperty(TextProperty):
  pass

class IntegerProperty(Property, ndb.model.IntegerProperty):
  pass

class BooleanProperty(Property, ndb.model.BooleanProperty):
  pass

class EnabledProperty(BooleanProperty):
  def __init__(self, default=False, *args, **kwargs):
    super(EnabledProperty, self).__init__(default=default, *args, **kwargs)

class BlobProperty(Property, ndb.model.BlobProperty):
  pass

class TimeProperty(Property, ndb.model.TimeProperty):
  pass

class DateProperty(Property, ndb.model.DateProperty):
  pass

class DateTimeProperty(Property, ndb.model.DateTimeProperty):
  def _get_for_client_side(self, instance, *kwargs):
    val = self._get_value(entity=instance)
    if val:
      return val.isoformat()
    return val

class CreatedDateTimeProperty(DateTimeProperty):
  def __init__(self, whitelisted=True, auto_now_add=True, *args, **kwargs):
    super(CreatedDateTimeProperty, self).__init__(whitelisted=True, 
        auto_now_add=auto_now_add, *args, **kwargs)

class UpdatedDateTimeProperty(DateTimeProperty):
  def __init__(self, whitelisted=True, auto_now=True, *args, **kwargs):
    super(UpdatedDateTimeProperty, self).__init__(whitelisted=True, 
        auto_now=auto_now, *args, **kwargs)

class DecimalProperty(Property):

  """A Property whose value is a Decimal object."""
  multiple = 1000000.0

  def _validate(self, value):
    if not isinstance(value, (int, long, float, decimal.Decimal)):
      raise datastore_errors.BadValueError('Bad Type for decimal. Got '
          '\'%s\'. Type: \'%s\'' % (value, type(value)))
    return decimal.Decimal(str(value))

  def _db_set_value(self, v, p, value):
    assert isinstance(value, (int, long, float, decimal.Decimal)), (self._name)
    v.set_int64value(int(float(value) * self.multiple))

  def _db_get_value(self, v, p):
    if not v.has_int64value():
      return None
    return decimal.Decimal(str(v.int64value()/self.multiple))

  def _get_for_client_side(self, instance, *kwargs):
    return str(self._get_value(entity=instance))

"""
This is the base model for both BaseDatastoreModel and BaseStructuredmodel.
"""
class BaseModel(object):
  """Filters model instances for client side representation."""
  def to_client_side(self, **kwargs):
    obj = {}
    val = None
    for prop_name,prop_instance in self.all_properties().iteritems():
      if prop_instance._whitelisted == True:
        if hasattr(prop_instance, u'_get_for_client_side'):
          obj[prop_name] = prop_instance._get_for_client_side(
              instance=self, **kwargs)
        else:
          obj[prop_name] = getattr(self, prop_name, None)
    try:
      """If the thing has an id, include it?"""
      obj['id'] = self.key.id()
    except:
      pass
    return obj

  @classmethod
  def filter_property(cls, property_name, value, context={}, ctx_opts={}):
    filter_method = getattr(cls, u'_filter_%s' % property_name, None)
    if filter_method:
      return filter_method(value, context, ctx_opts)
    else:
      return filters.base_filter.process(value, context, ctx_opts)
    
  @classmethod
  def is_DS(cls):
    if issubclass(cls, BaseDatastoreModel):
      return True
    return False
    
  def has_complete_key(self):
    return self._has_complete_key()

  def _get_property_instance_or_raise_error(self, name):
    prop = self.get_property_instance(name)
    if not prop:
      #change to raise more specific error.
      raise AssertionError('Invalid prop name: %s' % name)
    return prop

  def get_property_value(self, name, index=None, value_filter=None):
    """Handles getting the value of a property on an instance."""
    prop = self._get_property_instance_or_raise_error(name)
    if prop._repeated == True: 
      #forward to 'repeated' property getter.
      return self._get_property_value_repeated(name, index, value_filter)
    else:
      #is NOT repeated
      #enforce correct argument arrangement.
      assert index == None
      assert value_filter == None
      return prop._get_value(self)

  def set_property_value(self, name, value, index=None, value_filter=None):
    """Handles setting the value of a property on an instance."""
    prop = self._get_property_instance_or_raise_error(name)
    if index == None and value_filter == None:
      return prop._set_value(self, value)
    else:
      assert prop._repeated == True
      return self._set_property_value_repeated(name, value, index, value_filter)


  def _get_property_value_repeated(self, name, index=None, value_filter=None):
    """Handles getting the value of a property on a REPEATED instance."""
    prop = self._get_property_instance_or_raise_error(name)
    repeated_property_list = prop._get_value(self)
    assert prop._repeated #make sure it's actually a repeated property

    if index:
      #the list index should obviously always be an INT
      assert isinstance(index, int)
      try:
        repeated_property_list = [repeated_property_list[index]]
      except IndexError, e:
        #change to more specific error.
        raise AssertionError(u'Repeated Property Index Error!') 

    if value_filter:
      #must filter possible values by value_filter.
      #value_filter could be a value or dict of values.
      res_list = []
      for res in repeated_property_list:
        #loop through available items
        passed = True
        if isinstance(prop, db.StructuredProperty):
          assert isinstance(value_filter, dict)
          for filter_k,filter_v in value_filter.iteritems():
            #get the value to test
            value_to_test = res.get_property_value(filter_k)
            #test it
            if value_to_test != filter_v:
              passed = False
        else:
          if res != value_filter:
            passed = False

        if passed == True:
          res_list.append(res)
      repeated_property_list = res_list
    return repeated_property_list if not index else repeated_property_list[0]
            
  def _set_property_value_repeated(self, name, value, index=None, value_filter=None):
    """Handles setting the value of a property on a REPEATED instance."""
    prop = self._get_property_instance_or_raise_error(name)
    repeated_list_value = prop._get_value(self)
    assert prop._repeated #make sure it's actually a repeated property

    if not value_filter:
      #the list index should obviously always be an INT
      assert isinstance(index, int)
      try:
        repeated_list_value[index] = value
      except IndexError, e:
        #change to more specific error.
        raise AssertionError(u'Repeated Property Index Error!')
    else:
      #must apply set to values matching properties in value_filter.
      #value_filter could be a value or dict of values.
      index_list = []
      for list_index,list_item in enumerate(repeated_list_value):
        #loop through available items
        passed = True
        if isinstance(prop, db.StructuredProperty):
          assert isinstance(value_filter, dict)
          for filter_k,filter_v in value_filter.iteritems():
            #get the value to test
            value_to_test = list_item.get_property_value(filter_k)
            #test it
            if value_to_test != filter_v:
              passed = False
              continue
        else:
          if list_item != value_filter:
            passed = False
            continue

        if passed == True:
          index_list.append(list_index)
      for k in list_index:
        repeated_list_value[k] = value
    return True

  def udpate_property_value(self, name, value, index=None, value_filter=None):
    """Handles updating the value of a property on a REPEATED instance."""
    prop = self._get_property_instance_or_raise_error(name)
    assert prop._repeated #make sure it's actually a repeated property
    repeated_list_value = prop._get_value(self)
    assert isinstance(value, (dict))

    if not value_filter:
      #the list index should obviously always be an INT
      assert isinstance(index, int)
      try:
        repeated_list_value[index] = value
      except IndexError, e:
        #change to more specific error.
        raise AssertionError(u'Repeated Property Index Error!')
    else:
      #must apply set to values matching properties in value_filter.
      #value_filter could be a value or dict of values.
      index_list = []
      for list_index,list_item in enumerate(repeated_list_value):
        #loop through available items
        passed = True
        if isinstance(prop, db.StructuredProperty):
          assert isinstance(value_filter, (dict, prop._modelclass))
          for filter_k,filter_v in value_filter.iteritems():
            #get the value to test
            value_to_test = list_item.get_property_value(filter_k)
            #test it
            if value_to_test != filter_v:
              passed = False
              continue
        else:
          if list_item != value_filter:
            passed = False
            continue

        if passed == True:
          index_list.append(list_index)
      for k in list_index:
        for prop_name,prop_instance in value.all_properties().iteritems():
          if isinstance(value, prop._modelclass):
            new_prop_value = prop_instance._get_value(value)
          else:
            new_prop_value = value.get(prop_name)
          prop_instance._set_value(repeated_list_value[k], new_prop_value)
    return True

  def remove_property_value(self, name, index=None, value_filter=None):
    prop = self._get_property_instance_or_raise_error(name)
    assert prop._repeated #make sure it's actually a repeated property
    repeated_list_value = prop._get_value(self)

    if not value_filter:
      #the list index should obviously always be an INT
      assert isinstance(index, int)
      try:
        repeated_list_value.pop(index)
      except IndexError, e:
        #change to more specific error.
        raise AssertionError(u'Repeated Property Index Error!')
    else:
      #must apply set to values matching properties in value_filter.
      #value_filter could be a value or dict of values.
      for list_index,list_item in enumerate(repeated_list_value):
        #loop through available items
        passed = True
        if isinstance(prop, StructuredProperty):
          assert isinstance(value_filter, (dict, prop._modelclass))
          for filter_k,filter_v in value_filter.iteritems():
            #get the value to test
            value_to_test = list_item.get_property_value(filter_k)
            #test it
            if value_to_test != filter_v:
              passed = False
              continue
        else:
          if list_item != value_filter:
            passed = False
            continue

        if passed == True:
          #will this bork if I mutate the list while I iterate through it?
          repeated_list_value.pop(list_index)
    return True

  def add_property_value(self, name, value):
    prop = self.__class__.get_property_instance(name)
    assert prop._repeated #make sure it's actually a repeated property
    if isinstance(prop, StructuredProperty):
      assert isinstance(value, prop._modelclass)
    prop._get_value(self).append(value)
  
  @classmethod
  def get_property_instance(cls, name):
    prop = cls.all_properties().get(name)
    return prop

  @classmethod
  def kind(cls):
    return cls._get_kind()

  @classmethod
  def all_properties(cls):
    return cls._properties

"""
This is the base datastore model.

"""
class BaseDatastoreModel(BaseModel):
  @classmethod
  def _get_by_id(cls, id, *args, **kwargs):
    if hasattr(cls, u'filter_id'):
      filtered_id = cls.filter_id(id)
      _type = str(type(id))
      _filtered_type = str(type(filtered_id))
    return cls._get_by_id(filtered_id, *args, **kwargs)
      
  @classmethod
  def read_name(cls):
      title = []
      for k,char in enumerate(cls.kind()):
          if char.isupper():
            if k > 0:
              title.append(u'_')
          title.append(char.lower())
      return ''.join(title)    
  """Creates the model with a unique string id"""
  @classmethod
  def create_with_unique_string_id(cls,
                  key_length=32,
                  slug_property=False,
                  *args,
                   **kwargs):
    key_id = random_string(key_length)
    while Key(cls.kind(),str(key_id)).get():
      key_id = random_string(key_length)
    if slug_property is True:
      kwargs[u'slug'] = key_id
    instance = cls(id=key_id, *args, **kwargs)
    instance.put()
    return instance
  
  """Child classes can override this method to run startup logic"""
  @classmethod
  def _prepare(cls):
    cls.prepare()
    bolognium.ext.var_cache.set(u'%s_PREPARED' % cls.kind(), datetime.datetime.now().isoformat())

  """Child classes can override this method to run startup logic"""
  @classmethod
  def prepare(cls):
    pass

  def link(self, action, admin=False):
    if admin and auth.is_current_user_admin():
      l = u'/admin/%s_%s/%s' % (self.read_name(), action, self.key.id())
    else:
      l = u'/%s/%s/%s' % (self.read_name(), action, self.key.id())
    return l

  """This can be overriden to coerce ids 
  to a model specific type or range"""
  @classmethod
  def filter_id(self, id=None):
    return id

  @classmethod
  def load_if_permitted(cls, id=None, action=None, user=None):
    """ Loads an instance and calls Kind specific permission
      validation logic before handing it back.

    Args:
      id: The 'id' of the entity if it has one.
      action: The action for permission is being asked.
      user: An optional user to check against.

    Returns:
      An entity of class `cls` or None.

    Raises:
      SomeError(?): Could be one of a few different ones.
      """

    """if a user wasn't provided, use the current user"""
    user = user or bolognium.ext.auth.current_user()

    """Let the class filter it's own id."""
    id = cls.filter_id(id)
    if id:
      key = ndb.key.Key(cls.kind(), id)
      if key:
        instance = key.get()
        if instance:
          if hasattr(cls, u'has_permission') and \
            cls.has_permission(instance, action, user):
            return instance
    return

  @classmethod
  def list_for_admin(cls, *args, **kwargs):
    if hasattr(cls, u'_list_for_admin'):
      return cls._list_for_admin(is_admin= \
          bolognium.ext.auth.is_current_user_admin())
    else:
      return []

  @classmethod
  def list_for_current_user(cls, *args, **kwargs):
    if hasattr(cls, u'_list_for_current_user'):
      return cls._list_for_current_user(is_logged_in= \
          bolognium.ext.auth.is_logged_in())
    else:
      return []
  
class BaseStructuredModel(BaseModel):
  """
  This is the BaseStructuredModel, used as 'modelclass' for 
  the StructuredProperty and LocalStructuredProperty(s).
  """
  pass

class StructuredModel(BaseStructuredModel, ndb.model.Model):
  pass

class Model(BaseDatastoreModel, ndb.model.Model):
  pass

class Expando(BaseDatastoreModel, ndb.model.Expando):
  pass

class FancyDateTimeDelta(object):
  """
  Format the date / time difference between the supplied date and
  the current time using approximate measurement boundaries
  """

  def __init__(self, dt):
    now = datetime.datetime.now()
    delta = now - dt
    self.just_now = False
    if delta > datetime.timedelta(seconds=300):
      self.year = delta.days / 365
      self.month = delta.days / 30 - (12 * self.year)
      if self.year > 0:
        self.day = 0
      else: 
        self.day = delta.days % 30
      self.hour = delta.seconds / 3600
      self.minute = delta.seconds / 60 - (60 * self.hour)
    else:
      self.just_now = True

  def format(self):
    if self.just_now: return 'Just now'
    fmt = []
    for period in ['year', 'month', 'day', 'hour', 'minute']:
      value = getattr(self, period)
      if value:
        if value > 1:
          period += "s"
        fmt.append("%s %s" % (value, period))
    return ", ".join(fmt) + " ago"

"""Tries to coerce to a positive integer and returns zero on fail"""
def valid_id_or_default(value=None, default=None):
  return positive_int_or_default(value=value, default=default)

"""Tries to coerce to a positive integer and returns zero on fail"""
def valid_id_or_zero(value=None):
  return positive_int_or_default(value=value, default=0)

"""Tries to coerce to a positive integer and returns zero on fail"""
def positive_int_or_default(value, default=0):
  try:
    return max(int(value), 0)
  except (ValueError,TypeError):
    return default

"""Tries to coerce to a positive integer and returns zero on fail"""
def valid_string_id_or_none(value=None):
  return valid_string_id_or_default(value, default=None)

"""Tries to coerce to a positive integer and returns zero on fail"""
def valid_string_id_or_default(value=None, default=None):
  return string_or_default(value=value, default=default, min_length=1, max_length=1024)

"""Tries to coerce to a positive integer and returns zero on fail"""
def string_or_default(value, default=None, max_length=None, min_length=None):
  try:
    assert value
    value = str(value)
    if max_length:
      assert len(value) <= max_length
    if min_length:
      assert len(value) >= min_length
      
  except (ValueError, TypeError, AssertionError):
    value = default
  return value
