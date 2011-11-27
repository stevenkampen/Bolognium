#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from StringIO import StringIO

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.api.labs import taskqueue

import os
import sys
import decimal
import datetime
import inspect
import hashlib
import time
import random
import string
import math
import copy
import re

  
from urllib2 import urlparse

from copy import deepcopy
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.lexers import JavascriptLexer
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

import bolognium
from google.appengine.ext.ndb import tasklets

from lxml import etree, html

class AttrDict(dict):
  def __getattr__(self, name):
    if name not in self:
      raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, name))
    return self[name]


class FilterError(Exception):
  "All exceptions thrown by this library must be derived from this base class"
  def __init__(self, msg):
    self._msg = msg

  def msg(self):
    return self._msg

      
class InvalidDataError(FilterError):
  """All exceptions which were caused by data to be validated must be derived 
  from this base class."""
  def __init__(self, msg, value, key=None, context=None, error_dict=None):
    self._details = AttrDict(key=lambda: key, msg=lambda: msg, 
      value=lambda: value, context=lambda: context)
    self._error_dict = error_dict or {}
    super(InvalidDataError, self).__init__(msg)
  
  def __repr__(self):
    cls_name = self.__class__.__name__
    e = self.details()
    values = (cls_name, repr(e.msg()), repr(e.value()), repr(e.key()), repr(e.context()))
    return '%s(%s, %s, key=%s, context=%s)' % values
  __str__ = __repr__
  
  def details(self):
    """Return information about the *first* error."""
    return self._details
  
  def error_dict(self):
    "Return all errors as an iterable."
    return self._error_dict
  
  def error_for(self, field_name):
    return self.error_dict()[field_name]


class EmptyError(InvalidDataError):
  pass


class InvalidArgumentError(FilterError):
  pass



class Filter(object):
  messages = {
    'validation_failed': u'This value didn\'t pass property parent validation.'
  }

  def __init__(self, default=None, required=True, strip=False, **kwargs):
    self._opts = {
      u'default': default,
      u'required': required,
      u'strip': strip
    }

    #I forgot I wrote this. I'm hilarious.
    #I forgot I did this. I'm brilliant.
    self._opts.update(kwargs)
  
  # --------------------------------------------------------------------------
  # Implementation of BaseValidator API
  
  def add_opt(self, opt_name, value):
    assert isinstance(opt_name, basestring)
    self._opts[opt_name] = value

  def get_opt_or_default(self, opt_name, ctx_opts, default=None):
    try:
      return self.get_opt(opt_name, ctx_opts)
    except InvalidArgumentError, e:
      pass
    return default
    
  def get_opt(self, opt_name, ctx_opts):
    if opt_name in ctx_opts.keys():
      #The opt was passed in on 'process'.
      return ctx_opts[opt_name]
    elif opt_name in self._opts.keys():
      #Use the opt set during initialization.
      return self._opts[opt_name]
    raise InvalidArgumentError(opt_name)

  messages = {'empty': 'This must not be empty.'}

  """
  THE process method.
  """
  def process(self, value, context={}, ctx_opts={}):
    if u'computed_data' not in context:
      context[u'computed_data'] = {}

    #do value.strip() if so instructed.
    if self.get_opt(u'strip', ctx_opts) and hasattr(value, 'strip'):
      value = value.strip()

    #if no value is provided and value is required, raise an exception.
    if self.is_empty(value, context, ctx_opts) == True:
      if self.get_opt(u'required', ctx_opts) == True:
        self.error('empty', value, context, ctx_opts, errorclass=EmptyError)
      return self.empty_value(context, ctx_opts)

    #run the 'convert' method on the value
    converted_value = self.convert(value, context, ctx_opts)

    #run the 'validate' method on the value
    self.validate(converted_value, context, ctx_opts)

    return converted_value

  def message_for_key(self, key, context, ctx_opts):
    overriding_key = u'%s_message' % key
    if overriding_key in ctx_opts:
      return ctx_opts[overriding_key]

    if key in self.messages.keys():
      return self.messages[key]
    else:
      for cls in inspect.getmro(self.__class__):
        if issubclass(cls, Filter):
          if key in cls.messages.keys():
            return cls.messages[key]
        else:
          break

    bolognium.ext.utils.log.error(u'Filter \'%s\' could not get error message '
      u'by key: \'%s\'.' % (self.__class__.__name__, key))
    return u'There was an unexpected error with this field.'

  """
  THE error method.
  """
  def error(self, key, value, context, ctx_opts, errorclass=InvalidDataError, **values):
    """Raise an InvalidDataError for the given key."""
    msg_template = self.message_for_key(key, context, ctx_opts)
    raise errorclass(msg_template % values, value, key=key, context=context)
  
  def error_original(self, key, value, context, errorclass=InvalidDataError, **values):
    translated_message = self.message(key, context, **values)
    raise errorclass(translated_message, value, key=key, context=context)
  
  # --------------------------------------------------------------------------
  # Defining a convenience API
  
  def convert(self, value, context, ctx_opts):
    """Convert the input value to a suitable Python instance which is 
    returned. If the input is invalid, raise an ``InvalidDataError``."""
    return value
  
  def validate(self, converted_value, context, ctx_opts):
    """Perform additional checks on the value which was processed 
    successfully before (otherwise this method is not called). Raise an 
    InvalidDataError if the input data is invalid.
    
    You can implement only this method in your validator if you just want to
    add additional restrictions without touching the actual conversion.
    
    This method must not modify the ``converted_value``."""
    pass
  
  def empty_value(self, context, ctx_opts):
    """Return the 'empty' value for this validator (usually None)."""
    default_value = self.get_opt_or_default(u'default', ctx_opts, default=None)
    return default_value
  
  def is_empty(self, value, context, ctx_opts):
    """Decide if the value is considered an empty value."""
    return value in (None, u'')
  
  def is_required(self, set_explicitely=False):
    required = self.get_opt(u'required')
    if required == True:
      return True
    return False


class CurrentUserFilter(Filter):
  messages = {
    'not_logged_in': u'You do not appear to be logged in!'
  }
    
  def convert(self, value, context, ctx_opts):
    return auth.current_user()

  def validate(self, converted_value, context, ctx_opts):
    if converted_value is None:
      self.error('not_logged_in', converted_value, context, ctx_opts)
      
  def is_empty(self, value, context, ctx_opts):
    return value in (None, '')

class LinkFilter(Filter):
  messages = {
    'malformed_address': u'This does not appear to be a valid web address.'
  }
    
  def convert(self, value, context, ctx_opts):
    if value[:4] != u'http':
      value = u'http://%s' % value
    return value

  def validate(self, converted_value, context, ctx_opts):
    scheme, domain, path, params, query, fragment = urlparse.urlparse(converted_value)
    if not scheme or not domain or len(domain.split(u'.')) < 2:
      self.error('malformed_address', converted_value, context, ctx_opts)
      
class EnabledFilter(Filter):
  messages = {
    'invalid_enabled_status': u'An unrecognised value was found for \'enabled\'.'
  }
    
  def convert(self, value, context, ctx_opts):
    try:
      value = int(value)
    except ValueError, e:
      self.error(u'invalid_enabled_status', converted_value, context, ctx_opts)
    if value == 0:
      return False
    elif value == 1:
      return True

class DateTimeFilter(Filter):
  messages = {
    'malformed_datetime': u'This does not appear to be a valid date string.'
  }
    
  def convert(self, value, context, ctx_opts):
    try:
      return datetime.datetime.strptime(value, u'%d %b %Y')
    except ValueError:
      raise
      pass
    self.error('malformed_datetime', value, context, ctx_opts)

class DomainNameFilter(Filter):
  messages = {
    'invalid_domain': u'This does not appear to be a valid domain.'
  }

  def convert(self, value, context, ctx_opts):
    if value[:4] != u'http':
      value = u'http://%s' % value
    domain = urlparse.urlparse(value)[1]
    if not domain or domain == u'':
      domain = urlparse.urlparse(u'http://%s' % value)[1]
    if not domain or len(domain.split(u'.')) < 2 or \
      len(domain.split(u' ')) > 1:
      self.error('invalid_domain', value, context, ctx_opts)
    return domain.lower()

  def validate(self, converted_value, context, ctx_opts):
    if not converted_value:
      self.error('invalid_domain', converted_value, context, ctx_opts)

class DecimalFilter(Filter):
  messages = {
    'not_a_decimal': u'This does not appear to be a decimal.'
  }

  def convert(self, value, context, ctx_opts):
    try:
      return decimal.Decimal(value)
    except:
      self.error('not_a_decimal', value, context, ctx_opts)

  def validate(self, converted_value, context, ctx_opts):
    if not isinstance(converted_value, decimal.Decimal):
      self.error('not_a_decimal', converted_value, context, ctx_opts)

class StringFilter(Filter):
  messages = {
    'invalid_option': u'This is not a valid option.',
    'invalid_type': u'This does not appear to be text.',
    'too_long': u'This field cannot be longer than %(max_length)d characters.',
    'too_short': u'This field must be at least %(min_length)d characters.',
  }

  def convert(self, value, context, ctx_opts):
    if not isinstance(value, basestring):
      classname = value.__class__.__name__
      self.error('invalid_type', value, context, ctx_opts)
    return value

  def validate(self, converted_value, context, ctx_opts):
    choices = self.get_opt_or_default(u'choices', ctx_opts, default=None)
    min_len = self.get_opt_or_default(u'min_length', ctx_opts, default=None)
    max_len = self.get_opt_or_default(u'max_length', ctx_opts, default=None)
    val_len = len(converted_value)
    if choices and converted_value not in choices:
      self.error('invalid_option', converted_value, context, ctx_opts)
    if min_len and val_len < min_len:
      self.error('too_short', converted_value, context, ctx_opts, min_length=min_len, length=val_len)
    if max_len and val_len > max_len:
      self.error('too_long', converted_value, context, ctx_opts, max_length=max_len, length=val_len)
    return

  def is_empty(self, value, context, ctx_opts):
    return value in (None, '')

class EmailFilter(Filter):
  messages = {
    u'single_at': u"The email address must contain a single '@'.",
    u'invalid_email_character': u'Invalid character %(invalid_character)s in email address %(emailaddress)s.',
  }
  def validate(self, emailaddress, context):
    parts = emailaddress.split('@')
    if len(parts) != 2:
      self.error('single_at', emailaddress, context, ctx_opts)
    localpart, domain = parts
    super(EmailFilter, self).validate(domain, context)
    self._validate_localpart(localpart, emailaddress, context)
  
  def _validate_localpart(self, localpart, emailaddress, context):
    match = re.search('([^a-zA-Z0-9\.\_])', localpart)
    if match is not None:
      values = dict(invalid_character=repr(match.group(1)), emailaddress=repr(emailaddress))
      self.error('invalid_email_character', localpart, context, ctx_opts, **values)

class IntegerFilter(Filter):
  messages = {
    'invalid_type': u'Validator got unexpected input (expected string, got "%(classname)s").',
    'invalid_number': u'Please enter a number.',
    'too_low': u'Number must be %(min)d or greater.',
    'too_big': u'Number must be %(max)d or smaller.'
   }
  
  def convert(self, value, context, ctx_opts):
    if not isinstance(value, (int, basestring)):
      classname = value.__class__.__name__
      self.error('invalid_type', value, context, ctx_opts, classname=classname)
    try:
      return int(value)
    except ValueError:
      self.error('invalid_number', value, context, ctx_opts)
  
  def validate(self, value, context, ctx_opts):
    min_int = self.get_opt_or_default(u'min_int', ctx_opts)
    max_int = self.get_opt_or_default(u'max_int', ctx_opts)
    if (min_int is not None) and (value < min_int):
      self.error('too_low', value, context, ctx_opts, min=min_int)
    if (max_int is not None) and (value > max_int):
      self.error('too_big', value, context, ctx_opts, max=max_int)


class CountryNameFilter(Filter):
  messages = {
    u'invalid_country': u'This is not a valid country.'
  }
 
  def convert(self, value, context, ctx_opts):
    country_names_to_codes = app.variable.get(u'country_names_to_codes', default={})
    country_codes_to_names = app.variable.get(u'country_codes_to_names', default={})
    try:
      country_code = country_names_to_codes[value.lower()]
      country_name = country_codes_to_names[country_code]
      return country_name
    except KeyError:
      self.error(u'invalid_country', value, context, ctx_opts)

class CountryCodeFilter(Filter):
  messages = {
    u'invalid_country_code': u'This is not a valid country code.'
  }
 
  def convert(self, value, context, ctx_opts):
    country_names_to_codes = app.variable.get(u'country_names_to_codes')
    country_codes_to_names = app.variable.get(u'country_codes_to_names')
    try:
      country_code = value.upper()
      country_name = country_codes_to_names[country_code]
      return country_code
    except KeyError:
      self.error(u'invalid_country_code', value, context, ctx_opts)

class BooleanFilter(Filter):
  def __init__(self, strip=True, *args, **kwargs):
    super(BooleanFilter, self).__init__(strip=strip, *args, **kwargs)

  messages = {
    u'not_bool': u'This should be True or False'
  }
 
  def convert(self, value, context, ctx_opts):
    if value in (0, u'0', u'false'):
      return False
    elif value in (1, u'1', u'true'):
      return True
    self.error(u'not_bool', value, context, ctx_opts)

  def is_empty(self, value, context, ctx_opts):
    return value in (None, '')


"""
The ListValidator. Applies a particular validator to each 
item in a list, raising ValidationError's as per usual.
@Params:
  'message' : The message displayed if any of the items fail.
  'validator' : The validator to check each field against.  
  'separator' : The character at which to split the string.  
"""

class KindFilter(Filter):
  messages = {
    u'invalid_kind': u'This must be an entity of Kind \'%(kind)\'.',
    u'not_a_key': u'This is not a valid relationship.',
    u'incomplete_key': u'This is not a valid relationship.',
    u'does_not_exist': u'Could not load entity by Key.'
  }
  def convert(self, value, context, ctx_opts):
    if isinstance(value, Model):
      if value.has_complete_key():
        return value.key
      else:
        self.error(u'incomplete_key', value, context, ctx_opts)
    return value
    
  def validate(self, converted_value, context, ctx_opts):
    """If this isn't a key or an instance, then it's gone bad."""
    if not isinstance(converted_value, ndb.model.Key):
      self.error(u'not_a_key', converted_value, context, ctx_opts)
    
    kind_opt = self.get_opt_or_default(u'kind', default=None)
    
    """If a kind was specified, check the value's kind against it."""
    if kind_opt and converted_value.kind() != kind_opt:
      self.error(u'invalid_kind', converted_value, context, ctx_opts, kind=kind_opt)

  def is_empty(self, value, context, ctx_opts):
    return value in (None, '')

class ImgMetaFilter(Filter):
  """Takes an id (of a db.Img instance) and returns the 'meta', suitable for 
    using as a reference to the img from other model instances."""
  messages = {
    u'image_error': u'This could not be understood as an image.',
    u'image_id_error': u'Did not understand the image id \'%(img_id)s\'.'
  }
  def convert(self, value, context, ctx_opts):
    if not value: return None
    if isinstance(value, basestring):
      try:
        value = int(value)
      except ValueError, e:
        self.error(u'image_error', value, context, ctx_opts, img_id=value)

    img = bolognium.ext.db.Key(u'Img', value).get()
    if img:
      return img.meta
    self.error(u'image_error', value, context, ctx_opts)

"""
Regex Based filtering for short strings.
"""
class RegexFilter(StringFilter):
  def __init__(self,
              lowercase=False,
              uppercase=False,
              numeric=False,
              extra_chars=None,
              to_lowercase=False,
              to_uppercase=False,
              expression=None,
              *args,
              **kwargs):
    super(RegexFilter, self).__init__(*args, **kwargs)
        
    """Whether or not to coerce to a certain case"""
    self._opts[u'to_lowercase'] = to_lowercase
    self._opts[u'to_uppercase'] = to_uppercase

    if expression is None:
      expression = r''

      if lowercase == True:
          expression += r'a-z'

      if uppercase == True:
          expression += r'A-Z'

      if numeric == True:
        expression += r'0-9'

      if extra_chars is not None:
        for char in extra_chars:
          if char in (u'.', u'^', u'$', u'*', u'+', u'?', u'{',  u'}',
              u'[', u']', u'\\', u'|' u'(' u')', u'-'):
            char = r'\%s' % char
          expression += char

    """Compile the expression"""
    expression = r'[%s]' % expression
    self._opts[u'expression'] = expression
    self._opts['compiled_expression'] = re.compile(expression)


  def convert(self, value, context, ctx_opts):
    if self.get_opt(u'to_uppercase', ctx_opts) == True:
      value = value.upper()
    elif self.get_opt(u'to_lowercase', ctx_opts) == True:
      value = value.lower()
    value = super(RegexFilter, self).convert(value, context, ctx_opts)
    return value
    
  messages = {
    'invalid_characters': u'This field contains invalid characters.'
  }

class MustNotContainFilter(RegexFilter):
  def validate(self, converted_value, context, ctx_opts):
    new_val = converted_value
    self.get_opt(u'compiled_expression', ctx_opts).sub(u'', converted_value)
    if len(new_val) < len(converted_value):
      self.error(u'invalid_characters', converted_value, context, ctx_opts)
    else:
      super(MustNotContainFilter, self).validate(converted_value, context, ctx_opts)

class MustOnlyContainFilter(RegexFilter):
  def validate(self, converted_value, context, ctx_opts):
    new_val = self.get_opt(u'compiled_expression', ctx_opts).sub(u'', converted_value)
    if len(new_val) > 0:
      self.error(u'invalid_characters', converted_value, context, ctx_opts)
    else:
      super(MustOnlyContainFilter, self).validate(converted_value, context, ctx_opts)
    return 

class SensibleUINameCharsOnly(RegexFilter):
  def __init__(self, *args, **kwargs):
    super(SensibleUINameCharsOnly, self).__init__(lowercase=True,
        uppercase=True, numeric=True, extra_chars=u'-+!#@$&*%', *args, **kwargs)

  def validate(self, converted_value, context, ctx_opts):
    super(SensibleUINameCharsOnly, self).validate(converted_value, context, ctx_opts)

class LowerCaseAndUnderScoresOnly(RegexFilter):
  def __init__(self, *args, **kwargs):
    super(LowerCaseAndUnderScoresOnly, self).__init__(lowercase=True,
        uppercase=False, numeric=False, extra_chars=u'_', *args, **kwargs)

class HtmlFilter(StringFilter):
  messages = {
    'invalid_html': u'The HTML input could not be interpreted or was illegal. If this continues, report it to an admin.',
    'lexer_missing': u'A code block reported an unsupported language: %(lang)s.'
  }

  def convert(self, value, context, ctx_opts):
    try:
      return self.validate_with_lxml(value, context, ctx_opts)
    except Exception, e:
      bolognium.ext.utils.log.error(u'There was an Exception while '
        u'parsing some html. MSG: %s' % e)
      raise
      self.error(u'invalid_html', value, context, ctx_opts)

  def validate_with_lxml(self, converted_value, context, ctx_opts):
    converted_value = converted_value.replace(u'<BR>', u'<br/>')
    converted_value = converted_value.replace(u'<BR/>', u'<br/>')
    converted_value = converted_value.replace(u'<BR />', u'<br/>')
    converted_value = converted_value.replace(u'<br>', u'<br/>')
    converted_value = converted_value.replace(u'<br />', u'<br/>')
    split_on_breaks = converted_value.split(u'<br/>')
    for k,line in enumerate(split_on_breaks):
      if not line.strip():
        if k > 0 and k < (len(split_on_breaks)-1):
          split_on_breaks[k] = u'</p><p>'
      elif k < (len(split_on_breaks)-1) and split_on_breaks[k+1].strip():
        split_on_breaks[k] += '<br/>'

    converted_value = u'<p>%s</p>' % u''.join(split_on_breaks)
    converted_value = '<html><body><div id="html_canvas">%s</div></body></html>' % converted_value

    #filter the input first, to remove anything illegal
    filtered_root = self.filter_with_lxml(converted_value, context, ctx_opts)

    self.parse_with_lxml(filtered_root, context, ctx_opts)

    #strip paragraph tags again and replace with break formatting before return
    #This is the version of the post that can go directly back into the editor.
    filtered_string = u''
    for elm in filtered_root.get_element_by_id('html_canvas'):
      elm_string = u''
      if elm.tag == u'p':
        elm_string = u'%s<br/><br/>' % etree.tostring(elm)[3:-4]
      else:
        elm_string = etree.tostring(elm)
        
      filtered_string += elm_string

    return filtered_string

  def filter_with_lxml(self, converted_value, context, ctx_opts):
    root = html.fromstring(converted_value)
    canvas = root.get_element_by_id('html_canvas')

    ALLOWED_TAG_ATTR_CONFIG = {
      u'strong': [],
      u'b': [],
      u'i': [],
      u'em': [],
      u'a': [u'href', u'title'],
      u'p': [],
      u'h2': [],
      u'h3': [],
      u'h4': [],
      u'ul': [],
      u'ol': [],
      u'img': [u'src', 'id', u'alt', u'height', u'width', u'class'],
      u'pre': [u'lang', u'style']
    }

    ALLOWED_TAGS = ALLOWED_TAG_ATTR_CONFIG.keys()
    ALLOWED_IMG_CLASSES = [u'img-float-left', u'img-float-right', u'img-display-block']

    for child in canvas.iterdescendants():
      #strip the tags if the elements are not allowed.
      if child.tag in ALLOWED_TAGS:
        #Check each attribute.
        for attr in child.attrib.keys():
          if attr not in ALLOWED_TAG_ATTR_CONFIG[child.tag]:
            del child.attrib[attr]
        
      if child.tag == u'p':
        #if contains a single <p> or <img> element it should be dissolved.
        if len(child) == 1 and child[0].tag in (u'p', u'img'):
          canvas.replace(child, child[0])
        if len(child) == 0 and len(etree.tostring(child)) < 8:
          canvas.remove(child)
      if child.tag == u'img':
        #filter the classes
        try:
          _clss = child.attrib[u'class']
          del child.attrib[u'class']
        except KeyError:
          pass
        else:
          cls = None
          for _cls in _clss.split(u' '):
            if _cls in ALLOWED_IMG_CLASSES:
              cls = _cls
              break
          if cls is not None:
            child.attrib[u'class'] = cls
    
    return root

  def parse_with_lxml(self, converted_value, context, ctx_opts):
    converted_value = deepcopy(converted_value)
    filtered_canvas = converted_value.get_element_by_id('html_canvas')
    imgs = []
    img_ids = []

    for child in filtered_canvas.iterdescendants():
      if child.tag == u'img':
        id_str = child.attrib.get(u'id')
        if id_str:
          id_str_parts = id_str.split(u':')
          if len(id_str_parts) == 2 and id_str_parts[0] == u'img_id':
            img_id = bolognium.ext.db.valid_id_or_default(id_str_parts[1], default=None)
            if img_id:
              img_ids.append(img_id)

      elif child.tag == u'pre':
        lang = child.attrib.get(u'lang')
        if lang:
          lexer = None
          if lang in (u'python', u'javascript', u'java'):
            lexer = get_lexer_by_name(lang)

          if lexer:
            code_block_contents = highlight(child.text, lexer, HtmlFormatter(linenos=True))
            code_block_elem = etree.Element(u'div')
            code_block_elem.set(u'class', u'highlighted-code-block')
            code_block_elem.insert(0, html.fromstring(code_block_contents))
            child.getparent().replace(child, code_block_elem)
          else:
            self.error(u'lexer_missing', converted_value, context, ctx_opts, lang=lang)

    if len(img_ids):
      imgs = [bolognium.ext.db.Key(u'Img', id) for id in img_ids]
      context[u'computed_data'][u'imgs'] = imgs

    del filtered_canvas.attrib[u'id']
    filtered_canvas.attrib[u'class'] = u'_parsed_html'
    
    context[u'computed_data'][u'parsed_body'] = \
      etree.tostring(filtered_canvas, encoding=unicode)

@ndb.tasklets.tasklet
def get_all_images(img_ids):
  futures = []
  img_keys = []
  for id in img_ids:
    img_keys.append(bolognium.ext.db.Key(u'Img', id))
  res_future = bolognium.ext.db.get_multi_async(img_keys)
  res = yield res_future
  raise ndb.tasklets.Return(res)

decimal_filter = DecimalFilter()
datetime_filter = DateTimeFilter()
#url_encodable_filter = UrlEncodableFilter()
lowercase_and_underscores_only = LowerCaseAndUnderScoresOnly()
sensible_uiname_chars_only = SensibleUINameCharsOnly()
current_user = CurrentUserFilter()
html_filter = HtmlFilter()
img_meta_filter = ImgMetaFilter()
datetime_filter = DateTimeFilter()
string_filter = StringFilter()
slug_filter = MustOnlyContainFilter(lowercase=True, 
  to_lowercase=True, extra_chars=(u'-'))
enabled_filter = EnabledFilter()
base_filter = Filter()

  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
  
