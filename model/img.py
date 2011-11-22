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

import time

format_choices = [u'PNG', u'JPEG', u'TIFF', u'GIF', u'X-ICON', u'BMP', u'WEBP']

class Img(db.Model):
  blob_key = db.BlobKeyProperty(whitelisted=True, required=True)

  format = db.StringProperty(whitelisted=True)
  height = db.IntegerProperty(whitelisted=True)
  width = db.IntegerProperty(whitelisted=True)
  url = db.StringProperty(whitelisted=True, required=True)
  
  #reimplementation of all these meta fields
  @property
  def meta(self):
    return db.ImgMeta(
      img_id=self.key.id(),
      blob_key=self.blob_key,
      height=self.height,
      width=self.width,
      format=self.format
    )

  #created and updated properties
  created = db.CreatedDateTimeProperty()
  updated = db.UpdatedDateTimeProperty()

  unused = db.BooleanProperty(whitelisted=True, default=False)
  deleted = db.BooleanProperty(whitelisted=True, default=False)


  def make_cropped_copy(self, crop_args, format=None):
    cls = self.__class__
    image = self.image
    image.crop(*crop_args)

    #create the image
    new_image_data = image.execute_transforms(output_encoding=format or cls.get_format_from_string(self.format))

    #create the blob
    new_image = images.Image(new_image_data)
    blob = create_blob_from_image(new_image)
    blob_key = files.blobstore.get_blob_key(blob)
    #need this for local. blob key, eventual consistency, issue.
    if utils.is_local():
      time.sleep(1)

    return cls(
      blob_key=blob_key,
      url=images.get_serving_url(blob_key),
      width=new_image.width,
      height=new_image.height,
      format=cls.get_format_string(new_image.format))

  @classmethod
  def create_from_blob_key(cls, blob_key):
    #return the img instance
    if blob_key:
      blob_info = blobstore.get(blob_key)
      if blob_info:
        image = images.Image(blobstore.BlobReader(blob_key).read())
        return cls(
          blob_key=blob_key,
          url=images.get_serving_url(blob_key),
          width=image.width,
          height=image.height,
          format=cls.get_format_string(image.format))
    raise DoesNotExistError(u'Could not get image by Blob Key: %s' % blob_key)

  @classmethod
  def create_from_raw(cls, img_data, name=None, caption=None, size=None):

    #create the images.Image() object
    image = images.Image(img_data)

    #create the blob
    blob = create_blob_from_image(image)

    #need this for local. blob key, eventual consistency, issue.
    if utils.is_local():
      time.sleep(.250)

    #get the blob key
    blob_key = files.blobstore.get_blob_key(blob)

    #get a rough size
    bytes_ = -1
    if isinstance(size, int) and size > 0: 
      bytes_ = size

    #return the img instance
    return cls(
      blob_key=blob_key,
      url=images.get_serving_url(blob_key),
      width=image.width,
      height=image.height,
      format=cls.get_format_string(image.format))

  _image = None
  @property
  def image(self):
    if not self._image:
      self._image = images.Image(blob_key=self.blob_key)
    return self._image

  def serving_url(self, size=None, crop=False):
    url = self.url
    if size: url += u'=s%s' % size
    if crop: url += u'-c'
    return url
    
  @classmethod
  def format_choices(cls):
    return format_choices
    
  @classmethod
  def get_mime_string(cls, format):
    if format == images.JPEG:
      return u'image/jpeg'
    elif format == images.PNG:
      return u'image/png'
    elif format == images.GIF:
      return u'image/gif'
    elif format == images.BMP:
      return u'image/bmp'
    elif format == images.ICO:
      return u'image/x-icon'
    elif format == images.TIFF:
      return u'image/tiff'
    elif format == images.WEBP:
      return u'image/webp'
    else: 
      return u'image/png'

  @classmethod
  def get_format_from_string(cls, format):
    if format in format_choices:
      return getattr(images, format)
    raise BadFormatError()

  @classmethod
  def get_format_string(cls, format):
    if format == images.JPEG:
      return u'JPEG'
    elif format == images.PNG:
      return u'PNG'
    elif format == images.GIF:
      return u'GIF'
    elif format == images.BMP:
      return u'BMP'
    elif format == images.ICO:
      return u'X-ICON'
    elif format == images.TIFF:
      return u'TIFF'
    elif format == images.WEBP:
      return u'WEBP'
    raise Exception("Input format model was invalid!")


  @classmethod
  def validate_format(cls, format):
    if not isinstance(format, basestring):
      format = cls.get_format_string(format)
    format = format.upper()
    if format and format in db.Img.format_choices():
      return cls.get_format_from_string(format)
    raise cls.BadImgFormatError(format)

class Error(Exception):
  def __init__(self, msg=''):
    self._msg = msg

  def __str__(self):
    return u'Error! MSG: %s' % repr(self._format)
    
class BadFormatError(Error):
  def __init__(self, format=None, *args, **kwargs):
    self._format = format
    super(BadFormatError, self).__init__(*args, **kwargs)

  def __str__(self):
    return u'BadFormatError! Format: %s' % repr(self._format)

class BadImageDataError(Error):
  def __str__(self):
    return u'BadImageDataError!'

class DoesNotExistError(Error):
  def __init__(self, id=None, *args, **kwargs):
    self._id = id
    super(DoesNotExistError, self).__init__(*args, **kwargs)

  def __str__(self):
    return u'DoesNotExistError! Img ID: %s' % repr(self._id)

class BadIdError(Error):
  def __init__(self, id=None, *args, **kwargs):
    self._id = id
    super(BadIdError, self).__init__(*args, **kwargs)

  def __str__(self):
    return u'BadIdError! Should be a positive integer. Got Img ID: ' \
      u'%s of type \'%s\'.' % (repr(self._id), type(self._id))

Img.DoesNotExistError = DoesNotExistError
Img.BadFormatError = BadFormatError
Img.BadImageDataError = BadImageDataError
Img.BadIdError = BadIdError
Img.Error = Error

def create_blob_from_image(image):
  #create a blob
  file_ = files.blobstore.create(mime_type=db.Img.get_mime_string(image.format))
  #write it into the blob
  with files.open(file_, 'a') as f: f.write(image._image_data)
  files.finalize(file_)
  return file_
 
  
