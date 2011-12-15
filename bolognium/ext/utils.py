#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from google.appengine.api import memcache
from google.appengine.ext import deferred
from google.appengine.api import mail
from google.appengine.runtime import apiproxy_errors
from google.appengine.api.labs import taskqueue

import json

import bolognium.ext.db as db
import bolognium.ext.auth as auth
import bolognium.ext.template as template
from bolognium.ext.config import get_config

import time
import decimal
import os
import re
import datetime
import sys
import hashlib
import yaml
import random
import string

def is_local():
  return True if os.environ[u'SERVER_SOFTWARE'][:3].lower() == u'dev' else False

def is_debug():
  default = True
  
  """The cache time"""
  debug_value_cache_time = get_config(u'debug_value_cache_time', 
    default=60, cache_time=3600)

  debug = get_config(u'debug', default=default, 
    cache_time=debug_value_cache_time)
  return debug if debug in (True, False) else default

def base_url():
  return get_config(u'base_url')

def log_timing(func):
  def wrapper(*args, **kwargs):
    t1 = time.time()
    res = func(*args, **kwargs)
    t2 = time.time()
    log.debug(u'Function \'%s\' request took %0.3f ms' % 
      (func.__name__, (t2-t1)*1000.0))
    return res
  return wrapper

def random_string(length):
  return unicode(u''.join([random.choice(string.letters + string.digits) 
    for i in range(length)]))

def random_integer(start, stop, step=None):
  return random.randrange(start, stop, step)

def knuth_hash(i):
  return (i*2971215073) % 2**32

def update_datetime(_datetime, _timedelta):
  _datetime += _timedelta
  return _datetime

def format_string(s, max_length=None):
  pass
    
def make_salt():
  return os.urandom(16).encode('hex')

def make_hash(salt, password):
  return sha256_hash(salt + password)

def sha256_hash(input):
  return hashlib.sha256(input).hexdigest()

def md5_hash(input):
  return hashlib.md5(input).hexdigest()

def _fake_login_credentials(password=None):
  if not password:
    password = random_string(8)
  salt = make_salt()
  return {'salt': salt, 'password': make_hash(salt=salt,
      password=password)}

def event_codes():
  conf = get_config(u'events', default={})
  return conf.values()

def event_keys():
  conf = get_config(u'events', default={})
  return conf.keys()

def camel_case(s):
  return u''.join([word.capitalize() for word in s.split((u'_'))])

def un_camel_case(s):
  s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
  return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
  #return u'_'.join([word.lower() for word in re.findall('[A-Z][^A-Z]*', s)])

def event_code(event):
  conf = get_config(u'events', default={})
  try:
    return conf[event]
  except KeyError:
    return None

class AppLogsHandler(logging.Handler):

  def emit(self, record):
    """Emit a record.

    This implementation is based on the implementation of
    StreamHandler.emit()."""
    try:
      message = self._AppLogsMessage(record)
      if isinstance(message, unicode):
        message = message.encode("UTF-8")

      if auth.is_current_user_admin():
        title = u'%s [%s:%s] inside \'%s()\'' % (record.levelname, 
          record.filename, record.lineno, record.funcName)

        try:
          sess = auth.get_session()
          current_log_records = sess.get(u'log_records', None)
          if not isinstance(current_log_records, list):
            sess[u'log_records'] = []
          if title:
            sess[u'log_records'].append({u'title': title, u'payload': message})
        except (AttributeError, KeyError), e:
          raise
    except (KeyboardInterrupt, SystemExit):
      raise
    except:
      self.handleError(record)

  def _AppLogsMessage(self, record):
    """Converts the log record into a log line."""



    message = self.format(record).replace("\r\n", "\0")
    message = message.replace("\r", "\0")
    message = message.replace("\n", "\0")

    return "LOG %d %d %s\n" % (self._AppLogsLevel(record.levelno),
                               long(record.created * 1000 * 1000),
                               message)

  def _AppLogsLevel(self, level):
    """Converts the logging level used in Python to the API logging level"""
    if level >= logging.CRITICAL:
      return 4
    elif level >= logging.ERROR:
      return 3
    elif level >= logging.WARNING:
      return 2
    elif level >= logging.INFO:
      return 1
    else:
      return 0

def convertToHumanReadable(date_time):
  """
  converts a python datetime object to the 
  format "X days, Y hours ago"

  @param date_time: Python datetime object

  @return:
    fancy datetime:: string
  """
  current_datetime = datetime.datetime.now()
  delta = str(current_datetime - date_time)
  if delta.find(',') > 0:
    days, hours = delta.split(',')
    days = int(days.split()[0].strip())
    hours, minutes = hours.split(':')[0:2]
  else:
    hours, minutes = delta.split(':')[0:2]
    days = 0
  days, hours, minutes = int(days), int(hours), int(minutes)
  datelets =[]
  years, months, xdays = None, None, None
  plural = lambda x: 's' if x!=1 else ''
  if days >= 365:
    years = int(days/365)
    datelets.append('%d year%s' % (years, plural(years)))
    days = days%365
  if days >= 30 and days < 365:
    months = int(days/30)
    datelets.append('%d month%s' % (months, plural(months)))    
    days = days%30
  if not years and days > 0 and days < 30:
    xdays =days
    datelets.append('%d day%s' % (xdays, plural(xdays)))    
  if not (months or years) and hours != 0:
    datelets.append('%d hour%s' % (hours, plural(hours)))    
  if not (xdays or months or years):
    datelets.append('%d minute%s' % (minutes, plural(minutes)))    
  return ', '.join(datelets) + ' ago.'

#setup the logger
log = logging.getLogger(u'.raw')
if is_debug(): log.setLevel(logging.DEBUG-1)
#log.addHandler(AppLogsHandler())
