#!/usr/bin/env python

import logging, sys, os
current_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(current_path, u'bolognium/lib'))
sys.path.append(os.path.join(current_path, u'bolognium/ext'))

import beaker
from beaker.middleware import SessionMiddleware

def webapp_add_wsgi_middleware(app):
  app = SessionMiddleware(app, config={u'session.type': u'ext:google'})
  return app

