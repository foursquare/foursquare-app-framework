import itertools
import random
import string
import urllib
try: import simplejson as json
except ImportError: import json

import foursquare

from config import CONFIG
# Does this import fail for you? Fill out foursquare_secrets_template.py, and move it to foursquare_secrets.
from foursquare_secrets import SECRETS

def getServer():
  if CONFIG['local_dev']:
    return CONFIG['local_server']
  else:
    return CONFIG['prod_server']

def generateContentUrl(content_id):
  return CONFIG['content_uri'] % (getServer(), content_id)


def generateRedirectUri():
  return CONFIG['redirect_uri'] % getServer()


def generateFoursquareAuthUri(client_id):
  redirect_uri = generateRedirectUri()
  server = CONFIG['foursquare_server']
  url = '%s/oauth2/authenticate?client_id=%s&response_type=code&redirect_uri=%s'
  return url % (server, client_id, urllib.quote(redirect_uri))


def makeFoursquareClient(access_token=None):
  redirect_uri = generateRedirectUri()
  return foursquare.Foursquare(client_id = CONFIG['client_id'],
                               client_secret = SECRETS['client_secret'],
                               access_token = access_token,
                               redirect_uri = redirect_uri,
                               version = CONFIG['api_version'])


def generateId(size=20, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))


def fetchJson(url):
  """Does a GET to the specified URL and returns a dict representing its reply."""
#  logging.info('fetching url: ' + url)
  result = urllib.urlopen(url).read()
#  logging.info('got back: ' + result)
  return json.loads(result)

def isMobileUserAgent(user_agent):
  """Returns True if the argument is a User-Agent string for a mobile device.

  Includes iPhone, iPad, Android, and BlackBerry.
  """
  # Split on spaces and "/"s in user agent.
  tokens = itertools.chain.from_iterable([item.split("/") for item in user_agent.split()])
  return "Mobile" in tokens
