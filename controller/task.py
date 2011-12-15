#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import TaskRequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db
from google.appengine.api import memcache
import logging, time, datetime

class TaskPrepareModelHandler(TaskRequestHandler):
  def post(self, id=None, *args, **kwargs):
    _dict = db.model_dict
    model_class = _dict.get(model.string_or_default(id, default=u''))
    if model_class is None:
      raise Exception(u'Model %s not found' % model_name)
    if hasattr(model_class, u'_prepare'):
      model_class._prepare()
    
    
