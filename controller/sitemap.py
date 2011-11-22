#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import RequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

class SitemapIndexHandler(RequestHandler):
  def get(self, *args, **kwargs):
    self.response.headers.add_header('Content-Type', 'application/xml')
    self.set('posts', db.Post.list_for_current_user())

class SitemapRobotsHandler(RequestHandler):
  def get(self, *args, **kwargs):
    pass

class SitemapReIndexHandler(RequestHandler):
  def get(self, *args, **kwargs):
    pass
