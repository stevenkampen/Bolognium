#!/usr/bin/env python
# -*- coding: utf-8 -*-

# define custom routes
routes = [
	('home', '/', {'controller': 'page', 'action': 'home'}),
	('style-test', '/style-test', {'controller': 'page', 'action': 'style-test'}),
	('admin-dashboard', '/admin', {'controller': 'admin', 'action': 'dashboard'}),
  ('rpc-endpoint', '/rpc/:action', {'controller': 'rpc', 'action': ':method_name'})
]
