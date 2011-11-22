#!/usr/bin/env python
# -*- coding: utf-8 -*-

import google.appengine.ext.webapp as webapp2
from google.appengine.ext.webapp import blobstore_handlers

import bolognium.ext.utils as utils
import bolognium.ext.db as db

import sys, os, logging

class Response(webapp2.Response):
  pass

class Request(webapp2.Request):
  def abort(self, *args, **kwargs):
    webapp2.abort(*args, **kwargs)
    
  """Get the POST args"""
  def get_post_arguments(self):
    if not hasattr(self, u'_post_args'):
      setattr(self, u'_post_args', {})
      for key,value in self.POST.iteritems():
        try:
          self._post_args[key] = self.POST.getone(key)
        except KeyError:
          pass
    return self._post_args

  """The path"""
  @property
  def path(self):
    if not hasattr(self, u'_path'):
      self._path = self.environ.get(u'PATH_INFO', u'')
    return self._path

  """The path parts"""
  @property
  def path_parts(self):
    if not getattr(self, u'_path_parts', None):
      self.parse_path()
    return self._path_parts
     
  """The request method property"""
  @property
  def request_method(self):
    if not hasattr(self, u'_request_method'):
      self._request_method = self.environ.get(u'REQUEST_METHOD', None)
    return getattr(self, u'_request_method', None)

  """get argument coerced to True or False"""
  def get_bool(self, name):
    return True if self.get_range(name, min_value=0, max_value=1, default=0) == 1 else False

  """get argument coerced to True or False"""
  def get_int(self, name):
    return db.valid_id_or_default(self.get(name), default=None)


class WSGIApplication(webapp2.WSGIApplication):
  """A WSGI-compliant application."""

  #: Class used for the request object.
  request_class = Request

  #: Class used for the response object.
  response_class = Response

  #: A general purpose flag to indicate development mode: if True, uncaught
  #: exceptions are raised instead of using ``HTTPInternalServerError``.
  debug = False

  def __init__(self, router, debug=False, config=None):
    """Initializes the WSGI application.

    :param router:
        The router, loaded with the routes.
    :param debug:
        True to enable debug mode, False otherwise.
    :param config:
        A configuration dictionary for the application.
    """
    self.debug = debug
    self.registry = {}
    self.error_handlers = {}
    
    self.set_globals(app=self)
    self.config = self.config_class(config)
    self.router = router

def _get_handler_methods(handler):
  return webapp2._get_handler_methods(handler)

