#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import RequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db
import hashlib

class UserAccountHandler(RequestHandler):
  @auth.require_user()
  def get(self, *args, **kwargs):
    return

class UserLogoutHandler(RequestHandler):
  @auth.require_user()
  def get(self, *args, **kwargs):
    self.logout_user()
    self.message(u'You have been logged out.', u'success')
    self.redirect(u'/')

class UserLoginHandler(RequestHandler):
  @auth.require_anon()
  def get(self, *args, **kwargs):
    self.set_body_class(u'single_column')
    self.set(u'redirect_to', u'/account')

  @auth.require_anon()
  def post(self, *args, **kwargs):
    self.set_body_class(u'single_column')
    user = db.User.get_with_login_details(
      email=self.request.get(u'email', None),
      password=self.request.get(u'password', None)
    )
    if not user:
      """User not found. Set error message."""
      self.message(u'The login credentials you supplied were invalid.', u'error')
    elif user.enabled:
      """Success. Will now redirect to the specified address or root"""
      self.login_user(user)
      return self.redirect(self.request.get(u'redirect_to', u'/account'))
    else:
      """The login form will be displayed again"""
      self.message(u'You\'re account is not active.', u'error')
      return self.redirect(u'/login')
