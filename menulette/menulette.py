import logging
import os
import random

from google.appengine.ext.webapp import template

try: import simplejson as json
except ImportError: import json

from abstract_app import AbstractApp


class Menulette(AbstractApp):
  REACTION_STRINGS = {'amazing' : 'amazing.',
                      'death'   : 'death.'}
  
  def contentGet(self, client, content_info):
    content_json = json.loads(content_info.content)
    fsqCallback = self.request.get('fsqCallback')
    if content_info.reply_id:
      content_json["content_id"] = content_info.content_id
      content_json["fsqCallback"] = fsqCallback
      path = os.path.join(os.path.dirname(__file__), 'reply.html')
      self.response.out.write(template.render(path, content_json))
      return
    
    if content_info.post_id:
      reaction = content_json['reaction']
      content_json['reaction_string'] = self.REACTION_STRINGS[reaction]
      path = os.path.join(os.path.dirname(__file__), 'post.html')
      self.response.out.write(template.render(path, content_json))
      
  
  def appPost(self, client):
    sci = self.request.get('source_content_id')
    source_content_info = self.fetchContentInfo(sci)
    access_token = self.fetchAccessToken(source_content_info.fs_id)
    
    client.set_access_token(access_token)
    checkin_json = client.checkins(source_content_info.checkin_id)['checkin']

    reaction = None
    if self.request.get('amazing'):
      reaction = "amazing"
    elif self.request.get('death'):
      reaction = "death"
    else:
      logging.error('Bad appPost request: %s' % self.request)
      self.error(400)
      return
    reaction_string = self.REACTION_STRINGS[reaction]
    name = client.users()['user']['firstName']
    item = json.loads(source_content_info.content)['item']
    message = "I ordered the %s; it was %s" % (item, reaction_string)
    self.makeContentInfo( checkin_json = checkin_json,
                          content = json.dumps({'item': item,
                                                'name': name,
                                                'reaction': reaction}),
                          text = message,
                          post = True)

    # TODO(ak): Use fsqCallback
    fsqCallback = self.request.get('fsqCallback')
    logging.debug('fsqCallback = %s' % fsqCallback)
    self.redirect(fsqCallback)
        
  
  def checkinTaskQueue(self, client, checkin_json):
    venue_id = checkin_json['venue']['id']
    venue_json = client.venues(venue_id)['venue']
    
    if not 'menu' in venue_json:
      logging.info('No menu found for %s' % venue_json['name'])
      return
    
    menus_json = client.venues.menu(venue_id)['menu']['menus']
    count = menus_json['count']
    index = random.randrange(count)
    menus_json = menus_json['items'][index]['entries']
    count = menus_json['count']
    index = random.randrange(count)
    menus_json = menus_json['items'][index]['entries']
    count = menus_json['count']
    index = random.randrange(count)
    item = menus_json['items'][index]['name']
      
    message = 'Dare you to get the %s' % item
    self.makeContentInfo( checkin_json = checkin_json,
                          content = json.dumps({'item': item}),
                          text = message,
                          reply = True)
