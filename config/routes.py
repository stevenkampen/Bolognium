#!/usr/bin/env python
# -*- coding: utf-8 -*-

# define custom routes
routes = [
	('home', '/', {'controller': 'page', 'action': 'home'}),

  #main posts list
  ('posts-index', '/posts', {'controller': 'post', 'action': 'index'}),
  ('posts-index', '/posts/', {'controller': 'post', 'action': 'index'}),

  #post view
	('post-view', '/posts/:id/:slug', {'controller': 'post', 'action': 'view', 'kwargs': {'id': None, u'slug': None}}),

	('login-page', '/login', {'controller': 'user', 'action': 'login'}),
	('logout-page', '/logout', {'controller': 'user', 'action': 'logout'}),
	('admin-dashboard', '/admin', {'controller': 'admin', 'action': 'dashboard'}),
	('contact-page', '/contact', {'controller': 'page', 'action': 'contact'}),
	('about-page', '/about', {'controller': 'page', 'action': 'about'}),
  ('sitemap-index', '/sitemap', {'controller': 'sitemap', 'action': 'index'}),
  ('sitemap-robots', '/robots.txt', {'controller': 'sitemap', 'action': 'robots'}),
  ('rpc-endpoint', '/rpc/:action', {'controller': 'rpc', 'action': ':method_name'})
]
