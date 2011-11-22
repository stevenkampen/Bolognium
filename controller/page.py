#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.api import memcache

from bolognium.ext.request_handler import RequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db
#import bolognium.ext.metrics as metrics

import datetime

class PageHomeHandler(RequestHandler):
  def get(self, *args, **kwargs):
    self.set(u'posts', db.Post.list_for_current_user())

class PageAboutHandler(RequestHandler):
  def get(self, *args, **kwargs):
    pass

class PageContactHandler(RequestHandler):
  def get(self, *args, **kwargs):
    self.set(u'error', None)
    self.set(u'errors', {})
    self.set(u'input', {})

  def post(self, *args, **kwargs):
    try:
      input = {}
      errors = {}
      for field in (u'from_name', u'from_email', u'message'):
        input[field] = self.request.get(field, None)
        if not input[field]:
          errors[field] = u'This field is invalid or missing.'
      utils.send_contact(
        from_name=input[u'from_name'],
        from_email=input[u'from_email'],
        message=input[u'message']
      )
    except Exception, e:
      utils.log.error(u'There was an error! MSG: %s' % e)
      self.message(u'There was an error sending your contact message!', u'error')
      self.set(u'error', e)
      self.set(u'errors', errors)
      self.set(u'input', input)
    else:
      self.message(u'Your contact message was successfully sent.', u'success')
      return self.redirect(u'/')
