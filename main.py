#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(current_path, u'bolognium/lib'))
sys.path.append(os.path.join(current_path, u'bolognium/ext'))

from bolognium.ext import db as db
from bolognium.ext import utils as utils
from bolognium.ext import auth as auth
from bolognium.ext import webapp as webapp
from bolognium.ext import router as router

db.setup_models()

application = webapp.WSGIApplication(router.load_route_map(), 
  debug=utils.is_debug())
