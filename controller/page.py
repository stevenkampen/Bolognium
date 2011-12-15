#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.api import memcache

from bolognium.ext.request_handler import RequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

import datetime

class PageHomeHandler(RequestHandler):
  def get(self, *args, **kwargs):
    self.set(u'posts', db.Post.list_for_current_user())

class PageStyleTestHandler(RequestHandler):
  def get(self, *args, **kwargs):
    pass

