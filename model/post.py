#!/usr/bin/env python
# -*- coding: utf-8 -*-

import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

class Post(db.Model):
  type = db.StringProperty(choices=[u'blog'], default=u'blog')

  title = db.StringProperty(whitelisted=True, required=True, indexed=False)
  slugs = db.SlugProperty(whitelisted=True, repeated=True)
  teaser = db.StringProperty(whitelisted=True, required=True, indexed=False)

  raw_body = db.TextProperty(whitelisted=True, default=None)
  body = db.PostBodyProperty(whitelisted=True, default=None)
  parsed_body = db.TextProperty(whitelisted=True, default=None)

  imgs = db.KeyProperty(repeated=True, whitelisted=True)

  #tags = db.StringListProperty()
  enabled = db.BooleanProperty(whitelisted=True, default=False)

  created = db.CreatedDateTimeProperty()
  updated = db.UpdatedDateTimeProperty()

  def get_fancy_created_time(self):
    return utils.convertToHumanReadable(self.created)

  @property
  def slug(self):
    return self.slugs[0] if len(self.slugs) else u''

  @classmethod
  def _list_for_current_user(cls, is_logged_in=False):
    return cls.query().filter(
      cls.enabled == True, 
    ).order(-cls.created).fetch(100)
  
  @classmethod
  def _list_for_admin(cls, is_admin=False):
    """Don't call this directly. User model.list_for_admin()"""
    if is_admin:
      return cls.query().fetch(100)
    return []

  def permalink(self, absolute=True):
    url_string = u'/posts/%s' % self.key.id()
    if len(self.slugs):
      url_string += u'/%s' % self.slugs[0]
    if absolute is True:
      url_string = u'%s%s' % (utils.get_config(u'domain'), url_string)
    return url_string

  def last_updated(self):
    return self.updated
