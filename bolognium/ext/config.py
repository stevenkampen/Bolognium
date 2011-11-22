#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.api import memcache
import bolognium

def get_config(key, namespace=u'base', flush_memcache=False, default=None, cache_time=3600):
  cache_time = bolognium.ext.db.positive_int_or_default(cache_time, default=None)
  if cache_time is None:
    raise Exception(u'cache_time must be a positive integer.')
  mc_key = u'/CONFIG/%s/%s' % (namespace,key)
  data = None
  if flush_memcache == False:
    data = memcache.get(mc_key)

  if data is None:
    try:
      data = getattr(__import__(u'config.%s' % namespace, {}, {}, [u'config'], -1), key, None)
      try:
        memcache.set(mc_key, data)
      except ValueError:
        pass
    except (ImportError, AttributeError):
      raise

  return data if data else default
