#!/usr/bin/env python

from __future__ import with_statement

from google.appengine.api import memcache
from google.appengine.ext import deferred
from google.appengine.api import taskqueue
from google.appengine.ext import deferred
from google.appengine.api import images
from google.appengine.api import files
from google.appengine.ext.blobstore import blobstore

import bolognium.ext.db as db
import bolognium.ext.auth as auth
import bolognium.ext.utils as utils

class ImgMeta(db.StructuredModel):
  img_id = db.IntegerProperty(whitelisted=True, required=True)
  blob_key = db.BlobKeyProperty(whitelisted=True, required=True)

  format = db.StringProperty(whitelisted=True)
  height = db.IntegerProperty(whitelisted=True)
  width = db.IntegerProperty(whitelisted=True)
  url = db.ComputedProperty(func=lambda self: self.get_serving_url(), whitelisted=True)

  def get_serving_url(self, *args, **kwargs):
    return images.get_serving_url(self.blob_key, *args, **kwargs)

  #created and updated properties
  created = db.CreatedDateTimeProperty()
  updated = db.UpdatedDateTimeProperty()

