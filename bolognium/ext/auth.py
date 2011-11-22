#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import string
import logging
from random import choice
from hashlib import sha1, md5
import os

from google.appengine.api import memcache
from google.appengine.api import users

import bolognium
from bolognium.ext import db
import beaker

def get_session():
  #return os.environ[u'beaker.get_session']() #not sure when this works
  return os.environ[u'beaker.session'] #at the moment this works locally
  
def clear_old_sessions():
  pass #reimplement

def clear_log_records():
  if get_session().get(u'log_records', None):
    del get_session()[u'log_records']

def clear_messages():
  if get_session().get(u'messages', None):
    del get_session()[u'messages']


def google_id_string(name=None):
  user = users.get_current_user()
  if user:
    username = user.nickname()
    user_id = user.user_id()
    return u'[id:%s][username:%s]' % (user_id, username)
  return ''

def is_current_user_admin(name=None):
  return users.is_current_user_admin()

"""Used by things in places."""
def is_anonymous():
  return not bool(current_user())

"""Used by things in places."""
def is_logged_in():
  return bool(current_user())

"""Used by things in places."""
def logged_in_user():
  return current_user()
  
def current_user_for_client_side():
  u = current_user()
  if u:
    user_cs = u.to_client_side()
    user_cs_js = bolognium.ext.utils.json.dumps(user_cs)
    return user_cs_js
  else:
    return u'null'

def current_user(name=None):
  user = get_session().get(u'user', None)

  #if asking about specific attributes...
  if name and user:
    return user.check_for_attribute(name=name)
  
  return user

def require_idz_secure():
  def idz_secure_required(func):
    def wrapped_f(self, *args, **kwargs):
      if True:
        func(self, *args, **kwargs)
      else:
        return self.error(401)
    return wrapped_f
  return idz_secure_required

def require_admin():
  def admin_required(func):
    def wrapped_f(self, *args, **kwargs):
      if users.is_current_user_admin():
        func(self, *args, **kwargs)
      else:
        return self.redirect(users.create_login_url(self.request.uri))
    return wrapped_f
  return admin_required

def require_user():
  def user_required(func):
    def wrapped_f(self, *args, **kwargs):
      if self.current_user():
        func(self, *args, **kwargs)
      else:
        return self.error(404)
    return wrapped_f
  return user_required

def require_anon():
  def anon_required(func):
    def wrapped_f(self, *args, **kwargs):
      if not is_logged_in():
        func(self, *args, **kwargs)
      else:
        return self.error(404)
    return wrapped_f
  return anon_required
