# -*- coding: UTF-8 -*- 
# Created by qiu on 16-5-20
#





if __name__ == "__main__":
    pass



from tornado.httpclient import AsyncHTTPClient
from tornado.gen import coroutine
from tornado.web import RequestHandler
from tornado.escape import json_decode
import tornado.web
import tornado.httpserver
import tornado.ioloop


class Mainhandler(RequestHandler):
    @coroutine
    def get(self):
        http_client = AsyncHTTPClient()
        reponse = yield http_client.fetch("http://127.0.0.1:8887/pushbook", method = "POST",
                      body = str({
                          "body": "body --- "
                      }))

        self.write(json_decode(reponse.body)["body"])

if __name__ == "__main__":


    app = tornado.web.Application([
        (r"/test", Mainhandler),
    ], debug=True)

    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(8875)

    tornado.ioloop.IOLoop.current().start()


