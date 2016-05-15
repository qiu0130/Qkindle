# -*- coding: UTF-8 -*- 
# Created by qiu on 16-4-21
#
import time
import hashlib
import bcrypt
import os
import datetime
import tornado.web
import tornado.ioloop
import tornado.gen
import motor.motor_tornado
import tornado.escape
from pymongo import MongoClient
import pymongo

from tornado.web import RequestHandler
from tornado.httpserver import HTTPServer

import concurrent.futures

from tornado.options import define, options
import traceback

from PIL import Image, ImageDraw


define("port", help="run on port", default=8888, type=int)
define("mongodb", help="mongodb name", default="db", type=str)


# 异步加密
# executor = concurrent.futures.ThreadPoolExecutor(2)


class BaseHandler(tornado.web.RequestHandler):
    """
        基类
        cookie获取，验证登录状态
        获取mondgodb　DB
    """
    MIN_LIMIT = 12
    MAIN_LIMIT = 8
    PUSH_LINE = "推送图书"
    UPLOAD_LINE = "上传图书"


    def get_current_user(self):
        return self.get_secure_cookie("test")

    @property
    def db(self):
        return self.settings["db"]

    def write_error(self, status_code, **kwargs):
        """Override to implement custom error pages.

        ``write_error`` may call `write`, `render`, `set_header`, etc
        to produce output as usual.

        If this error was caused by an uncaught exception (including
        HTTPError), an ``exc_info`` triple will be available as
        ``kwargs["exc_info"]``.  Note that this exception may not be
        the "current" exception for purposes of methods like
        ``sys.exc_info()`` or ``traceback.format_exc``.
        """
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            # in debug mode, try to send a traceback
            self.set_header('Content-Type', 'text/plain')
            for line in traceback.format_exception(*kwargs["exc_info"]):
                self.write(line)
            self.finish()
        else:
            if status_code == 404:
                self.render("404.html", error = kwargs["error"])

            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                            "code": status_code,
                            "message": self._reason,
                        })


class BookIndexHandler(BaseHandler):
    """
        主页
    """
    def get(self, index_tag):

        all_tag = self.db.tags.find()
        _user = self.db.user.find_one({"username": tornado.escape.native_str(self.current_user)},
                                      {"id": 1})

        analyze_result = self.db.analyze.find_one()
        all_online = self.db.online.find().sort("loginAt", pymongo.DESCENDING)

        if index_tag == "":
            push_books = self.db.book.find({"mode": "push"}).sort("createdAt", pymongo.DESCENDING).limit(
                BaseHandler.MAIN_LIMIT)
            upload_books = self.db.book.find({"mode": "upload"}).sort("createdAt", pymongo.DESCENDING).limit(
                BaseHandler.MAIN_LIMIT)
        else:
            cur_tag = self.db.tags.find_one({"uri": index_tag})
            push_books = self.db.book.find({"mode": "push", "tag": cur_tag["name"]}).sort("createdAt",
                                                                                   pymongo.DESCENDING).limit(
                BaseHandler.MAIN_LIMIT)
            upload_books = self.db.book.find({"mode": "upload","tag": cur_tag["name"]}).sort("createdAt",
                                                                                   pymongo.DESCENDING).limit(
            BaseHandler.MAIN_LIMIT)

        # if None in [all_tag, analyze_result, push_books, upload_books]:
        #     self.write_error(404)
        #     return

        self.render("main.html",
                    visited = 0 if not analyze_result else analyze_result["visited"],
                    push_line = BaseHandler.PUSH_LINE,
                    upload_line = BaseHandler.UPLOAD_LINE,
                    push_books = push_books,
                    upload_books = upload_books,
                    tags = all_tag,
                    mode = "main",
                    online = all_online,
                    id = None if not _user else _user["id"]
                    )


class PushIndexHandler(BaseHandler):
    """
        图书推送首页
    """
    def get(self, push_tag, page):

        all_tag = self.db.tags.find()
        _user = self.db.user.find_one({"username": tornado.escape.native_str(self.current_user)},
                                      {"id": 1})

        analyze_result = self.db.analyze.find_one()
        all_online = self.db.online.find().sort("loginAt", pymongo.DESCENDING)

        pages = self.db.book.count()

        page_count = pages / BaseHandler.MIN_LIMIT
        skip_page = (int(page) - 1) * BaseHandler.MIN_LIMIT


        if push_tag == "recent":
            push_books = self.db.book.find({"mode": "push"}).sort("createdAt", pymongo.DESCENDING).limit(BaseHandler.MIN_LIMIT)

        else:
            cur_tag = self.db.tags.find_one({"uri": push_tag})
            if not cur_tag:
                self.write_error(404)
                return
            push_books = self.db.book.find({ "mode": "push",
                                             "tag": cur_tag["name"]}).sort("createdAt",
                                            pymongo.DESCENDING).skip(skip_page).limit(
                                        BaseHandler.MIN_LIMIT)

        self.render("push.html",
                    visited = 0 if not analyze_result else analyze_result["visited"],
                    online = all_online,
                    tags= all_tag,
                    page_count = int(page_count),
                    push_books = push_books,
                    push_line = BaseHandler.PUSH_LINE,
                    mode = "push",
                    tag = push_tag,
                    id = None if not _user else _user["id"])

    @tornado.web.authenticated
    def post(self, book, id):

        uri = self.get_argument("uri", None)
        if book == "book" and uri:
            self.push_book_action()
            self.db.user.update({"username": tornado.escape.native_str(self.current_user)}, {"$inc": {"push_count": 1}})

        self.redirect(uri)

    def push_book_action(self):
        pass
class UploadIndexHandler(BaseHandler):
    """
        图书上传首页
    """
    def get(self, upload_tag, page):

        all_tag = self.db.tags.find()
        _user = self.db.user.find_one({"username": tornado.escape.native_str(self.current_user)},
                                      {"id": 1})

        analyze_result = self.db.analyze.find_one()
        all_online = self.db.online.find().sort("loginAt", pymongo.DESCENDING)

        pages = self.db.book.count()

        page_count = pages / BaseHandler.MIN_LIMIT
        skip_page = (int(page) - 1) * BaseHandler.MIN_LIMIT

        if upload_tag == "recent":
            upload_books = self.db.book.find({"mode":"upload"}).sort("createdAt",
                                                                                  pymongo.DESCENDING).limit(
                BaseHandler.MIN_LIMIT)

        else:
            cur_tag = self.db.tags.find_one({"uri": upload_tag})
            if not cur_tag:
                self.write_error(404)
                return
            upload_books = self.db.book.find({ "mode":"upload",
                                             "tag": cur_tag["name"]}).sort("createdAt",
                                            pymongo.DESCENDING).skip(skip_page).limit(
                                        BaseHandler.MIN_LIMIT)

        self.render("upload.html",
                    visited = 0 if not analyze_result else analyze_result["visited"],
                    online = all_online,
                    tags= all_tag,
                    page_count = int(page_count),
                    upload_books = upload_books,
                    upload_line = BaseHandler.UPLOAD_LINE,
                    mode = "upload",
                    tag = upload_tag,
                    id = None if not _user else _user["id"])

    @tornado.web.authenticated
    def post(self, book, id):
        uri = self.get_argument("uri", None)
        file = self.request.files["book_file"][0]
        content_type = file["content_type"]

        if content_type not in ["application/mobi", "application/azw", "application/pdf"]:
            self.render("error.html", error = "图书仅支持.mobi、.azw格式")
            return

        if not file:
            self.render("error.html", error = "图书上传失败")
            return

        upload_path = os.path.join(self.settings["static_path"], "book")
        if not os.path.exists(upload_path):
            os.mkdir(upload_path)

        file_name = file["filename"]
        m = hashlib.md5()
        m.update(file_name.encode("utf-8"))
        img = m.hexdigest() + "." + file_name.split(".")[-1]

        with open(os.path.join(upload_path, img), 'wb') as up:
            up.write(file['body'])

        self.db.user.update({"username": tornado.escape.native_str(self.current_user)}, {"$inc": {"upload_count": 1}})
        self.db.book.update({"id": id}, {"$set": {"mode": "push"}})

        self.redirect(uri)


class PartLineModlue(tornado.web.UIModule):
    """
        分割线UI
    """
    def render(self, line):
        return self.render_string("modules/part_line.html", line=line)


class PushBookModule(tornado.web.UIModule):
    """
        book基本信息
    """

    def render(self, book):
        return self.render_string("modules/push_book.html", book=book)

class UploadBookModule(tornado.web.UIModule):
    """
        book基本信息UI
    """
    def render(self, book):
        return self.render_string("modules/upload_book.html", book=book)


class RegisterHandler(BaseHandler):
    """
        用户注册
    """
    def get(self):
        self.render("register.html", error = None)

    def post(self):
        username = self.get_argument("username", None)
        email = self.get_argument("email", None)
        kindle_email = self.get_argument("kindle_email", None)
        password = self.get_argument("password", None)

        # 对称加密

        if not username or not email or not kindle_email or not password:
           self.render("register.html", error = "信息不全")


        hashed_password = bcrypt.hashpw(tornado.escape.utf8(password),
                                        bcrypt.gensalt())

        # md5
        m = hashlib.md5()
        m.update(username.encode("utf-8"))
        user = {
            "username": username,
            "email": email,
            "kindle_email": kindle_email,
            "hashed_password": hashed_password,
            "createdAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "push_count": 0,
            "upload_count": 0,
            "photo": "photo/3152ca324dda20cb320ca71e79a2ba44.jpg",
            "id": m.hexdigest()
        }

        self.db.user.insert(user)
        self.set_secure_cookie("test", username)
        self.redirect("/username/" + user["id"])

class LoginHandlder(BaseHandler):
    """
        用户登陆
    """

    def get(self):
        self.render("login.html", error=None)

    def post(self):

        user = self.db.user.find_one({"username": self.get_argument("username", None)})
        password = self.get_argument("password")

        if not user:
            self.render("login.html", error="用户不存在")
            return
        hashed_password = bcrypt.hashpw(tornado.escape.utf8(password),
                                        tornado.escape.utf8(user["hashed_password"]))

        if hashed_password == user["hashed_password"]:
            # m = hashlib.md5()
            # m.update(password.encode("utf-8"))

            self.db.analyze.update({}, {"$inc": {"visited": 1}})

            self.db.online.insert({
                "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": user["username"],
                "url": "/username/" + user["id"],
                "photo": user["photo"]
            })
            self.set_secure_cookie("test", user["username"])
            self.redirect("/main/")
        else:
            self.render("login.html", error="密码错误")

class LogoutHandler(BaseHandler):
    """
        用户退出
    """

    def get(self):
        self.clear_cookie("test")
        self.redirect("/main/")


class UsernameHandler(BaseHandler):
    """
        用户基本信息
    """

    def get(self, id):

        user = self.db.user.find_one({"id": id}, {"_id": 0})
        if not user:
            raise tornado.web.HTTPError(404)

        self.render("username.html", user=user, id=user["id"])

    def post(self, id):
        username = self.get_argument("username", None)
        email = self.get_argument("email", None)
        kindle_email = self.get_argument("kindle_email", None)
        password = self.get_argument("password", None)

        # user = self.db.user.find_one({"id": id}, {"username": 1, "email": 1,
        #                                           "kindle_email": 1, "hashed_password": 1, "_id": 0})

        user = {}
        if username:
            user["username"] = username
        if email:
            user["email"] = email
        if kindle_email:
            user["kindle_email"] = kindle_email
        if password:
            user["hashed_password"] = bcrypt.hashpw(tornado.escape.utf8(password),
                                                    bcrypt.gensalt())

        self.db.user.update({"id": id}, {"$set": user})

        self.redirect("/username/" + id)

class Application(tornado.web.Application):
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.zqreadDB

        headlers = [
            (r"/auth/login", LoginHandlder),
            (r"/auth/logout", LogoutHandler),
            (r"/auth/register", RegisterHandler),

            (r"/main/(.*)", BookIndexHandler),

            (r"/push/(.*)/(.*)", PushIndexHandler),
            (r"/upload/(.*)/(.*)", UploadIndexHandler),
            (r"/username/(.*)", UsernameHandler),
            (r"/admin/(.*)", AdminHandler),
        ]

        settings = {
            "db": self.db,
            "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            "login_url": "/auth/login",
            "xsrf_cookies": True,
            "debug": True,
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "static_path": os.path.join(os.path.dirname(__file__), "static"),

            "ui_modules": {
                "PushBook": PushBookModule,
                "UploadBook": UploadBookModule,
                "PartLine": PartLineModlue,
            }
        }
        super(Application, self).__init__(headlers, **settings)


class AdminHandler(BaseHandler):

    def get(self, post_type):
        self.render("admin.html")


    def post(self, post_type):

        self.set_header("Content-Type", "application/json")

        if post_type == "book":
            name = self.get_argument("name", None)
            author = self.get_argument("author", None)
            tag = self.get_argument("tag", None)
            mode = self.get_argument("mode", None)

            file = self.request.files["img"]
            if not file:
                self.write_error(404)
                return

            file = file[0]
            upload_path = os.path.join(self.settings["static_path"], "image")

            if not os.path.exists(upload_path):
                os.mkdir(upload_path)

            file_name = file["filename"]
            m = hashlib.md5()
            m.update(file_name.encode("utf-8"))
            img = m.hexdigest() + "." + file_name.split(".")[-1]
            file_img = os.path.join(upload_path, img)

            with open(file_img, 'wb') as up:
                up.write(file['body'])
            content_type = file["content_type"]

            im = Image.open(file_img)
            im_reszie = im.resize((170, 150), Image.ANTIALIAS)
            im_reszie.save(file_img)

            self.add_book(img, author, name, tag, mode)
            self.write({"name": name, "author": author, "mode": mode, "tag": tag,
                        "img": img, "content_type": content_type})
        elif post_type == "tag":
            uri = self.get_argument("uri", None)
            tag_name = self.get_argument("tag_name", None)
            self.add_tag(uri, tag_name)
            self.write({ "uri": uri, "tag_name": tag_name})
        elif post_type == "coll":
            colletion = self.get_argument("collection", None)
            self.write({"collection": colletion, "status": self.drop_collection()})
        self.flush()

    def add_book(self, img, author, name, tag, mode):
        m = hashlib.md5()
        m.update(name.encode("utf-8"))
        self.db.book.insert({
            "id": m.hexdigest(),
            "img": "image/" + img,
            "author": author,
            "name": name,
            "tag": tag,
            "mode": mode,
            "createdAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    def add_tag(self, uri, name):
        self.db.tags.insert({
            "uri": uri,
            "name": name,
        })

    def clear_zero_analyze(self):
        result = self.db.analyze.update({}, {"visited": 0})
        if result["ok"] == 1:
            return "yes"
        return "no"

    def drop_collection(self, col):
        reslut = ""
        if col == "tags":
            self.db.tags.drop()
            reslut = "drop tags"
        elif col == "book":
            self.db.book.drop()
            reslut = "drop book"
        elif col == "online":
            self.db.online.drop()
            reslut = "drop online"
        elif col == "analyze":
            self.db.analyze.drop()
            reslut = "analyze"
        return reslut

    def create_collection(self, coll, size, max, flag):
        self.db.create_collection(coll, size = size, max = max, capped = flag)

    def create_analyze(self, coll):
        self.db.create_collection(coll)

if __name__ == "__main__":
    options.parse_command_line()

    # db = motor.motor_tornado.MotorClient().zqread_database
    # db.create_collection("online", size = 1024, max = 6, capped = True)

    http_server = HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
