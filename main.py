#!/usr/bin/python

import Cookie
import email.utils
import logging
import os
import time
try: import simplejson as json
except ImportError: import json

from foursquare import InvalidAuth

from config import CONFIG, APP_CLASS
from foursquare_secrets import SECRETS
from model import UserSession, UserToken
import utils

from google.appengine.api import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

class OAuthConnectErrorException(Exception):
  pass

class OAuthConnectDeniedException(Exception):
  pass


class OAuth(webapp.RequestHandler):
  """Handle the OAuth redirect back to the service."""
  def post(self):
    self.get()

  def get(self):
    try:
      error = self.request.get('error')
      if error == "access_denied":
        raise OAuthConnectDeniedException
      elif error:
        raise OAuthConnectErrorException

      code = self.request.get('code')
      if not code:
        raise OAuthConnectErrorException

      client = utils.makeFoursquareClient()
      access_token = client.oauth.get_token(code)
      if not access_token:
        raise OAuthConnectErrorException
      client.set_access_token(access_token)
    except OAuthConnectDeniedException:
      self.redirect(CONFIG['auth_denied_uri'])
      return
    except OAuthConnectErrorException:
      path = os.path.join(os.path.dirname(__file__),
                          'templates/connect_error.html')
      self.response.out.write(template.render(path, {'name': CONFIG['site_name']}))
      return

    user = client.users()  # returns the auth'd users info
    fs_user_id = user['user']['id']

    existing_token = UserToken.get_by_fs_id(fs_user_id)

    if existing_token:
      token = existing_token
    else:
      token = UserToken()

    token.token = access_token
    token.fs_id = fs_user_id
    token.put()

    session = UserSession.get_or_create_session(fs_user_id)
    cookie = Cookie.SimpleCookie()
    cookie['session'] = session.session
    cookie['session']['path'] = '/'
    cookie['session']['expires'] = email.utils.formatdate(time.time() + (14 * 86400), localtime=False, usegmt=True)
    self.response.headers.add_header("Set-Cookie", cookie.output()[12:])
    isMobile = utils.isMobileUserAgent(self.request.headers['User-Agent'])
    redirect_uri = CONFIG['auth_success_uri_mobile'] if isMobile else CONFIG['auth_success_uri_desktop']
    self.redirect(redirect_uri)


class IsAuthd(webapp.RequestHandler):
  """Returns whether or not a user has connected their foursquare account"""
  def get(self):
    user_token = UserToken.get_from_cookie(self.request.cookies.get('session', None))
    is_authd = 'false'
    if user_token and user_token.fs_id:
      client = utils.makeFoursquareClient(user_token.token)
      try:
        client.users()
        is_authd = 'true'
      except InvalidAuth:
        user_token.delete()

    self.response.out.write(is_authd)


class ProcessCheckin(webapp.RequestHandler):
  PREFIX = "/checkin"

  def post(self):
    # Validate against our push secret if we're not in local_dev mode.
    if (self.request.get('secret') != SECRETS['push_secret'] and not CONFIG['local_dev']):
      self.error = 403
      return
    checkin_json = json.loads(self.request.get('checkin'),
                              parse_float=str)
    if 'venue' not in checkin_json:
      # stupid shouts. skip everything
      return
    logging.debug('received checkin ' + checkin_json['id'])
    taskqueue.add(url='/_checkin',
                  params={'checkin': self.request.get('checkin')})


class HomePage(webapp.RequestHandler):
  def get(self):
    client_id = CONFIG['client_id']
    params = {'client_id': client_id}
    params['auth_url'] = utils.generateFoursquareAuthUri(client_id)
    params['name'] = CONFIG['site_name']
    params['description'] = CONFIG['site_description']
    path = os.path.join(os.path.dirname(__file__),
                        'templates/index.html')
    self.response.out.write(template.render(path, params))


application = webapp.WSGIApplication([('/oauth.*', OAuth),
                                      ('/checkin', ProcessCheckin),
                                      ('/isAuthd', IsAuthd),
                                      ('/', HomePage),
                                      ('/_checkin', APP_CLASS),
                                      ('/.*', APP_CLASS)],
                                     debug=CONFIG['debug'])

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
