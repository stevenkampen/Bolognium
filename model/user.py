#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bolognium.ext.db as db
import bolognium.ext.auth as auth
import bolognium.ext.utils as utils

class User(db.Model):
  
  #first and last name will be widely used
  username = db.StringProperty(
      required=True,
      whitelisted=True
  )
  
  email = db.EmailProperty()
  password = db.StringProperty(default=None)
  salt = db.StringProperty(default=None)

  #app specific status
  enabled = db.EnabledProperty(whitelisted=True)

  #this should take care of itself
  updated = db.UpdatedDateTimeProperty()
  created = db.CreatedDateTimeProperty()

  def check_for_attribute(self, name=None):
    if name == u'id':
      return self.key.id()
    if name == u'key':
      return self.key
    parts = name.split(u'.')

    """Loop through with the pointer"""
    _part = self
    for part in parts:
      _part = getattr(_part, part, None)
      if _part is None: break

    return _part
    
  def reload_from_datastore(self):
    self = self.get_by_id(self.key.id())
    return self

  @classmethod
  def has_permission(self, instance=None, action=None, user=None):
    if instance:
      if action in (u'view', u'edit'):
        if auth.is_current_user_admin() or \
          (user and instance.key == user.key):
          return True
    return False

  @classmethod
  def _list_for_admin(cls, is_admin=False):
    """Don't call this directly. User db.list_for_admin()"""
    if is_admin:
      return cls.query()
    return []

  @classmethod
  def get_with_login_details(cls, email, password):
    user = cls.query(cls.email == email).get()
    if user and utils.make_hash(user.salt, password) == user.password:
      return user
    return None
