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
    pass

  @auth.require_admin()
  def post(self, *args, **kwargs):
    utils.log.debug(self.request.get_post_arguments())
    """
    Saves a new News item.
    """
    context = {}
    filtered_input = {}
    fields = [
      (u'title', dict(strip=True, required=True)),
      (u'teaser', dict(strip=True, required=True)),
      (u'body',  dict(required=True)),
    ]
    error_count = 0
  
    #get the standard properties
    for field_data in fields:
      field_name, ctx_opts = field_data[0],field_data[1]
      try:
        filtered_input[field_name] = db.Post.filter_property(field_name, self.request.POST.get(field_name), 
          context=context, ctx_opts=ctx_opts)
      except db.FilterError, e:
        error_count += 1
        self.set_template_error(field_name, e.msg())

    #pull out slug
    try:
      slug = db.Post.filter_property(u'slug', self.request.POST.get(u'slug'), 
        context=context, ctx_opts=dict(strip=True, required=False))
      if slug: filtered_input[u'slugs'] = [slug]
    except db.FilterError, e:
      error_count += 1
      self.set_template_error(u'slug', e.msg())

    filtered_input[u'parsed_body'] = context[u'computed_data'].get(u'parsed_body', u'')
    filtered_input[u'imgs'] = context[u'computed_data'].get(u'imgs', [])

    if error_count == 0:    
      post = db.Post(**filtered_input)
      post.put()
      self.message(u'The Post <strong>\'%s\'</strong> has been created.' % 
        post.title, u'success')
      return self.redirect(u'/post/edit/%s' % post.key.id())
    self.message(u'There was an error with the submission.', u'error')

class PostEditHandler(RequestHandler):
  @auth.require_admin()
  def get(self, id=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    if post:
      self.set(u'post_id', post_id)
      self.set(u'post', post)
    else:
      self.error(404, abort=True)

  @auth.require_admin()
  def post(self, id=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    self.set(u'post_id', post_id)
    self.set(u'post', post)
    if post:
      context = {}
      filtered_input = {}
      fields = [
        (u'title', dict(strip=True, required=True)),
        (u'teaser', dict(strip=True, required=True)),
        (u'body',  dict(required=True)),
      ]
      error_count = 0
    
      #get the standard properties
      for field_data in fields:
        field_name, ctx_opts = field_data[0],field_data[1]
        try:
          #stuff the POST value through a filter
          post_value = self.request.POST.get(field_name)
          filtered_input[field_name] = db.Post.filter_property(field_name, 
            post_value, context=context, ctx_opts=ctx_opts)
        except db.FilterError, e:
          #filter failed
          error_count += 1
          self.set_template_error(field_name, e.msg())

      filtered_input[u'parsed_body'] = context[u'computed_data'].get(u'parsed_body', u'')
      filtered_input[u'imgs'] = context[u'computed_data'].get(u'imgs', [])

      if error_count == 0:    
        #Filter success!
        for field_name,value in filtered_input.iteritems():
          post.set_property_value(field_name, value)
        post.put()
        self.message(u'The Post <strong>\'%s\'</strong> has been updated.' % 
          post.title, u'success')
        return self.redirect(u'/post/edit/%s' % post.key.id())
      self.message(u'There was an error with the submission.', u'error')
    else:
      self.error(404, abort=True)

class PostEditStatusHandler(RequestHandler):
  """
  Path = '/post/edit-status/:id'
  Controller to edit the standard properties of an existing Post.
  """
  @auth.require_admin()
  def post(self, id=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    if post:
      try:
        new_enabled_status = db.Post.filter_property(u'enabled', self.request.POST.get(u'enabled'))
      except db.FilterError, e:
        self.set_template_error(u'enabled', e.msg())
        self.message(u'There was an error with the submission.', u'error')
      else:
        post.set_property_value(u'enabled', new_enabled_status)
        post.put()
        self.message(u'The News item <strong>%s</strong> has been updated.' % 
          post.title, u'success')
        return self.redirect(u'/post/edit/%s' % post.key.id())
    else:
      self.error(404, abort=True)

class PostAddSlugHandler(RequestHandler):
  """
  Path = '/post/remove-slug/:id'
  Controller to edit the standard properties of an existing Post.
  """
  @auth.require_admin()
  def post(self, id=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    if post:
      try:
        new_slug = db.Post.filter_property(u'slug', self.request.POST.get(u'slug'))
      except db.FilterError, e:
        self.message(u'There was an error!', u'error')
      else:
        post.add_property_value(u'slugs', new_slug)
        post.put()
        self.message(u'The slug <strong>%s</strong> was added.' % 
          new_slug, u'success')
      return self.redirect(u'/post/edit/%s' % post.key.id())
    else:
      self.error(404, abort=True)

class PostRemoveSlugHandler(RequestHandler):
  """
  Path = '/psot/remove-slug/:id'
  Controller to edit the standard properties of an existing Post.
  """
  @auth.require_admin()
  def post(self, id=None, *args, **kwargs):
    post_id = db.valid_id_or_default(id, default=None)
    post = None if not post_id else db.Key(u'Post', post_id).get()
    if post:
      try:
        slug_to_remove = db.Post.filter_property(u'slug', self.request.POST.get(u'slug'))
      except db.FilterError, e:
        self.message(u'There was an error!', u'error')
      else:
        post.remove_property_value(u'slugs', value_filter=slug_to_remove)
        post.put()
        self.message(u'The slug <strong>%s</strong> was removed.' % 
          slug_to_remove, u'success')
      return self.redirect(u'/post/edit/%s' % post.key.id())
    else:
      self.error(404, abort=True)
