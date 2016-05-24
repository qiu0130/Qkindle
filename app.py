# -*- coding: UTF-8 -*- 
# Created by qiu on 16-4-21
#
import time
import uuid
import hashlib
import bcrypt
import os
import datetime
import tornado.web
import tornado.ioloop
import tornado.gen
import motor.motor_tornado
import tornado.escape
import traceback
import concurrent.futures
import pymongo
import threading

from tornado.httpserver import HTTPServer
from tornado.options import define, options
from PIL import Image

from push import send_email_to_kindle


define("port", help="run on port", default=8889, type=int)

executor = concurrent.futures.ThreadPoolExecutor(3)



class BaseHandler(tornado.web.RequestHandler):
    """
        基类
    """
    OTHER_LIMIT = 4
    MAIN_LIMIT = 4

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
                # 重载404页面
                self.render("404.html")

            self.finish("<html><title>%(code)d: %(message)s</title>"
                        "<body>%(code)d: %(message)s</body></html>" % {
                            "code": status_code,
                            "message": self._reason,
                        })

class BookMainHandler(BaseHandler):
    """
        主页
    """
    @tornado.gen.coroutine
    def get(self, index):

        _tag = yield self.db.tags.find().to_list(None)
        _analyze = yield self.db.user.count()

        _online = yield self.db.online.find().sort("loginAt", pymongo.DESCENDING).to_list(None)

        if index == "recent":
            push_books = yield self.db.book.find({"mode": "push"}).sort("createdAt", pymongo.DESCENDING).limit(
                BaseHandler.MAIN_LIMIT).to_list(None)

            upload_books = yield self.db.book.find({"mode": "upload"}).sort("createdAt", pymongo.DESCENDING).limit(
                BaseHandler.MAIN_LIMIT).to_list(None)
        else:
            cur_tag = yield self.db.tags.find_one({"index": index})

            if not cur_tag:
                self.render("error.html", error = "not found current tag")
                return

            push_books = yield  self.db.book.find({"mode": "push", "tag": cur_tag["name"]}).sort("createdAt",
                         pymongo.DESCENDING).limit(BaseHandler.MAIN_LIMIT).to_list(None)

            upload_books = yield  self.db.book.find({"mode": "upload","tag": cur_tag["name"]}).sort("createdAt",
                           pymongo.DESCENDING).limit(BaseHandler.MAIN_LIMIT).to_list(None)

        self.render("main.html",
                    visited = _analyze,
                    push_title = "最新推送图书",
                    upload_title = "最新上传图书",
                    push_books = push_books,
                    upload_books = upload_books,
                    tags = _tag,
                    mode = "main",
                    online = _online,
                    )

class PushIndexHandler(BaseHandler):
    """
        图书推送首页
    """
    @tornado.gen.coroutine
    def get(self, index, page):

        _tag = yield self.db.tags.find().to_list(None)
        _analyze = yield self.db.analyze.find_one()
        _online = yield self.db.online.find().sort("loginAt", pymongo.DESCENDING).to_list(None)

        skip_page = (int(page) - 1) * BaseHandler.OTHER_LIMIT

        if index == "recent":
            push_books = yield self.db.book.find({"mode": "push"}).sort("createdAt", pymongo.DESCENDING).limit(
                         BaseHandler.OTHER_LIMIT).to_list(None)
            _pages = yield self.db.book.count()

        else:
            cur_tag = yield self.db.tags.find_one({"index": index})
            if not cur_tag:
                self.render("error.html", error = "not found current tag")
                return

            push_books = yield self.db.book.find({ "mode": "push","tag": cur_tag["name"]}).sort("createdAt",
                         pymongo.DESCENDING).skip(skip_page).limit(BaseHandler.OTHER_LIMIT).to_list(None)

            _pages = yield self.db.book.find({"mode": "push", "tag": cur_tag["name"]}).sort("createdAt",
                        pymongo.DESCENDING).count()

        if int(_pages % BaseHandler.OTHER_LIMIT) == 0:
            page_count = int(_pages / BaseHandler.OTHER_LIMIT)
        else:
            page_count = int(_pages / BaseHandler.OTHER_LIMIT) + 1

        self.render("push.html",
                    visited = 0 if not _analyze else _analyze["visited"],
                    online = _online,
                    tags= _tag,
                    page_count = page_count,
                    push_books = push_books,
                    push_title = "全部推送图书",
                    mode = "push",
                    index = index)

    @tornado.gen.coroutine
    def post(self, book, name):
        _uri = self.get_argument("uri", None)

        if _uri is not None:
            _user = yield self.db.user.find_one({"username": tornado.escape.native_str(self.current_user)},
                                    {"kindle_email": 1})
            _book = yield self.db.book.find_one({"name": name})
            if not _book or not _user:
                self.render("error.html", error = "没有找到用户或图书不存在")
                return

            threading.Thread(target=send_email_to_kindle, args=(_user["kindle_email"], _book["name"])).start()

            self.redirect(_uri)
        else:
            self.redirect("/main/recent")

    # def send_to_kindle_email(self, future, stmp_sever, password, from_email, to_email, subject):
    #
    #     envelope = Envelope(
    #         from_addr= (from_email, "from {}".format(from_email)),
    #         to_addr=(to_email, "to {}".format(to_email)),
    #         subject = subject.split(".")[0],
    #         text_body = subject,
    #     )
    #     book_dir = os.path.join(self.settings["static_path"], "book")
    #     envelope.add_attachment(os.path.join(book_dir, subject))
    #
    #     try:
    #         envelope.send(stmp_sever, login = from_email, password = password, tls = True, port = 25)
    #     except Exception as e:
    #         print(e)
    #         future.set_future("no")
    #     else:
    #         future.set_future("yes")

    # @tornado.gen.coroutine
    # def push_book_handler(self, filename, kindle_email):
    #     future = concurrent.futures.Future()
    #     threading.Thread(target=send_email_to_kindle, args=(future, kindle_email, filename)).start()
    #     return future

class UploadIndexHandler(BaseHandler):
    """
        图书上传首页
    """
    @tornado.gen.coroutine
    def get(self, index, page):

        _tag = yield self.db.tags.find().to_list(None)

        _analyze = yield self.db.user.count()
        _online = yield self.db.online.find().sort("loginAt", pymongo.DESCENDING).to_list(None)



        skip_page = (int(page) - 1) * BaseHandler.OTHER_LIMIT

        if index == "recent":
            upload_books = yield self.db.book.find({"mode":"upload"}).sort("createdAt",pymongo.DESCENDING).limit(
                BaseHandler.OTHER_LIMIT).to_list(None)
            _pages = yield self.db.book.count()

        else:
            cur_tag = yield self.db.tags.find_one({"index": index})
            if not cur_tag:
                self.render("error.html", error = "not found current tag")
                return

            upload_books = yield self.db.book.find({ "mode":"upload","tag": cur_tag["name"]}).sort(
                "createdAt",pymongo.DESCENDING).skip(skip_page).limit(BaseHandler.OTHER_LIMIT).to_list(None)

            _pages = yield self.db.book.find({"mode": "push", "tag": cur_tag["name"]}).sort("createdAt",
                        pymongo.DESCENDING).count()

        if int(_pages % BaseHandler.OTHER_LIMIT) == 0:
            page_count = int(_pages / BaseHandler.OTHER_LIMIT)
        else:
            page_count = int(_pages / BaseHandler.OTHER_LIMIT) + 1

        self.render("upload.html",
                    visited = _analyze,
                    online = _online,
                    tags= _tag,
                    page_count = page_count,
                    upload_books = upload_books,
                    upload_title = "全部上传图书",
                    mode = "upload",
                    index = index,
                   )


    @tornado.gen.coroutine
    def post(self, book, name):

        upload_book = yield self.db.book.find_one({"name": name})
        if upload_book["mode"] == "upload":
            self.render("error.html", error = "图书已存在！")
            return

        _uri = self.get_argument("uri", None)
        file = self.request.files.get("book_file", None)
        if not file or len(file) < 1:
            self.render("error.html", error = "请添加图书")
            return

        file = file[0]
        book_name = file.get("filename", None)
        if not book_name:
            self.render("error.html", error = "图书不存在")
            return

        upload_path = os.path.join(self.settings["static_path"], "book")
        if not os.path.exists(upload_path):
            os.mkdir(upload_path)

        with open(os.path.join(upload_path, book_name), 'wb') as up:
            up.write(file['body'])

        yield self.db.user.update({"username": tornado.escape.native_str(self.current_user)}, {"$inc": {
            "upload_count": 1}})
        yield self.db.book.update({"name": name}, {"$set": {"mode": "push"}})

        if os.path.isfile(os.path.join(upload_path, book_name)):
            self.redirect(_uri)
        else:
            self.render("error.html", error = "图书上传失败")


class PartLineModlue(tornado.web.UIModule):
    """
        push and upload title
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

    @tornado.gen.coroutine
    def post(self):

        username = self.get_argument("username", None)
        email = self.get_argument("email", None)
        kindle_email = self.get_argument("kindle_email", None)
        password = self.get_argument("password", None)


        if not username or not email or not kindle_email or not password:
           self.render("register.html", error = "信息不全")

        user = yield self.db.user.find_one({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)})

        if user is not None:
            self.render("register.html", error = "用户已存在")
            return

        hashed_password = yield executor.submit(bcrypt.hashpw, tornado.escape.utf8(password), bcrypt.gensalt())
        user = {
            "username": username,
            "email": email,
            "kindle_email": kindle_email,
            "hashed_password": hashed_password,
            "createdAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "push_count": 0,
            "upload_count": 0,
            "photo": "photo/3152ca324dda20cb320ca71e79a2ba44.jpg", # 默认头像
            "_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)
        }

        yield self.db.user.insert(user)
        yield self.db.online.insert({
                "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": user["username"],
                "url": "/username/" + user["username"],
                "photo": user["photo"]
            })
        yield  self.db.analyze.update({}, {"$inc": {"visited": 1}})

        self.set_secure_cookie("test", username)
        self.redirect("/username/" + user["username"])

class LoginHandlder(BaseHandler):
    """
        用户登陆
    """

    def get(self):
        self.render("login.html", error = None)

    @tornado.gen.coroutine
    def post(self):


        username  = self.get_argument("username", None)
        password = self.get_argument("password", None)

        if username == "qiu" and password == "foryouathousand":
            self.redirect("/admin/")

        user = yield self.db.user.find_one({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)})
        if not user:
            self.render("login.html", error="用户不存在")
            return

        password = self.get_argument("password")

        hashed_password = yield executor.submit(bcrypt.hashpw, tornado.escape.utf8(password),
                                        tornado.escape.utf8(user["hashed_password"]))

        if hashed_password == user["hashed_password"]:

            yield self.db.analyze.update({}, {"$inc": {"visited": 1}})

            yield self.db.online.insert({
                "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": user["username"],
                "url": "/username/" + user["username"],
                "photo": user["photo"]
            })

            self.set_secure_cookie("test", user["username"])
            self.redirect("/main/recent")
        else:
            self.render("login.html", error="密码错误")

class LogoutHandler(BaseHandler):
    """
        用户退出
    """
    def get(self):
        self.clear_cookie("test")
        self.redirect("/main/recent")

class UsernameHandler(BaseHandler):
    """
        用户基本信息
    """
    @tornado.gen.coroutine
    def get(self, name):

        user = yield self.db.user.find_one({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, name)})
        if not user:
            self.redirect("/auth/login")
        self.render("userinfo.html", user = user)

    @tornado.gen.coroutine
    def post(self, name):

        email = self.get_argument("email", None)
        kindle_email = self.get_argument("kindle_email", None)
        password = self.get_argument("password", None)

        user = {}
        if email is not None:
            user["email"] = email
        if kindle_email is not None:
            user["kindle_email"] = kindle_email
        if password is not None:
            user["hashed_password"] = yield executor.submit(bcrypt.hashpw, tornado.escape.utf8(password),
                                                    bcrypt.gensalt())
        if user is not None:
            yield self.db.user.update({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, name)}, {"$set": user})
        self.redirect("/username/" + name)


class AvatarHandler(BaseHandler):

    @tornado.gen.coroutine
    def post(self, name):
        _uri  = self.get_argument("uri", "None")
        file = self.request.files["avatar_file"][0]
        if not file:
            self.render("error.html", error = "上传头像失败")
            return

        upload_path = os.path.join(self.settings["static_path"], "photo")
        if not os.path.exists(upload_path):
            os.mkdir(upload_path)

        file_name = file["filename"]

        m = hashlib.md5()
        m.update(file_name.encode("utf-8"))
        img_name = m.hexdigest() + "." + file_name.split(".")[-1]
        img_path = os.path.join(upload_path, img_name)
        with open(img_path, 'wb') as up:
            up.write(file['body'])

        im = Image.open(img_path)
        im_reszie = im.resize((100, 100), Image.ANTIALIAS)
        im_reszie.save(img_path)

        yield self.db.user.update({"username": tornado.escape.native_str(self.current_user)},
                                  {"$set": {"photo": "photo/" + img_name }})
        yield self.db.online.update({"username": tornado.escape.native_str(self.current_user)},
                                    {"$set": {"photo": "photo/" + img_name,
                                               "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),}})

        if not _uri:
            self.redirect("/main/recent")
        self.redirect(_uri)

class BookHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self, name):

        _book = yield  self.db.book.find_one({"name": name})
        self.render("book.html",
                    book = _book,
                    )

class Application(tornado.web.Application):
    def __init__(self):

        motor_db = motor.motor_tornado.MotorClient().zqreadDB

        headlers = [
            (r"/auth/login", LoginHandlder),
            (r"/auth/logout", LogoutHandler),
            (r"/auth/register", RegisterHandler),

            (r"/main/(.*)", BookMainHandler),

            (r"/push/(.*)/(.*)", PushIndexHandler),
            (r"/upload/(.*)/(.*)", UploadIndexHandler),
            (r"/username/(.*)", UsernameHandler),
            (r"/admin/(.*)", AdminHandler),
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
            index = self.get_argument("index", None)
            name = self.get_argument("name", None)
            self.add_tag(index, name)
            self.write({ "index": index, "name": name})

        elif post_type == "coll":
            colletion = self.get_argument("collection", None)
            self.write({"collection": colletion, "status": self.drop_collection()})
        self.flush()

    def add_book(self, img, author, name, tag, mode):
        self.db.book.insert({
            "img": "image/" + img,
            "author": author,
            "name": name,
            "tag": tag,
            "mode": mode,
            "createdAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    def add_tag(self, index, name):
        self.db.tags.insert({
            "index": index,
            "name": name,
        })

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
        return reslut

    def create_collection(self, coll="online", size=1024, max=6, flag = True):
        self.db.create_collection(coll, size = size, max = max, capped = flag)


if __name__ == "__main__":

    options.parse_command_line()
    http_server = HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()
