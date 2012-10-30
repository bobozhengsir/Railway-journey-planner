# -*- coding: utf-8 -*-
from bottle import run, debug

import controllers
from controllers import webapp

DEBUG = True

debug(DEBUG)
run(webapp, host='0.0.0.0', port=8080, reloader=DEBUG)
