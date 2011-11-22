#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, UndefinedError
from jinja2.loaders import split_template_path
from jinja2.utils import open_if_exists

import sys, os, logging

def get_tpl_env():
	return Environment(loader=CustomLoader(u'view'))

class CustomLoader(FileSystemLoader):
	"""
	My Custom Template Loader
	"""

	def get_source(self, environment, template):
		pieces = split_template_path(template)
		for searchpath in self.searchpath:
			filename = os.path.join(searchpath, *pieces)
			f = open_if_exists(filename)
			if f is None:
				continue
			try:
				contents = f.read().decode(self.encoding)
			finally:
				f.close()

			mtime = os.path.getmtime(filename)
			def uptodate():
				try:
					return os.path.getmtime(filename) == mtime
				except OSError:
					return False
			return contents, filename, uptodate
		raise TemplateNotFound(template)

def get_template(*args, **kwargs):
  return template_env.get_template(*args, **kwargs)

template_env = get_tpl_env()
