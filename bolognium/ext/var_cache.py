#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from google.appengine.api import memcache
from google.appengine.ext import deferred
from google.appengine.api import mail
from google.appengine.runtime import apiproxy_errors
from google.appengine.api.labs import taskqueue

import bolognium.ext.db as db
import bolognium.ext.utils as utils

import time
import decimal
import os
import sys
import hashlib
import yaml
import random
import string


def get(name, default=None, raw=False):
  var = db.Variable.get_by_id(_mc_name(name))
  if var is not None:
    #make value the actual value, whether is came from memcache or the datstore
    value = var.value if isinstance(var, app.models.Variable) else var

    #parse and return, or just return
    if raw == True:
      return value

    #return end value
    return utils.json.loads(value)

  #not in memcache or datastore so return default
  return default
  
def set(name, value, cache_time=3600):
  name = db.string_or_default(name, None)
  assert name
  new_value = utils.json.dumps(value)

  var = db.Variable.get_or_insert_async(_mc_name(name), variable_name=name, value=new_value).get_result()
  if var.has_complete_key():
    if var.value != new_value:
      var.value = new_value
      var.put_async()
  else:
    var.put_async()
  return var

def _mc_name(name):
  return u'/VARIABLE/%s' % name
