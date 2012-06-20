import random
import string

from google.appengine.ext import db

class UserSession(db.Model):
  """Maps user cookies back to foursquare ids."""
  fs_id = db.StringProperty()
  session = db.StringProperty()

  @staticmethod
  def get_or_create_session(user_id):
    session = UserSession().all().filter('fs_id =', user_id).get()
    if not session:
      session = UserSession()
      session.fs_id = user_id
      session.session = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(64))
      session.put()
    return session

  @staticmethod
  def get_from_cookie(cookie):
    return UserSession().all().filter('session =', cookie).get()


class UserToken(db.Model):
  """Contains the user to foursquare_id + oauth token mapping."""
  fs_id = db.StringProperty()
  token = db.StringProperty()

  @staticmethod
  def get_by_fs_id(fs_id):
    return UserToken().all().filter('fs_id =', fs_id).get()

  @staticmethod
  def get_from_cookie(cookie):
    session = UserSession.get_from_cookie(cookie)
    if session:
      return UserToken.get_by_fs_id(session.fs_id)
    return None

class ContentInfo(db.Model):
  """Generic object for easily storing content for a reply or post."""
  content_id = db.StringProperty()
  checkin_id = db.StringProperty()
  venue_id = db.StringProperty()
  fs_id = db.TextProperty()
  content = db.TextProperty()
  reply_id = db.TextProperty()
  post_id = db.TextProperty()
