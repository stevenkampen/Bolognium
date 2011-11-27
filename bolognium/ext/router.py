#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.lib.routes.mapper import Mapper as RoutesMapper
import bolognium.ext.utils as utils
import bolognium.ext.webapp as webapp
from bolognium.ext.config import get_config

import sys, os

class Mapper(RoutesMapper):
  def dispatch(self, request, response):
    """Routes the request to a handler and action method, 
    and runs the dispatch method on it."""
    path = request.path
    matched_route = self.match(path)
    if matched_route is not None:
      if matched_route[u'controller'] == u'rpc':
        action_parts = matched_route[u'action'].split(u'_')
        controller = action_parts[0]
        action = u'%s_rpc' % u'_'.join(action_parts[1:])
      else:
        controller = matched_route[u'controller']
        action = matched_route[u'action']
      del matched_route[u'action']
      del matched_route[u'controller']
        
      method_kwargs = matched_route
    else:
      """Splitting path by '/' and routing to default
      controller/action endpoint"""
      action = None
      controller = None
      method_kwargs = {}
      if path.startswith(u'/'):
        path = path[1:]
      path_parts = path.split(u'/')
      if len(path_parts) >= 2:
        controller = path_parts[0]
        action = path_parts[1]
        if len(path_parts) >= 3:
          method_kwargs[u'id'] = path_parts[2]

    if controller and action:
      #replace hyphens with underscores in the action
      action = action.replace(u'-', u'_')
      """build the module and controller class names from the route parameters."""
      module_name = u'controller.%s' % controller
      action = utils.camel_case(action)
      controller = utils.camel_case(controller)
      class_name = u'%s%sHandler' % (controller, action)

      """ Initialize matched controller from given module."""
      try:
        __import__(module_name, {}, {}, [''], -1)
      except ImportError, e:
        utils.log.warn(u"Could Not Import Module: %s. MSG: %s" % (module_name, e))
      else:
        """return controller class"""
        module = sys.modules[module_name]
        _handler = getattr(module, class_name, None)
        utils.log.debug(u"###########REQUEST############ Controller: \'%s\' RequestHandler | Class: \'%s\' | Method \'%s\'." % (module_name, class_name, request.request_method.upper()))
        if _handler:
          _handler = _handler(request, response)
          method = getattr(_handler, request.request_method.lower(), None)
          return _handler.dispatch(method=method, controller=controller, 
            action=action, method_kwargs=method_kwargs)
        else:
          utils.log.warn(u"Could Not Find RequestHandler classs by name: %s." % class_name)
          

    request.abort(404)

def load_route_map():
  # init route map
  route_map = Mapper(explicit=True)
  #setup all routes from the routes config
  for route in get_config(u'routes', u'routes', flush_memcache=True, default=[]):
    kwargs = route[2][u'kwargs'] if route[2].get(u'kwargs') else {}
    route_map.connect(route[0], route[1], controller=route[2][u'controller'], action=route[2][u'action'], **kwargs)
  return route_map
    
