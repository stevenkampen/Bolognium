#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bolognium.ext.request_handler import RequestHandler
import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

class PostLandingPageHandler(RequestHandler):
	def get(self, *args, **kwargs):
		pass

class PostIndexHandler(RequestHandler):
	def get(self, *args, **kwargs):
		self.set(u'posts', db.Post.list_for_current_user())

class PostViewHandler(RequestHandler):
  def get(self, id=None, slug=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    assert post_id, u'No post_id!'
    if post_id:
      post = db.Key(u'Post', post_id).get()
      assert post, u'No post by ID: %s' % post_id
      if post:
        if slug:
          assert slug in post.slugs, u'Invalid slug \'%s\' for post by ID \'%s\'.' % (slug, post_id)
        else:
          pass #no slug, which is ok. The id is correct.
        #set the post
        self.set(u'post', post)
      else:
        return self.error(404)
        
    self.set(u'post_id', post_id)
    self.set(u'slug', slug)

class PostAddHandler(RequestHandler):
  @auth.require_admin()
  def get(self, *args, **kwargs):
    self.set(u'input', {})
    self.set(u'errors', {})

  @auth.require_admin()
  def post(self, *args, **kwargs):
    """Try it, maybe error, or maybe success and redirect."""
    post, e, context = db.Post.create_from_input(
      input_schema=[
        {u'name': u'title', u'ctx_opts': {u'max_length': 150, u'required': True}},
        {u'name': u'slugs', u'ctx_opts': {u'max_length': 100, u'required': True}},
        {u'name': u'teaser', u'ctx_opts': {u'max_length': 500, u'required': True}},
        {u'name': u'body', u'ctx_opts': {u'required': True, u'strip': True}}
      ],
      input_data = self.request.get_post_arguments()
    )
    if e:
      #VALIDATION FAILED
      details = e.details()
      context = details.context()
      self.set(u'errors', e.error_dict())
      self.set(u'input', context[u'sanitized_input'])
      self.set(u'post', None)
    else:
      """Success!"""
      self.message(u'The Post <strong>\'%s\'</strong> was created. It should appear shortly.' % post.title, 'success')
      return self.redirect(u'/admin')

class PostEditHandler(RequestHandler):
  @auth.require_admin()
  def get(self, id=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    assert post
    if post:
      self.set(u'post_id', post_id)
      self.set(u'post', post)
      self.set(u'errors', {})
      self.set(u'input', {})

  @auth.require_admin()
  def post(self, id=None, *args, **kwargs):
    """Try it, maybe error, or maybe success and redirect."""
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    assert post
    e, context = post.update_from_input(
      input_schema=[
        {u'name': u'title', u'ctx_opts': {u'max_length': 150, u'required': True}},
        {u'name': u'slugs', u'ctx_opts': {u'max_length': 100}},
        {u'name': u'teaser', u'ctx_opts': {u'max_length': 500}},
        {u'name': u'enabled'},
        u'body'
      ],
      input_data = self.request.get_post_arguments()
    )
    if e:
      #VALIDATION FAILED
      details = e.details()
      context = details.context()
      self.set(u'post', post)
      self.set(u'post_id', post_id)
      self.set(u'error', e)
      self.set(u'errors', e.error_dict())
      self.set(u'input', context[u'sanitized_input'])
    else:
      """Success!"""
      self.message(u'The Post <strong>\'%s\'</strong> was updated.' % post.title, u'success')
      if post.enabled:
        return self.redirect(post.permalink())
      else:
        return self.redirect(u'/post/edit/%s' % post_id)
