#!/usr/bin/env python
import bolognium.ext.db as db
import bolognium.ext.var_cache as var_cache
from bolognium.ext.config import get_config

import logging

class Variable(db.Model):
 
  variable_name = db.StringProperty(required=True, whitelisted=True)
  value = db.JsonProperty(whitelisted=True)

  @classmethod
  def prepare(cls):
    for name,row in get_config(u'defaults', u'variables', flush_memcache=True, default=[]):
      #instantiate the entity
      try:
        var = var_cache.set(name, row)
      except Exception, e:
        logging.error(u"Error while creating entity of kind '%s'. MSG: %s" % (cls.__name__, e))
 
