#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import CronRequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

class CronHourlyHandler(CronRequestHandler):
  def work(self, *args, **kwargs):
    pass

class CronDailyHandler(CronRequestHandler):
  def work(self, *args, **kwargs):
    pass
