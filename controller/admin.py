#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import RequestHandler, AjaxRequestHandler
from bolognium.ext.auth import require_admin, require_user, require_anon
import bolognium.ext.db as db
import bolognium.ext.auth as auth
import bolognium.ext.utils as utils

class AdminDashboardHandler(RequestHandler):
  @require_admin()
  def get(self, *args, **kwargs):
    pass

class AdminUserIndexHandler(RequestHandler):
  @require_admin()
  def get(self, *args, **kwargs):
    self.set(u'users', db.User.list_for_admin())

class AdminUserViewHandler(RequestHandler):
  @require_admin()
  def get(self, id=None, *args, **kwargs):
    user = app.models.User.load_if_permitted(id, u'view')
    if user:
      self.set(u'user', campaign)
    else:
      self.error(404)

class AdminPostIndexHandler(RequestHandler):
	def get(self, *args, **kwargs):
		self.set(u'posts', db.Post.list_for_admin())
