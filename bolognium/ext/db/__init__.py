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

import filters as filters_module

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

def _apply_property_updates(model_instance, updates={}):
  """  
  :param instance:
    A ``BaseModel`` instance.
  :param updates:
    The updated field => value dict. 
  :returns:
    None.
  :raises:
    The standard validation exceptions.
  """
  #bolognium.ext.utils.log.debug(updates)
  try:
    assert len(updates) > 0
    assert isinstance(model_instance, BaseModel)
    for prop_name,update_data in updates.iteritems():
      prop_instance = model_instance.get_property_instance(prop_name)

      if not prop_instance:
        bolognium.ext.utils.log.error(u'No property by name: \'%s\'.' % prop_name)
        raise AssertionError(u'No property by name: \'%s\'.' % prop_name)
      if isinstance(prop_instance, StructuredProperty):
        _operated_structured_props = {}
        ##### StructuredProperty 
        if prop_instance._repeated:
          ####### REPEATED 
          assert isinstance(update_data, dict)
          """{'OP_KEY': {'INDEX': dict(**op_data_row)}}"""
          for op_key,op_data_dict in update_data.iteritems():
            assert isinstance(op_data_dict, dict)
            assert op_key in (u'ADD', u'SET', u'DELETE', u'UPDATE', u'REPLACE')

            """{'OP_KEY': {'INDEX': dict(**op_data_row)}}"""
            for index,op_data_row in op_data_dict.iteritems():

              #the primary key cannot be deleted.
              assert prop_instance._modelclass._primary_key != prop_name

              #each value (in this case prop._modelclass instance) can
              #only have a single operation applied.
              _unique_op_string = u'%s.[%s]' % (prop_name, index)
              if not _operated_structured_props.get(_unique_op_string):
                _operated_structured_props[_unique_op_string] = op_key
              assert op_key == _operated_structured_props[_unique_op_string]

              if op_key == u'DELETE': #can delete individual properties or whole object
                if isinstance(op_data_row, dict):
                  #remove select child props
                  struct_instance = model_instance.get_property_value(prop_name, index=index)
                  if not struct_instance:
                    raise AssertionError(u'Could not get %s.%s by index '
                      u'\'%s\'.' % (model_instance.kind(), prop_name, 
                      index))
                  else:
                    for _k, _v in op_data_row.iteritems():
                      _nested_prop_instance = prop_instance._modelclass.\
                        get_property_instance(_k)
                      assert _v == True
                      delattr(struct_instance, _k)
               
                else:
                  assert op_data_row == True
                  #remove the whole record.
                  list_index = None
                  struct_instance = model_instance.get_property_value(prop_name, index=index)
                  if struct_instance:
                    _p_list = model_instance.get_property_value(prop_name)
                    _p_list.remove(struct_instance)
                  else:
                    #did not exist. #must error
                    raise AssertionError(u'Could not get %s.%s by index '
                      u'\'%s\'.' % (model_instance.kind(), prop_name, 
                      index))
                  
              elif op_key == u'ADD':#raise already exists error if key exists already.
                if isinstance(op_data_row, StructuredModel):
                  _v = op_data_row.primary_key()
                else:
                  assert isinstance(op_data_row, dict)
                  _v = op_data_row.get(prop_instance.primary_key_name)
                assert _v not in (None, u'')
                _current = model_instance.get_property_value(prop_name, index=index)
                if _current:
                  model_instance.get_property_value(prop_name).remove(_current)
                  raise AssertionError(u'Already Exists Error while '
                    u'ADDing %s.%s by index \'%s\'.' % 
                    (model_instance.kind(), prop_name, index))

                _p_list = model_instance.get_property_value(prop_name)
                if isinstance(op_data_row, dict):
                  op_data_row = prop_instance._modelclass(**op_data_row)
                _p_list.append(op_data_row)
              
              elif op_key == u'SET':#equivelant to a 'REPLACE' without raising error on non existant indexes
                new_index = op_data_row.get(prop_instance.primary_key_name) or index

                assert isinstance(op_data_row, dict)
                _current = model_instance.get_property_value(prop_name, index=index)
                _p_list = model_instance.get_property_value(prop_name)
                if _current:
                  _p_list.remove(_current)
                    
                #make sure the end index is set
                op_data_row[prop_instance.primary_key_name] = new_index
                _p_list.append(prop_instance._modelclass(**op_data_row))
                
              elif op_key == u'UPDATE':#should raise an error on non existant indexes
                assert isinstance(op_data_row, dict)
                new_index = op_data_row.get(prop_instance._modelclass._primary_key) or index

                _current = model_instance.get_property_value(prop_name, index=index)
                if _current:
                  op_data_row[prop_instance._modelclass._primary_key] = new_index
                  _current.populate(**op_data_row)
                else:
                  raise AssertionError(u'Does Not Exist Error while '
                    u'UPDATEing %s.%s by index \'%s\'.' % 
                    (model_instance.kind(), prop_name, index))

              elif op_key == u'REPLACE':#should raise an error on non existant indexes
                assert isinstance(op_data_row, dict)
                new_index = op_data_row.get(prop_instance._modelclass._primary_key) or index
                _current = model_instance.get_property_value(prop_name, index=index)
                if _current:
                  _p_list = model_instance.get_property_value(prop_name)
                  _p_list.remove(_current)
                  op_data_row[prop_instance._modelclass._primary_key] = new_index
                  _p_list.append(prop_instance._modelclass(**op_data_row))
                else:
                  raise AssertionError(u'Does Not Exist Error while '
                    u'REPLACEing %s.%s by index \'%s\'.' % 
                    (model_instance.kind(), prop_name, index))
              else:
                raise AssertionError('Invalid operation type \'%s\'.' % op_key)
            
        else:
          ####### NON-REPEATED (STRUCTURED)
          _unique_op_string = u'NON_REPEATED_%s' % (prop_name)
          if not _operated_structured_props.get(_unique_op_string):
            _operated_structured_props[_unique_op_string] = op_key
          assert op_key == _operated_structured_props[_unique_op_string]
          op_key = update_data[0]
          _val = update_data[1]

          _current = model_instance.get_property_value(prop_name)
          if op_key == u'SET':
            assert isinstance(op_data_row, dict)
            #_new_val = prop_instance._modelclass(**op_data_row)
            model_instance.set_property_value(prop_name, op_data_row)
          elif op_key == u'UPDATE':
            assert isinstance(op_data_row, dict)
            _current = model_instance.get_property_value(prop_name)
            if current_:
              _current.populate(op_data_row)
            else:
              raise AssertionError(u'Does Not Exist Error while '
                u'UPDATEing \'%s.%s\'.' % (model_instance.kind(), 
                prop_name))
          elif op_key == u'DELETE':
            assert bool(isinstance(op_data_row, dict) or op_data_row == True)
            if op_data_row == True:
              self.delete_property_value(prop_name)
            else:
              struct = model_instance.get_property_value(prop_name)
              for _k,_v in op_data_row.iteritems():
                _struct_prop = struct.get_property(_k)
                if _struct_prop:
                  _struct_prop._delete_value(struct)
                else:
                  raise AssertionError(u'Bad property name \'%s\' '
                    u'while DELETEing properties from structured model '
                    u'class \'%s\'.' % (struct.kind(), prop_name))
                  
          else:
            raise AssertionError('Invalid operation type \'%s\'.' % op_key)
          
      else:
        ##### REGULAR PROPERTY 
        if prop_instance._repeated:
          for op_key,op_data in update_data.iteritems():
            _value_list = model_instance.get_property_value(prop_name)
            ##### REPEATED
            if op_key == u'ADD':
              for val in op_data:
                if val not in _value_list:
                  _value_list.append(val)
            elif op_key == u'REPLACE':
              for val in op_data:
                try:
                  _list_index = _value_list.index(val)
                except ValueError:
                  raise AssertionError(u'Does Not Exist Error while '
                    u'REPLACEing \'%s.%s\' with value \'%s\' .' % 
                    (model_instance.kind(), prop_name, val))
                else:
                  _value_list[_list_index] = val
            elif op_key == u'DELETE':
              for val in op_data:
                try:
                  _list_index = _value_list.index(val)
                except ValueError:
                  raise AssertionError(u'Does Not Exist Error while '
                    u'DELETEing \'%s.%s\' with value \'%s\' .' % 
                    (model_instance.kind(), prop_name, val))
                else:
                  _value_list.pop(_list_index)
            else:
              raise AssertionError('Invalid operation type \'%s\'.' % op_key)
            
        else:
          ##### NON-REPEATED
          assert not isinstance(update_data, (dict, list))
          prop_instance._set_value(model_instance, update_data)

  except AssertionError, e:
    #should halt the updates and throw back a general error.
    logging.error(u'ERROR WITH UPDATES: %s' % updates)
    raise datastore_errors.BadValueError(u'There was a general error '
      u'when applying updates. MSG: %s' % e)

class BaseProperty(ndb.model.Property):
  _class_filters = []
  _whitelisted = False
  _primary_key = False

  def __init__(self, whitelisted=False, primary_key=False, *args, **kwargs):

    """Indicates if visible in client side output."""
    self._whitelisted = whitelisted

    """Indicates a claim of primary key."""
    if primary_key in (True, False):
      self._primary_key = primary_key

    super(BaseProperty, self).__init__(*args, **kwargs)

  def _get_all_filters_for_property(self, additional_filters=[]):
    filter_instances = []

    """Add filters passed in on the fly (right at the input stage)."""
    if isinstance(additional_filters, list):
      filter_instances.extend(additional_filters)

    """Add filters defined by property class"""
    _class_filters = getattr(self, u'_class_filters', None)
    if isinstance(_class_filters, list):
      filter_instances.extend(_class_filters)

      """Check each filter in the list is ACTUALLY a filter."""
    for _filter in filter_instances:
      try:
        assert isinstance(_filter, filters_module.Filter)
      except AssertionError:
        raise Exception(u'_get_all_filters_for_property produced '
          u'an invalid \'_filter\' arg \'%s\' for property \'%s.%s\'.'
          % (_filter, cls.kind(), property_instance._name))

    return filter_instances


class UserProperty(BaseProperty, ndb.model.UserProperty):
  pass

class GeoPtProperty(BaseProperty, ndb.model.GeoPtProperty):
  pass

class GenericProperty(BaseProperty, ndb.model.GenericProperty):
  pass

class LocalStructuredProperty(BaseProperty, ndb.model.LocalStructuredProperty):
  def _get_for_client_side(self, instance=None, **kwargs):
    val = self._get_value(entity=instance)
    if val:
      try:
        val = val.to_client_side()
      except Exception, e:
        val = None
    return val

class StructuredProperty(BaseProperty, ndb.model.StructuredProperty):
  def _get_for_client_side(self, instance=None, **kwargs):
    val = self._get_value(entity=instance)
    if val:
      try:
        val = val.to_client_side()
      except Exception, e:
        val = None
    return val

  @property
  def primary_key_name(self, **kwargs):
    return self._modelclass._primary_key

  def primary_key(self, **kwargs):
    return self._modelclass.primary_key()

  def _validate(self, value):
    value = super(StructuredProperty, self)._validate(value)
    if self._repeated and value and value.primary_key() in (None, u''):
      raise datastore_errors.BadValueError(u'StructuredProperty '
        u'modelclass \'s\' failed primary key test for use in a \'repeated\' '
        u'property.' % self._modelclass.kind())

class ComputedProperty(BaseProperty, ndb.model.ComputedProperty):
  pass

### @@TODO: FIX THIS!!!
class KnuthedIDProperty(ComputedProperty):
  ### @@TODO: FIX THIS!!!
  def __init__(self, *args, **kwargs):
    super(KnuthedIDProperty, self).__init__(
      func=lambda self: self._get_knuthed_id_or_none, *args, **kwargs)

  ### @@TODO: FIX THIS!!!
  ### @@TODO: Should knuth_hash the instance.id() 
  def _get_knuthed_id_or_none(self):
    if self.key and self.key.id():
      return bolognium.ext.utils.knuth_hash(self.key.id())
    return None

class KeyProperty(BaseProperty, ndb.model.KeyProperty):
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

class BlobKeyProperty(BaseProperty, ndb.model.BlobKeyProperty):
  def _get_for_client_side(self, instance=None, recursion_level=1, **kwargs):
    val = self._get_value(entity=instance)
    return str(val)

class TextProperty(BaseProperty, ndb.model.TextProperty):
  pass

class PostBodyProperty(TextProperty):
  _class_filters = [filters_module.html_filter]

class JsonProperty(TextProperty):
  def _get_for_client_side(self, instance=None, **kwargs):
    val = bolognium.ext.utils.json.loads(val)
    return self.get_loaded_data(self, instance)

  def get_loaded_data(self, instance):
    val = self._get_value(entity=instance)
    val = bolognium.ext.utils.json.loads(val)
    return val

class StringProperty(BaseProperty, ndb.model.StringProperty):
  _class_filters = [filters_module.StringFilter(max_length=500)]

class UnderscoredSlugProperty(StringProperty):
  _class_filters = [filters_module.MustOnlyContainFilter(lowercase=True, 
    to_lowercase=True, extra_chars=(u'_'))]

class SlugProperty(StringProperty):
  _class_filters = [filters_module.MustOnlyContainFilter(lowercase=True, 
    to_lowercase=True, extra_chars=(u'-'))]

class NameProperty(BaseProperty, ndb.model.StringProperty):
  _class_filters = [filters_module.lowercase_and_underscores_only, \
      filters_module.StringFilter(min_length=1, max_length=500)]

class CountryCodeProperty(StringProperty):
  _class_filters = [filters_module.RegexFilter(min_length=2, max_length=2, \
      lowercase=True, uppercase=True, to_uppercase=True)]

class UINameProperty(StringProperty):
  _class_filters = [filters_module.sensible_uiname_chars_only]

class EmailProperty(StringProperty):
  _class_filters = [filters_module.EmailFilter()]

class PhoneNumberProperty(StringProperty):
  _class_filters = [filters_module.StringFilter(max_length=100)]

class DomainNameProperty(StringProperty):
  _class_filters = [filters_module.DomainNameFilter()]

class LinkProperty(TextProperty):
  _class_filters = [filters_module.LinkFilter()]

class IntegerProperty(BaseProperty, ndb.model.IntegerProperty):
  _class_filters = [filters_module.IntegerFilter()]

class BooleanProperty(BaseProperty, ndb.model.BooleanProperty):
  _class_filters = [filters_module.BooleanFilter()]

class EnabledProperty(BooleanProperty):
  _class_filters = [filters_module.StringFilter(max_length=100), \
      filters_module.BooleanFilter()]
  def __init__(self, default=False, *args, **kwargs):
    super(EnabledProperty, self).__init__(default=default, *args, **kwargs)

class BlobProperty(BaseProperty, ndb.model.BlobProperty):
  pass

class TimeProperty(BaseProperty, ndb.model.TimeProperty):
  pass

class DateProperty(BaseProperty, ndb.model.DateProperty):
  pass

class DateTimeProperty(BaseProperty, ndb.model.DateTimeProperty):
  _class_filters = [filters_module.datetime_filter]
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

class DecimalProperty(BaseProperty):
  _class_filters = [filters_module.decimal_filter]

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
  def is_DS(cls):
    if issubclass(cls, BaseDatastoreModel):
      return True
    return False
    
  def has_complete_key(self):
    return self._has_complete_key()

  def _get_property_instance_or_raise_error(self, name):
    prop = self.__class__.get_property_instance(name)
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
    if prop._repeated == True: 
      #forward to 'repeated' property setter.
      return self._set_property_value_repeated(name, value, index, value_filter)
    else:
      #is NOT repeated
      #enforce correct argument arrangement.
      assert index == None
      assert value_filter == None
      return prop._set_value(self, value)


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
          #will this bork if I mutate the list while I iterate through it?
          repeated_list_value.pop(list_index)
    return True

  def add_property_value(self, name, value):
    prop = self.__class__.get_property_instance(name)
    assert prop._repeated #make sure it's actually a repeated property
    if isinstance(_prop, StructuredProperty):
      assert isinstance(value, prop._modelclass):
    prop._get_value(self).append(value)
  
  @classmethod
  def get_property_instance(cls, name):
    name = name.split(u'.')
    prop = cls.all_properties().get(name[0])
    if len(name) > 1:
      return prop._modelclass.all_properties().get(name[1])
      
    return cls._properties.get(name[0])

  @classmethod
  def kind(cls):
    return cls._get_kind()

  @classmethod
  def all_properties(cls):
    return cls._properties

  @classmethod
  def _sanitize_input_schema(cls, input_schema={}):
    sanitized_input_schema = {}
    schema_ctx_opts = {}
    for prop_conf in input_schema:
      ctx_opts = {}
      prop_desc_str = None
      filters = []
      _operations = None
      if isinstance(prop_conf, basestring):
        prop_desc_str = prop_conf
      elif isinstance(prop_conf, dict):
        prop_desc_str = prop_conf.get(u'name')
        ctx_opts = prop_conf.get(u'ctx_opts', {})
        filters = prop_conf.get(u'filters', filters)
        if not isinstance(filters, list):
          filters = [filters]
        _operations = prop_conf.get(u'operations', _operations)
        if _operations and not isinstance(_operations, list):
          _operations = [_operations]
      else:
        raise Exception(u'_sanitize_input_schema got invalid property got '
          u'invalid property configuration type. Excecpted dict, but got '
          u'%s.' % prop_conf.__class__)
        
      """validate the option"""
      if prop_desc_str:
        prop_instance = cls.get_property_instance(prop_desc_str)
        if not prop_instance:
          raise Exception(u'_sanitize_input_schema got invalid property '
            u'name for Kind \'%s\'. Property Name: \'%s\'' % (cls.kind(), prop_desc_str))

        for _filter in filters:
          try:
            assert isinstance(_filter, filters_module.Filter)
          except AssertionError, e:
            raise Exception(u'_sanitize_input_schema found invalid '
              u'filter args in the input schema. Prop_desc_str: \'%s\''
              % (prop_desc_str))

        schema_ctx_opts[prop_desc_str] = ctx_opts
        sanitized_input_schema[prop_desc_str] = {
          u'name': prop_desc_str,
          u'filters': filters,
          u'operations': _operations,
          u'ctx_opts': ctx_opts
        }
      else:
        raise Exception(u'_sanitize_input_schema found invalid '
          u'\'name\' in the input schema. Prop_desc_str: \'%s\'.'
          % (prop_desc_str))
    #bolognium.ext.utils.log.debug(sanitized_input_schema)
    return sanitized_input_schema, schema_ctx_opts

  @classmethod
  def _structure_input_data(cls, sanitized_input={}):
    structured_input = {}
    _processed = {}
    for post_key,post_value in sanitized_input.iteritems():
      #parse the string
      post_key_parts, base_prop_name, op_key, index, third_arg = \
        cls._parse_input_string(post_key)

      prop_instance = cls.get_property_instance(base_prop_name)

      if isinstance(prop_instance, StructuredProperty):
        ###################### """StructuredProperty"""

        primary_key_name = prop_instance._modelclass._primary_key
        if third_arg and third_arg != primary_key_name:
          try:# this enforces the primary key is set
            index = sanitized_input[u'%s.[%s].%s' % (base_prop_name, 
              op_key, primary_key_name)]
          except KeyError, e:
            bolognium.ext.utils.log.warn(u'Ignoring StructuredProperty input on '
              u'KEY \'%s\' because primary_key input was not found.' % 
              u'%s.[%s].%s' % (base_prop_name, op_key, third_arg))
            continue

        if not third_arg:
          val = post_value
        elif op_key == u'DELETE':
          if third_arg is None:
            val = True
          else:
            val = {str(third_arg): True}
        else:
          val = {str(third_arg): post_value}

        """StructuredProperty()"""
        if prop_instance._repeated:
          ###################### """REPEATED StructuredProperty"""
          """REPEATED StructuredProperty. Conform to SET UPDATE REPLACE DELETE schema"""

          if not base_prop_name in structured_input.keys():
            structured_input[base_prop_name] = {
              u'ADD': {},
              u'SET': {},
              u'UPDATE': {},
              u'REPLACE': {}, 
              u'DELETE': {}
            }
          if not third_arg:
            bolognium.ext.utils.log.debug(val)
            assert isinstance(val, StructuredModel)
            structured_input[base_prop_name][op_key][val.primary_key()] = val
          else:
            if not index in structured_input[base_prop_name][op_key].keys():
              structured_input[base_prop_name][op_key][index] = {}
            structured_input[base_prop_name][op_key][index].update(val)
            
        else:
          if not third_arg:
            assert isinstance(val, StructuredModel)
            structured_input[base_prop_name][op_key][index] = val
          elif not structured_input.get(base_prop_name):
            structured_input[base_prop_name] = [op_key,val]
          elif isinstance(val, dict):
            structured_input[base_prop_name][1].update(val)
          else:
            raise AssertionError(u'There was a problem!')
            logging.error(u'There was a problem!')

      else:
        ###################### """NORMAL PROP"""
        if prop_instance._repeated:
          ###################### """NORMAL PROP REPEATED"""
          """REPEATED - Conform to ADD REPLACE DELETE schema"""
          """Create the op element if it doesn't exist."""
          if not structured_input.get(base_prop_name):
            structured_input[base_prop_name] = {
              u'ADD': [],
              u'REPLACE': {},
              u'DELETE': []
            }
          """NOT REPEATED - Simple. {'key':'value'}"""

          if op_key == u'REPLACE':
            structured_input[base_prop_name][op_key][index] = post_value
          elif op_key == u'DELETE':
            structured_input[base_prop_name][op_key].append(index)
          else:
            structured_input[base_prop_name][op_key].append(post_value)
          
        else:
          ###################### """NORMAL PROP NON-REPEATED"""
          """NOT REPEATED - Simple. {'key':'value'}"""
          structured_input[base_prop_name] = post_value
          
    return structured_input

  @classmethod
  def _parse_input_string(cls, post_key=u''):
    post_key_parts = post_key.split(u'.')
    base_prop_name = post_key_parts[0]
    if len(post_key_parts) > 1:
      if len(post_key_parts) > 2:
        if post_key_parts[-1][-1] == u']':
          post_key_parts = [post_key_parts[0], u'.'.join(post_key_parts[1:])]
        elif len(post_key_parts) > 3:
          post_key_parts = \
            [post_key_parts[0], u'.'.join(post_key_parts[1:-1]), post_key_parts[-1]]
        

      #operation:index keys should be wrapped in []
      assert post_key_parts[1][0] == u'['
      assert post_key_parts[1][-1] == u']'

      third_arg = post_key_parts[2] if len(post_key_parts) > 2 else None
      instruct_key_parts = post_key_parts[1][1:-1].split(u':', 1)
      op_key = instruct_key_parts[0]
      i_len = len(instruct_key_parts)
      index = instruct_key_parts[1] if i_len > 1 else None
    else:
      third_arg = op_key = index = None

    return post_key_parts, base_prop_name, op_key, index, third_arg

  @classmethod
  def _parse_and_sanitize_input_data(cls, input_schema={}, input_data={}):
    """ Loop through input data items and....
    """
    assert isinstance(input_schema, dict)
    assert isinstance(input_data, dict)

    """Create a schema validator."""
    filter_schema_validator = filters_module.SchemaFilter()

    sanitized_input_data = {}
    _operations = {}
    for post_key,post_val in input_data.iteritems():
      try:
        input_schema_arg = prop_instance = None
        filter_instances = []
        #assert post_key not in sanitized_input_data.keys():
          
        post_key_parts, base_prop_name, op_key, index, third_arg = \
          cls._parse_input_string(post_key)
        
        #the base property
        input_schema_arg = base_prop_name
        prop_instance = cls.get_property_instance(base_prop_name)
        assert prop_instance

        if isinstance(prop_instance, StructuredProperty):
          ################# """StructuredProperty"""
          """StructuredProperty(s) must always have an op_key"""
          assert op_key in (u'ADD', u'SET', u'UPDATE', u'REPLACE', u'DELETE')

          """If a third arg exists (property.[OPERATION:index].third_arg)
          it will need to be added to the initial base_property_name 
          before that's checked against the input_schema"""
          if third_arg:
            input_schema_arg += u'.%s' % third_arg
            if op_key in (u'SET', u'DELETE'):
              try:
                assert third_arg != prop_instance._modelclass._primary_key
              except AssertionError, e:
                bolognium.ext.utils.log.debug('post_key: %s is invalid because the primary_key value should not be set there.' % post_key)
                continue
              if op_key == u'DELETE':
              
                """We have to make sure the 'base' property delete is
                recognised/respected over delete operations on child 
                properties."""
                _parent_string = u'.'.join(post_key_parts[:2])
                parent_del_val = input_data.get(_parent_string, None)
                assert (not parent_del_val or parent_del_val != u'true')
              
                """The ONLY Delete 'value'."""
                assert post_val == u'true'
        
          if prop_instance._repeated:
            """REPEATED STRUCTURED PROPERTY"""

            """There should always be an index when ADDing."""
            assert bool(index or op_key == u'ADD')

          else: 
            """NON-REPEATED STRUCTURED PROPERTY"""
            assert not index

          if third_arg:
            """The property instance will actually be on the _modelclass."""
            new_prop_instance = prop_instance._modelclass.get_property_instance(third_arg)
            assert new_prop_instance
            prop_instance = new_prop_instance


          ################# """END OF STRUCTURED PROPERTY"""
        else: 
          ################# """NORMAL PROPERTY"""
          if prop_instance._repeated:
            """REPEATED NORMAL PROPERTY"""

            """This should be the case"""
            if op_key in (u'REPLACE', u'DELETE'):
              assert index
            else:
              assert op_key == u'ADD'
          else:
            """NON-REPEATED NORMAL PROPERTY"""
            # should not be set
            assert not op_key 
            assert not third_arg 
            assert not index 

            # can only be 'SET'
            op_key = u'SET'

          ################# """END OF NORMAL PROPERTY"""

        #checks that no previous input row has already started an incompatible operation.
        unique_operation_string = u'%s:%s:%s' % (base_prop_name, third_arg or u'NO_THIRD_ARG', index or u'NO_INDEX')

        assert unique_operation_string not in _operations.keys()
        _operations[unique_operation_string] = op_key

        """Check we have eveything""" #checks against keys in input_schema
        assert prop_instance
        assert input_schema_arg
        assert input_schema_arg in input_schema.keys()
        _valid_ops = input_schema[input_schema_arg][u'operations']
        if _valid_ops:
          assert op_key in _valid_ops

        if op_key and op_key == u'DELETE':
          #'delete' inputs don't need to be filtered
          filter_instances = []
        else:
          """The filters that apply to this property."""
          filter_instances = prop_instance._get_all_filters_for_property(
            input_schema[input_schema_arg][u'filters'])

        """The value is added to the sanitized dict for sending back."""
        sanitized_input_data[post_key] = post_val 

        """Add the wrapper around the input field."""
        filter_schema_validator.add(post_key, filters_module.\
            PropertyFilterWrapper(property_name=post_key, filters=\
            filter_instances, property_instance=prop_instance))

      except AssertionError, e:
        bolognium.ext.utils.log.debug(u'Error during input data filtering. MSG: %s' % e.message)
        """All AssertionError(s) mean an unrecognized input key 
        and the input should be ignored."""
        continue

    #bolognium.ext.utils.log.debug(u'SANITIZED INPUT DATA:')
    #bolognium.ext.utils.log.debug(sanitized_input_data)
    #return both the validator, and the data ready to process.
    return filter_schema_validator, sanitized_input_data

  @classmethod
  def filter_input(cls, input_data, input_schema={}, model_instance=None):
    assert isinstance(input_data, dict)

    """Create the context to hold the current entity, etc"""
    context = {u'instance': model_instance, u'raw_input': input_data,
      u'sanitized_input':{}, u'computed_data': {}}
    
    """Sanitize the input schema"""
    input_schema, ctx_opts = cls._sanitize_input_schema(input_schema=input_schema)

    #bolognium.ext.utils.log.debug(u'SANITIZED INPUT SCHEMA:')
    #bolognium.ext.utils.log.debug(input_schema)

    """Sanitize the input schema"""
    filter_schema_validator, sanitized_input = cls.\
      _parse_and_sanitize_input_data(input_schema=input_schema, \
      input_data=input_data)

    context[u'sanitized_input'] = sanitized_input
    context[u'ctx_opts'] = ctx_opts

    if len(sanitized_input) > 0 :
      sanitized_input = filter_schema_validator.process(sanitized_input,
        context)
    else:
      raise Exception('Model.filter_input() called with empty input.')
      
    return sanitized_input, context

  @classmethod
  def create_from_input(cls, id=None, parent=None, input_schema={}, 
    input_data={}, extra_data={}, transactional=False, **kwargs):
    assert isinstance(transactional, bool)
    kwargs['input_schema'] = input_schema
    kwargs['input_data'] = input_data
    if transactional:
      return ndb.model.transaction(lambda:cls._create_from_input(**kwargs))
    else:
      return cls._create_from_input(**kwargs)
    
  @classmethod
  def _create_from_input(cls, id=None, parent=None, input_schema={}, 
    input_data={}, extra_data={}, save=True):
    """ Validates inputted fields then creates
      a new entity if everything went ok.

    Args:
      id: string_id of soon to be entity.
      parent: Parent of soon to be entity or None.
      input_schema: A filtration description.
      input_data: The raw input to be filtered.
      extra_data: Extra Data to be applied after construction.

    Returns:
      An entity of class `cls`.
    """

    assert isinstance(extra_data, dict)
    entity = None
    err = None
    context = {}
    try:
      """validate the received fields"""
      filtered_input, context = cls.filter_input(input_data=input_data, 
          input_schema=input_schema, model_instance=None)

      structured_updates = cls._structure_input_data(filtered_input)

      _initial_props = {}
      _after_create_props = {}
      
      # decide which properties will be added at creation, 
      # and which will be applied after.
      for prop_name,_input in structured_updates.iteritems():
        _p = cls.get_property_instance(prop_name)

        if not isinstance(_p, StructuredProperty) and not _p._repeated:
          _initial_props[str(prop_name)] = _input
        else:
          _after_create_props[str(prop_name)] = _input

      """Create the entity with all regular attributes"""
      entity = cls(id=id, parent=parent, **_initial_props)

      """Apply extended properties if there is any."""
      if len(_after_create_props) > 0:
        try:
          _apply_property_updates(entity, updates=_after_create_props)
        except datastore_errors.BadValueError, e:
          raise filters_module.InvalidDataError('There was an unspecified error.',
            '', 'unspecified_error', context, error_dict={})

      """Apply extra properties added by controller if there is any."""
      computed_prop_data = context.get(u'computed_data', None)
      if computed_prop_data:
        _apply_property_updates(entity, updates=computed_prop_data)

      """Apply extra properties added by controller if there is any."""
      if len(extra_data) > 0:
        try:
          _apply_property_updates(entity, updates=extra_data)
        except datastore_errors.BadValueError, e:
          raise filters_module.InvalidDataError('There was an unspecified error.',
            '', 'unspecified_error', context, error_dict={})

      #save if so instructed
      if save == True:
        if not isinstance(entity, StructuredModel):
          entity.put()

    except filters_module.InvalidDataError, e:
      err = e

    """return the entity"""
    return entity,err,context

  @classmethod
  def _update_from_input(cls, instance, input_schema={}, input_data={}, save=True):
    """ Takes a bunch of keywords and tries to update
      an entity using them.

    Args:
      input schema: Field/Filter info, etc.
      input_data: The attributes to update and their new values.

    Returns:
      The updated entity. Sure, why not?

    Raises:
      InvalidDataError: Validation failed.
      SomeOtherError(?): Could be one of a few different ones.
      """

    err = None
    filtered_input = {}
    context = {}
    try:
      """run the validation"""
      filtered_input, context = cls.filter_input(input_data=
        input_data, input_schema=input_schema, model_instance=instance)    
      """no exceptions were raised, so apply the changes"""

      #structured updates
      structured_updates = cls._structure_input_data(filtered_input)
      
      """Apply the structured updates."""
      try:
        _apply_property_updates(instance, updates=structured_updates)
      except datastore_errors.BadValueError, e:
        raise filters_module.InvalidDataError('There was an unspecified '
          u'error.', '', 'unspecified_error', context, error_dict={})

      """Apply extra properties added by controller if there is any."""
      computed_prop_data = context.get(u'computed_data', None)
      if computed_prop_data:
        _apply_property_updates(instance, updates=computed_prop_data)

      #This is the default behaviour.
      if save == True:
        if not isinstance(instance, StructuredModel):
          instance.put()

    except filters_module.InvalidDataError, e:
      err = e

    """return the entity"""
    return err, context

  def update_from_input(self, input_schema={}, input_data={}, transactional=False, **kwargs):
    assert isinstance(transactional, bool)
    kwargs['input_schema'] = input_schema
    kwargs['input_data'] = input_data
    kwargs['instance'] = self
    if transactional:
      return ndb.model.transaction(lambda:self._update_from_input(**kwargs))
    else:
      return self._update_from_input(**kwargs)



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
  
"""
This is the BaseStructuredModel, used as 'modelclass' for 
the StructuredProperty and LocalStructuredProperty(s).
"""
class BaseStructuredModel(BaseModel):
  _primary_key = None

  def primary_key(self):
    _primary_key_prop = self.__class__.get_property_instance(self._primary_key)
    if _primary_key_prop:
      return _primary_key_prop._get_value(self)
    return None

  @classmethod
  def _fix_up_properties(cls):
    super(BaseStructuredModel, cls)._fix_up_properties()
    if cls.__module__ != __name__:
      for p_name,p in cls.all_properties().iteritems():
        if p._primary_key:
          if cls._primary_key is not None:
            raise Exception(u'Multiple properties have claimed '
              u'primary_key on Model:\'%s\'' % cls.kind())
          cls._primary_key = p_name

      if not cls._primary_key:
        raise NotImplementedError(u'Model:\'%s\' has no nominated '
          u'primary_key. Currently, StructuredProperty(s) must claim a '
          u'primary key property.' % cls.kind())

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

"""Generates random strings at a specified length"""
def random_string(length):
  return unicode(''.join([random.choice(string.letters \
    + string.digits) for i in range(length)]))

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
