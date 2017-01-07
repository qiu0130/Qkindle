# _*_ coding: utf-8 _*_

from tornado import web
from motor import motor_tornado
from handler import *
from module import *


class Application(web.Application):
    def __init__(self):
        motor_db = motor_tornado.MotorClient().qkindle
        handlers = [
            (r"/auth/login", LoginHandlder),
            (r"/auth/logout", LogoutHandler),
            (r"/auth/register", RegisterHandler),

            (r"/main/(.*)", HomeIndexHandler),

            (r"/push/(.*)/(.*)", PushIndexHandler),
            (r"/upload/(.*)/(.*)", UploadIndexHandler),

            (r"/username/(.*)", UserInfoHandler),
            (r"/photo/(.*)", AvatarHandler),
            (r"/book/(.*)", BookHandler),
        ]
        settings = {
            "db": motor_db,
            "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            "xsrf_cookies": True,
            "debug": True,
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "static_path": os.path.join(os.path.dirname(__file__), "static"),

            "ui_modules": {
                "PushBook": PushBookModule,
                "UploadBook": UploadBookModule,
                "PartLine": PartLineModule,
            }
        }
        super(Application, self).__init__(handlers, **settings)
