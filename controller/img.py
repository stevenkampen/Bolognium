#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import RequestHandler, AjaxRequestHandler
from bolognium.ext.auth import require_admin, require_user, require_anon
import bolognium.ext.db as db
import bolognium.ext.auth as auth
import bolognium.ext.utils as utils

class ImgIndexHandler(RequestHandler):
  @require_admin()
  def get(self, *args, **kwargs):
    imgs = db.Img.list_for_admin()
    self.set(u'imgs', imgs)
