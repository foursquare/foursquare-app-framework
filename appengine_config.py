# Enable appstats
# http://code.google.com/appengine/docs/python/tools/appstats.html

def webapp_add_wsgi_middleware(app):
    from google.appengine.ext.appstats import recording
    app = recording.appstats_wsgi_middleware(app)
    return app