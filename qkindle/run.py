# -*- coding: utf-8 -*-

from tornado import httpserver, ioloop
from tornado.options import define, options
from app import Application


define("port", help="run on port", default=8888, type=int)

if __name__ == "__main__":
    options.parse_command_line()
    application = Application()
    http_server = httpserver.HTTPServer(application)
    http_server.listen(options.port)
    ioloop.IOLoop.current().start()

