#!/usr/bin/env python
# -*- coding: utf-8 -*-

#google libs
from google.appengine.ext.blobstore import blobstore
import google.appengine.ext.webapp as webapp
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue

import webob
from webob import exc

import bolognium.ext.aes as aes
import bolognium.ext.template as template
import bolognium.ext.auth as auth
import bolognium.ext.utils as utils
import bolognium.ext.webapp as webapp

#base libs
import sys, os, urlparse, traceback, logging, datetime, Cookie, pickle, cgi

import webob

class BaseRequestHandler(webapp.webapp2.RequestHandler):
  
  def get_valid_handlers(self):
    return 'get, post'

  def will_redirect(self):
    status_code = int(self.response.status.split(' ', 1)[0])
    if status_code in (301, 302):
      return True
    return False

  user = None
  _parsed_uri = None
  _parsed_referer_uri = None
  _start_time = None
  _response_data = None
  _render_on_redirect = False
  
    
  def set_status(self, code):
    self.response.set_status(code)

  def ms_since_start(self):
    td = datetime.datetime.now() - self._start_time
    return int(td.days*86400000 + td.seconds*1000 + td.microseconds/1000)

  def dispatch(self, method, controller, action, method_kwargs):
    """
      Dispatches the request.

    """
    if method is None:
      # 405 Method Not Allowed.
      # The response MUST include an Allow header containing a
      # list of valid methods for the requested resource.
      # http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.6
      valid = self.get_valid_handlers()
      self.abort(405, headers=[('Allow', valid)])

    try:
      self.setup()
      method(**method_kwargs)
      resp = self.respond(controller, action)
    except Exception, e:
      resp = self.handle_exception(e)

    self.session.save()
    return resp

  def setup(self):
    pass

  def handle_exception(self, ex):
    if isinstance(ex, exc.HTTPException):
      error_code = ex.code
    else:
      if utils.is_debug() or auth.is_current_user_admin():
        error_code = 500
      else:
        error_code = 404

    self.error(error_code)

    #log the exception
    self.log_exception(ex)

    return self.respond_on_error(error_code)

  def respond_on_error(self, code):
    self.response.clear()
    return self.response.write(u'')

  def log_exception(self, ex):
    lines = ''.join(traceback.format_exception(*sys.exc_info()))
    if isinstance(ex, urlfetch.DownloadError) or \
      isinstance(ex, DeadlineExceededError) or \
      isinstance(ex, taskqueue.TransientError):
      utils.log.warn(lines)
    else:
      utils.log.error(lines)
      if not utils.is_local() and not utils.is_debug():
        mail.send_mail(
          sender=u'aero@wasteofpaper.com',
          to=u'steve@wasteofpaper.com',
          subject=u'Caught Exception',
          body=lines)

  @property
  def country_code(self):
    return self.request.headers.get(u'X-AppEngine-Country', 'XX')

  @property
  def session(self):
    return auth.get_session()

  def parse_uri(self, uri):
    parsed_uri = urlparse.urlparse(uri)
    return {
      u'scheme': parsed_uri.scheme,
      u'netloc': parsed_uri.netloc,
      u'domain': u'%s://%s' % (parsed_uri.scheme, parsed_uri.netloc),
      u'path': parsed_uri.path,
      u'path_items': [x for x in parsed_uri.path.split(u'/') if len(x)],
      u'params': parsed_uri.params,
      u'query': parsed_uri.query,
      u'fragment': parsed_uri.fragment
    }

  @property
  def referer_uri(self):
    return self.request.headers.get(u'referer')

  @property
  def parsed_referer_uri(self):
    # get the current uri parsed into individual elements
    if not self._parsed_referer_uri:
      self._parsed_referer_uri = self.parse_uri(self.referer_uri)
    return self._parsed_referer_uri

  @property
  def parsed_uri(self):
    # get the current uri parsed into individual elements
    if not self._parsed_uri:
      self._parsed_uri = self.parse_uri(self.request.uri)
    return self._parsed_uri

  def get_current_session(self):
    return self.session

  def current_user(self, name=None):
    if not self.user:
      """hasn't been loaded yet this request"""
      user = self.session.get(u'user')

      """if there was a user in session, reload from datastore"""
      if user:
        self.user = user.reload_from_datastore()

    """if asking about specific attributes..."""
    if name is not None:
      return self.user.check_for_attribute(name=name)
    
    """Or return the whole user."""
    return self.user

  def login_user(self, user):
    self.user = self.session[u'user'] = user

  def logout_user(self):
    self.user = self.session[u'user'] = None

  def update_session_user(self):
    self.session[u'user'] = self.current_user()

  def error(self, code=404, *args, **kwargs):
    """Clears the response output stream and sets the given HTTP error code.
      Args:
      code: the HTTP status error code (e.g., 501)
    """
    self.response.clear()
    self.response.set_status(code)

  def __call__(self, *args, **kwargs):
    try:
      self.setup()
      self._start_time = datetime.datetime.now()
      self.request.func(**self.request.request_kwargs)
    except Exception, e:
      self.handle_exception(e)
    if self.response.__dict__[u'_Response__status'][0] not in (301,302):
      self._respond()

  def respond(self, *args, **kwargs):
    self.response.write(self._response_data)

class NoTemplateRequestHandler(BaseRequestHandler):
  _request_data = None
  
  def error(self, code):
    super(NoTemplateRequestHandler, self).error(code=code)

  def set_response_data(self, data=None):
    self._response_data = data

class BlobstoreUploadHandler(NoTemplateRequestHandler, webapp.blobstore_handlers.BlobstoreUploadHandler):
  pass

class AjaxRequestHandler(NoTemplateRequestHandler):
  set_json_content_type_header = True

  def omit_json_content_type_header(self):
    self.set_json_content_type_header = False
    
  def respond(self, *args, **kwargs):
    if self.set_json_content_type_header == True:
      self.response.headers.add_header('Content-Type', 'application/json')

    #json encode the response data
    response_payload = utils.json.dumps(self._response_data)
    
    #if jsonp 'callback' was set, format the string accordingly.
    if self.request.get(u'callback'):
      response_payload = u'%s(%s)' % (self.request.get(u'callback'), response_payload)

    self.response.write(response_payload)
    return self.response

class RPCRequestHandler(AjaxRequestHandler):
  _rpc_params = {}

  @property
  def params(self):
    try:
      self._rpc_params = utils.json.loads(self.request.get(u'params'))
    except (ValueError,TypeError), e:
      raise
      utils.log.warn(u'Could not decode RPC params from params string: %s' % 
        str(self.request.get(u'params')))
      self._rpc_params = {}
    return self._rpc_params

class ApiRequestHandler(NoTemplateRequestHandler):
  _decrypted_payload = None
  _request_action = None
  _request_data = None

  def setup(self):
    self._decrypt_payload()

  @property
  def request_action(self):
    return self._request_action

  @property
  def request_data(self):
    return self._request_data

  def _decrypt_payload(self):
    if not self._decrypted_payload:
      try:
        _payload = aes.decrypt(self.request.get(u'payload', ''))
        assert isinstance(_payload, basestring)
        self._decrypted_payload = utils.json.loads(_payload)
        assert isinstance(self._decrypted_payload, dict)
        self._request_action = self._decrypted_payload['action']
        self._request_data = self._decrypted_payload['data']
      except (AssertionError,KeyError), e:
        #raise e
        return self.error(400)

  def respond(self, *args, **kwargs):
    output = { 
      u'status_code': self._status_code, 
      u'status_msg': self._status_msg,
      u'data': self._response_data
    }
    return _aes.encrypt(utils.json.dumps(output))

  def get(self, *args, **kwargs):
    try:
      getattr(self, self.request_action)(*args, **kwargs)
    except AttributeError, e:
      self.log.error(u'Api Request Handler didn\'t have method \'%s\' '
        u'as described by the request_action param.')
      self.error(404)

class RequestHandler(BaseRequestHandler):
  _layout = None
  _body_class = None
  _template_name = None
  _template_vars = {}

  def set(self, name=None, data=None):
    if name:
      self._template_vars[name] = data
      return
    return False

    

  def _global_template_vars(self):
    _globals = {
      u'session': self.session,
      u'layout': self.layout,
      u'body_class': self.body_class,
      u'raw_uri' : self.request.uri,
      u'parsed_uri' : self.parsed_uri,
      u'logged_in_user' : self.current_user(),
      u'is_admin' :  auth.is_current_user_admin(),
      u'auth' :  auth,
      u'utils' :  utils,
    }
    return _globals

  @property
  def layout(self):
    return self._layout if self._layout else u'default'

  @property
  def body_class(self):
    return self._body_class if self._body_class else u''

  def _json_global_vars(self):
    return {
      u'raw_uri' : self.request.uri,
      u'parsed_uri' : self.parsed_uri,
      u'is_admin' :  auth.is_current_user_admin(),
      u'debug' :  utils.is_debug()
    }

  """
  # Sets the base template. 
  >>> self.set_layout(u'blank') = '/view/layouts/blank.phtml'
  >>> self.set_layout(u'default') = '/view/layouts/default.phtml' # <-- The default!
  """
  def set_layout(self, layout=None):
    if layout:
      self._layout = layout

  """
  # Sets the body class string
  >>> self.set_body_class(u'single_column') = '<body class="single_column">...'
  """
  def set_body_class(self, body_class=None):
    if body_class:
      self._body_class = body_class


  """
  Sets up all templating stuff for page request handlers
  """
  def respond(self, controller, action):
    #for redirects that shouldn't render the page before they redirect
    if self.will_redirect() and self._render_on_redirect == False:
      return self.response
    """Load the template"""
    _template = template.get_template(name=u'%s/%s.html' % 
      (utils.un_camel_case(controller), utils.un_camel_case(action)))

    """Load some default variables"""
    default_vars = self._global_template_vars()
    default_vars.update(self._template_vars)
    self.set('_json_globals_vars', utils.json.dumps(self._json_global_vars()))
    output = _template.render(default_vars)
    self.response.write(output)
    return self.response

  def respond_on_error(self, code):
    self.response.clear()
    return self.respond(u'Error', str(code))

  def message(self, msg=None, level=u'system'):
    if msg:
      msg = {u'type': level, u'message': msg}
      current_msgs = self.session.get(u'messages', None)
      if not isinstance(self.session.get(u'messages'), list):
        self.session[u'messages'] = []
      self.session[u'messages'].append(msg)
    return

  def error(self, code, abort=False, context={}, *args, **kwargs):
    super(RequestHandler, self).error(code=code, context=context, *args, **kwargs)
    if abort == True:
      if code == 400:
        ex = exc.HTTPBadRequest()
      elif code == 401:
        ex = exc.HTTPUnauthorized()
      elif code == 402:
        ex = exc.HTTPPaymentRequired()
      elif code == 403:
        ex = exc.HTTPForbidden()
      elif code == 404:
        ex = exc.HTTPNotFound()
      elif code == 405:
        ex = exc.HTTPMethodNotAllowed()
      elif code == 406:
        ex = exc.HTTPNotAcceptable()
      elif code == 407:
        ex = exc.HTTPProxyAuthenticationRequired()
      elif code == 408:
        ex = exc.HTTPRequestTimeout()
      elif code == 409:
        ex = exc.HTTPConfict()
      elif code == 410:
        ex = exc.HTTPGone()
      elif code == 411:
        ex = exc.HTTPLengthRequired()
      elif code == 412:
        ex = exc.HTTPPreconditionFailed()
      elif code == 413:
        ex = exc.HTTPRequestEntityTooLarge()
      elif code == 414:
        ex = exc.HTTPRequestURITooLong()
      elif code == 415:
        ex = exc.HTTPUnsupportedMediaType()
      elif code == 416:
        ex = exc.HTTPRequestRangeNotSatisfiable()
      elif code == 417:
        ex = exc.HTTPExpectationFailed()
      elif code == 500:
        ex = exc.HTTPInternalServerError()
      elif code == 501:
        ex = exc.HTTPNotImplemented()
      elif code == 502:
        ex = exc.HTTPBadGateway()
      elif code == 503:
        ex = exc.HTTPServiceUnavailable()
      elif code == 504:
        ex = exc.HTTPGatewayTimeout()
      elif code == 505:
        ex = exc.HTTPVersionNotSupported()
      raise ex

class TaskRequestHandler(BaseRequestHandler):
  pass

class CronRequestHandler(BaseRequestHandler):
  def get(self, *args, **kwargs):
    self.work()

  def work(self, _method, **kwargs):
    pass
