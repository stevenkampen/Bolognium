#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for the Facebook Platform.

This client library is designed to support the Graph API and the official
Facebook JavaScript SDK, which is the canonical way to implement
Facebook authentication. Read more about the Graph API at
http://developers.facebook.com/docs/api. You can download the Facebook
JavaScript SDK at http://github.com/facebook/connect-js/.

If your application is using Google AppEngine's webapp framework, your
usage of this module might look like this:

    user = facebook.get_user_from_cookie(self.request.cookies, key, secret)
    if user:
        graph = facebook.GraphAPI(user["access_token"])
        profile = graph.get_object("me")
        friends = graph.get_connections("me", "friends")

"""

import cgi
import hashlib
import base64
import hmac
import time
import urllib
from google.appengine.api import urlfetch

import json

class Facebook(object):
	app = None
	"""Wraps the Facebook specific logic"""
	def __init__(self, app):
		self.app = app
		self.app_id = self.app.get_config(u'%sapp_id'  % 'dev_' if self.app.is_local() else u'app_id', u'facebook')
		self.app_secret = self.app.get_config(u'%sapp_secret' % 'dev_' if self.app.is_local() else u'app_secret', u'facebook')
		self.user_id = None
		self.access_token = None
		self.signed_request = {}

	def __call__(self, user_id=None, access_token=None):
		instance = self.__class__(self.app)
		instance.user_id = user_id
		instance.access_token = access_token
		return instance

	def api(self, path, params={}, method=u'GET', domain=u'graph'):
		"""Make API calls"""
		params[u'method'] = method
		if u'access_token' not in params and self.access_token:
			params[u'access_token'] = self.access_token
		result = json.loads(urlfetch.fetch(
			url=u'https://%s.facebook.com%s' % (domain, path),
			payload=urllib.urlencode(params),
			method=urlfetch.POST,
			headers={u'Content-Type': u'application/x-www-form-urlencoded'}).content)
		if isinstance(result, dict) and u'error' in result:
			raise FacebookApiError(result)
		return result

	def load_signed_request(self, signed_request):
		"""Load the user state from a signed_request value"""
		try:
			sig, payload = signed_request.split(u'.', 1)
			sig = self.base64_url_decode(sig)
			data = json.loads(self.base64_url_decode(payload))
			expected_sig = hmac.new(self.app_secret, msg=payload, digestmod=hashlib.sha256).digest()

		except ValueError, ex:
			pass # ignore if can't split on dot

		else:
			if sig == expected_sig and data[u'issued_at'] > (time.time() - 86400):
				self.signed_request = data
				self.user_id = data.get(u'user_id')
				self.access_token = data.get(u'oauth_token')


	def load_signed_request_dict(self, data):
		if data[u'issued_at'] > (time.time() - 86400):
			self.signed_request = data
			self.user_id = data.get(u'user_id')
			self.access_token = data.get(u'oauth_token')

	def __str__(self):
		return u"Facebook Object for User: %s" % (self.user_id or u'None')

	@property
	def user_cookie(self):
		"""Generate a signed_request value based on current state"""
		if not self.user_id:
			return
		payload = self.base64_url_encode(json.dumps({
			u'user_id': self.user_id,
			u'issued_at': str(int(time.time())),
		}))
		sig = self.base64_url_encode(hmac.new(
			self.app_secret, msg=payload, digestmod=hashlib.sha256).digest())
		return sig + '.' + payload

	@staticmethod
	def base64_url_decode(data):
		data = data.encode(u'ascii')
		data += '=' * (4 - (len(data) % 4))
		return base64.urlsafe_b64decode(data)

	@staticmethod
	def base64_url_encode(data):
		return base64.urlsafe_b64encode(data).rstrip('=')


class FacebookApiError(Exception):
	def __init__(self, result):
		self.result = result

	def __str__(self):
		return self.__class__.__name__ + ': ' + json.dumps(self.result)


class GraphApi(object):
	"""A client for the Facebook Graph API.

	See http://developers.facebook.com/docs/api for complete documentation
	for the API.

	The Graph API is made up of the objects in Facebook (e.g., people, pages,
	events, photos) and the connections between them (e.g., friends,
	photo tags, and event RSVPs). This client provides access to those
	primitive types in a generic way. For example, given an OAuth access
	token, this will fetch the profile of the active user and the list
	of the user's friends:

		graph = facebook.GraphAPI(access_token)
		user = graph.get_object("me")
		friends = graph.get_connections(user["id"], "friends")

	You can see a list of all of the objects and connections supported
	by the API at http://developers.facebook.com/docs/reference/api/.

	You can obtain an access token via OAuth or by using the Facebook
	JavaScript SDK. See http://developers.facebook.com/docs/authentication/
	for details.

	If you are using the JavaScript SDK, you can use the
	get_user_from_cookie() method below to get the OAuth access token
	for the active user from the cookie saved by the SDK.
	"""
	def __init__(self, access_token=None):
		self.access_token = access_token

	def get_object(self, id, **args):
		"""Fetchs the given object from the graph."""
		return self.request(id, args)

	def get_objects(self, ids, **args):
		"""Fetchs all of the given object from the graph.

		We return a map from ID to object. If any of the IDs are invalid,
		we raise an exception.
		"""
		args["ids"] = ",".join(ids)
		return self.request("", args)

	def get_connections(self, id, connection_name, **args):
		"""Fetchs the connections for given object."""
		return self.request(id + "/" + connection_name, args)

	def put_object(self, parent_object, connection_name, **data):
		"""Writes the given object to the graph, connected to the given parent.

		For example,

			graph.put_object("me", "feed", message="Hello, world")

		writes "Hello, world" to the active user's wall. Likewise, this
		will comment on a the first post of the active user's feed:

			feed = graph.get_connections("me", "feed")
			post = feed["data"][0]
			graph.put_object(post["id"], "comments", message="First!")

		See http://developers.facebook.com/docs/api#publishing for all of
		the supported writeable objects.

		Most write operations require extended permissions. For example,
		publishing wall posts requires the "publish_stream" permission. See
		http://developers.facebook.com/docs/authentication/ for details about
		extended permissions.
		"""
		assert self.access_token, u'Write operations require an access token'
		return self.request(parent_object + u'/' + connection_name, post_args=data)

	def put_wall_post(self, message, attachment={}, profile_id=u'me'):
		"""Writes a wall post to the given profile's wall.

		We default to writing to the authenticated user's wall if no
		profile_id is specified.

		attachment adds a structured attachment to the status message being
		posted to the Wall. It should be a dictionary of the form:

			{"name": "Link name"
			 "link": "http://www.example.com/",
			 "caption": "{*actor*} posted a new review",
			 "description": "This is a longer description of the attachment",
			 "picture": "http://www.example.com/thumbnail.jpg"}

		"""
		return self.put_object(profile_id, u'feed', message=message, **attachment)

	def put_comment(self, object_id, message):
		"""Writes the given comment on the given post."""
		return self.put_object(object_id, u'comments', message=message)

	def put_like(self, object_id):
		"""Likes the given object."""
		return self.put_object(object_id, u'likes')

	def delete_object(self, id):
		"""Deletes the object with the given ID from the graph."""
		self.request(id, post_args={u'method': u'delete'})

	def request(self, path, args=None, payload=None):
		"""Fetches the given path in the Graph API.

		We translate args to a valid query string. If post_args is given,
		we send a POST request to the given path with the given arguments.
		"""
		url = u'https://graph.facebook.com/%s' % path
		if args:
			url = u'%s?%s' % (url,urllib.urlencode(args))

		headers = {}
		method = urlfetch.GET

		if payload is not None:
			#change method to post
			method = urlfetch.POST
			#add access token to post args if one is set
			if self.access_token:
				payload[u'access_token'] = self.access_token
			#encode post args
			payload = urllib.urlencode(payload)
			#add the correct headers for posts
			headers[u'Content-Type'] = u'application/x-www-form-urlencoded'

		#get it
		file = urlfetch.fetch(
			url=url,
			payload=post_data,
			method=method,
			headers=headers
		)
							
		error = None
		if file.status_code == 200:
			response = json.loads(file.content)
			if response.get(u'error'):
				error = response[u'error']
		if error is not None:
			error_type = u'URLError'
			error_msg = u'URL fetch returned error. Code: %s,  Original URL: %s, Final URL: %s' % (file.status_code, url, file.final_url)
			raise GraphAPIError(error[u'type'], error[u'message'])
		return response


class GraphAPIError(Exception):
	def __init__(self, type, message):
		Exception.__init__(self, message)
		self.type = type

def get_user_from_cookie(cookies):
    """Parses the cookie set by the official Facebook JavaScript SDK.

    cookies should be a dictionary-like object mapping cookie names to
    cookie values.

    If the user is logged in via Facebook, we return a dictionary with the
    keys "uid" and "access_token". The former is the user's Facebook ID,
    and the latter can be used to make authenticated requests to the Graph API.
    If the user is not logged in, we return None.

    Download the official Facebook JavaScript SDK at
    http://github.com/facebook/connect-js/. Read more about Facebook
    authentication at http://developers.facebook.com/docs/authentication/.
    """
    cookie = cookies.get(u'fbs_' + app.get_config(u'app_id', u'facebook'), u'')
    if not cookie: return None
    args = dict((k, v[-1]) for k, v in cgi.parse_qs(cookie.strip('"')).items())
    payload = "".join(k + u'=' + args[k] for k in sorted(args.keys())
                      if k != 'sig')
    sig = hashlib.md5(payload + app.get_config(u'app_secret', u'facebook')).hexdigest()
    expires = int(args[u'expires'])
    if sig == args.get(u'sig') and (expires == 0 or time.time() < expires):
        return args
    else:
        return None
