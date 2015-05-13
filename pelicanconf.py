#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'scbzyhx'
SITENAME = u'YANG'
SITEURL = u'http://scbzyhx.github.io'

PATH = 'content'

TIMEZONE = 'Asia/Shanghai'

DEFAULT_LANG = u'zh'

THEME = 'pelican-themes/pelican-bootstrap3'
DISQUS_SITENAME = u'yhx'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (#('weibo', 'http://weibo.com/u/3445058592/'),
         ('Github', 'http://github.com/'),
         #('Jinja2', 'http://jinja.pocoo.org/'),
         #('You can modify those links in your config file', '#'),
         )

# Social widget
SOCIAL = (('weibo', 'http://weibo.com/u/3445058592/'),
         ('Github', 'http://github.com/scbzyhx'),)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

PLUGIN_PATHS = [u'pelican-plugins'] #plugin path
PLUGINS = ['sitemap','random_article','neighbors'] # plugins enabled

SITEMAP = {
	"format":"xml",
	"priorities":{
		"articles":0.7,
		"indexes":0.5,
		"pages":0.3,
	},
	"changefreqs":{
		"articles":"monthly",
		"indexes":"daily",
		"pages":"monthly",
	}
}
#random to some blog
RANDOM = 'random.html'

RELATED_POSTS_MAX = 10

#STATIC FILES
#FILE_TO_COPY setting has been removed in favor of STATIC_PATHS and EXTRA_PATH_METADATA, 
#see https://github.com/getpelican/pelican/blob/master/docs/settings.rst#path-metadata
#FILES_TO_COPY = {
	#("extra/robots.txt","robots.txt")
#}
#STATIC DIRS
#STATIC_PATH = [u'img']
