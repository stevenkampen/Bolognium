#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import RequestHandler, AjaxRequestHandler

import bolognium.ext.db as db
import bolognium.ext.auth as auth
import bolognium.ext.utils as utils

class Error403Handler(RequestHandler):
  def get(self, *args, **kwargs):
    return

class Error404Handler(RequestHandler):
  def get(self, *args, **kwargs):
    return

class Error405Handler(RequestHandler):
  def get(self, *args, **kwargs):
    return


class Error500Handler(RequestHandler):
  def get(self, *args, **kwargs):
    return
