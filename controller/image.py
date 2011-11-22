#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
from google.appengine.api import images
from google.appengine.api import files
from google.appengine.api import urlfetch
from google.appengine.runtime import apiproxy_errors
from google.appengine.ext.blobstore import blobstore

from bolognium.ext.request_handler import RequestHandler
from bolognium.ext.request_handler import AjaxRequestHandler
from bolognium.ext.request_handler import RPCRequestHandler
from bolognium.ext.request_handler import BlobstoreUploadHandler

import bolognium.ext.utils as utils
import bolognium.ext.auth as auth
import bolognium.ext.db as db

import os
import urlparse

class ImageIndexHandler(RequestHandler):
  @auth.require_admin()
  def index(self, *args, **kwargs):
    return
      
class ImageGetUploadUrlHandler(AjaxRequestHandler):
  @auth.require_admin()
  def get(self, *args, **kwargs):
    self.omit_json_content_type_header()
    self.set_response_data({u'upload_url': blobstore.create_upload_url(u'/image/add')})
    #self.set_response_data({u'upload_url': u'/admin/dashboard'})
  
class ImageAddHandler(BlobstoreUploadHandler):
  @auth.require_admin()
  def post(self, *args, **kwargs):
    try:
      upload_files = self.get_uploads('image')
      blob_info = upload_files[0]

      #create and save the img instance
      img = db.Img.create_from_blob_key(blob_info.key())
      img.put()

    except db.Img.DoesNotExistError, e:
      raise
    except Exception:
      raise
    else:
      self.set_response_data(utils.json.dumps(img.meta.to_client_side()))
      
class ImageCropAndCopyRpcHandler(RPCRequestHandler):
  @auth.require_admin()
  def post(self, *args, **kwargs):
    try:
      img_id = self.params.get(u'img_id')
      img_instance = db.Img.get_by_id(img_id)
      if not img_instance:
        raise db.Img.DoesNotExistError(img_id)
      
      #parse the crop params
      crop_args = self.params.get(u'crop_args')
      crop_args = [float(x) for x in crop_args.split(u':')]
      format = self.request.get(u'format', None)
      new_img = img_instance.make_cropped_copy(
        crop_args=crop_args, format=format)
      new_img.put()
      
    except db.Img.DoesNotExistError, e:
      self.error(500)
      self.set_response_data({u'error_msg': str(e)})
    except (images.TransformationError, images.BadRequestError), e:
      self.set_response_data({u'error_msg': u'Something went seriously wrong. MSG: %s' % e})
      self.error(500)
    except (images.TransformationError, images.BadRequestError), e:
      self.set_response_data({u'error_msg': u'Unexpected Error! MSG: %s' % e})
      self.error(500)
    else:
      self.set_response_data({'cropped_img': new_img.meta.to_client_side()})

def get_image_by_url(url):
  return urlfetch.fetch(url).content
  
