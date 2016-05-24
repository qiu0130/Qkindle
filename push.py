# -*- coding: UTF-8 -*- 
# Created by qiu on 16-5-23
#
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from tornado.web import RequestHandler
from tornado.options import options, define
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
from concurrent.futures import Future
import threading

import tornado.gen

define("ports", default=8888, help = "run on give port", type = int)

class MainHandler(RequestHandler):

    def post(self):

      pass

@tornado.gen.coroutine
def get_data(kindle_email, filename):
    future = Future()
    threading.Thread(target=send_email_to_kindle, args=(future, kindle_email, filename)).start()
    return future


def send_email_to_kindle(receiver, filename):

    sender = "zqkindle@126.com"
    password = 'qiu63876092'
    smtp_server = 'smtp.126.com'

    msg = MIMEMultipart('related')
    msg['Subject'] = filename

    filepath = "/home/qiu/PycharmProjects/zqread/static/book/" + filename
    with open(filepath, "rb") as fp:
        file = fp.read()
        msg.set_payload(file, charset="utf-8")

    msg.add_header("Content-Type", "application/octet-stream")
    msg.add_header("Content-Disposition", "attachment", filename = filename)


    smtp = smtplib.SMTP(smtp_server)
    # smtp.connect('smtp.126.com')
    smtp.login(sender, password)
    # smtp.set_debuglevel(1)

    try:
        smtp.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print("fail")
    else:
        print("ok")
    finally:
        smtp.quit()


if __name__ == "__main__":
    options.parse_command_line()

    application = Application([
        (r"/pushbook", MainHandler),
    ], debug=True)

    http_server = HTTPServer(application)
    http_server.listen(8887)
    IOLoop.current().start()

