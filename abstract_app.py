import logging
try: import simplejson as json
except ImportError: import json

from google.appengine.ext import webapp

from config import CONFIG
from model import UserToken, ContentInfo
import utils


class AbstractApp(webapp.RequestHandler):
  def get(self):
    client = utils.makeFoursquareClient()

    content_id = self.request.get('content_id')
    if content_id:
      content_info = ContentInfo.all().filter('content_id =', content_id).get()
      if not content_info:
        self.error(404)
        return
      return self.contentGet(client, content_info)

    return self.appGet(client)


  def post(self):
    if self.request.path.startswith('/_checkin') and self.request.get('checkin'):
      # Parse floats as string so we don't lose lat/lng precision. We can use Decimal later.
      checkin_json = json.loads(self.request.get('checkin'),
                                parse_float=str)
      user_id = checkin_json['user']['id']
      access_token = self.fetchAccessToken(user_id)
      if not access_token:
        logging.warning('Recieved push for unknown user_id {}'.format(user_id))
        return
      client = utils.makeFoursquareClient(access_token)
      return self.checkinTaskQueue(client, checkin_json)

    client = utils.makeFoursquareClient()
    return self.appPost(client)


  def appGet(self, client):
    """Generic handler for GET requests"""
    logging.warning('appGet stub called')
    self.error(404)
    return


  def homepageGet(self, client):
    """Serves a simple homepage where the user can authorize the app"""


  def contentGet(self, client, content_info):
    """Handler for content related GET requests"""
    logging.warning('contentGet stub called')
    self.error(404)
    return


  def appPost(self, client):
    """Generic handler for POST requests"""
    logging.warning('appPost stub called')
    self.error(404)
    return


  def checkinTaskQueue(self, authenticated_client, checkin_json):
    """Handler for check-in task queue"""
    logging.warning('checkinTaskQueue stub called')
    return

  def fetchAccessToken(self, user_id):
    request = UserToken.all()
    request.filter("fs_id = ", str(user_id))
    user_token = request.get()
    return user_token.token if user_token else None

  def fetchContentInfo(self, content_id):
    request = ContentInfo.all().filter("content_id = ", content_id)
    return request.get()

  def generateContentUrl(self, content_id):
    return utils.generateContentUrl(content_id)

  def makeContentInfo(self,
                      checkin_json,
                      content,
                      url=None,
                      text=None, photoId=None,
                      reply=False, post=False):
    assert (reply ^ post), "Must pass exactly one of reply or post"
    assert (text or photoId)

    # Avoid posting duplicate content.
    request = ContentInfo.all()
    request = request.filter('checkin_id = ', checkin_json['id'])
    existing_contents = request.fetch(10)
    for existing_content in existing_contents:
      # Check that they're the same type of content
      if existing_content.reply_id and not reply:
        continue
      if existing_content.post_id and not post:
        continue
      # Check if the content payload is the same
      if existing_content.content == content:
        logging.info('Avoided posting duplicate content %s' % content)
        return existing_content

    content_id = utils.generateId()
    checkin_id = checkin_json['id']

    content_info = ContentInfo()
    content_info.content_id = content_id
    content_info.fs_id = checkin_json['user']['id']
    content_info.checkin_id = checkin_id
    content_info.venue_id = checkin_json['venue']['id']
    content_info.content = content
    if not url:
      url = self.generateContentUrl(content_id)

    access_token = self.fetchAccessToken(content_info.fs_id)
    client = utils.makeFoursquareClient(access_token)

    params = {'contentId' : content_id,
              'url' : url}
    if text:
      params['text'] = text
    if photoId:
      params['photoId'] = photoId

    logging.info('creating content with params=%s' % params)

    if post:
      if CONFIG['local_dev']:
        content_info.post_id = utils.generateId()
      else:
        response_json = client.checkins.addpost(checkin_id, params)
        content_info.post_id = response_json['post']['id']
    elif reply:
      if CONFIG['local_dev']:
        content_info.reply_id = utils.generateId()
      else:
        response_json = client.checkins.reply(checkin_id, params)
        reply_id = None
        if 'replies' in response_json:
          reply_id = response_json['replies']['id']
        elif 'reply' in response_json:
          # Right now we return "replies" but we should probably return "reply"
          # adding this so I don't have to do it later in the event we rename
          reply_id = response_json['reply']['id']
        else:
          logging.error("Could not find reply id in /checkins/reply response: %s" % response_json)

        content_info.reply_id = reply_id

    content_info.put()

    return content_info
