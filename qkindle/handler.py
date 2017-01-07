# -*- coding: utf-8 -*-

import os
import re
import time
import uuid
import hashlib
import bcrypt
import datetime
import tornado.gen
from tornado import escape
import concurrent.futures
import pymongo
import threading
from PIL import Image

from utils import send_email_to_kindle
from base import BaseHandler


executor = concurrent.futures.ThreadPoolExecutor(3)
UPLOAD_LIMIT = 12
PUSH_LIMIT = 12
HOME_LIMIT = 8
HOME_ACTIVE = 6

per_page = 10
expires_cookie = 30 * 60

class HomeIndexHandler(BaseHandler):
    """
        Home Page
    """
    @tornado.gen.coroutine
    def get(self, tag):
        if tag == "tip":
            self.render("tips.html")

        _tag = yield self.db.tags.find().to_list(None)
        _count = yield self.db.user.count()
        _online = yield self.db.user.find()\
            .sort("loginAt", pymongo.DESCENDING)\
            .limit(HOME_ACTIVE).to_list(None)

        if tag == "recent":
            _push_books = yield self.db.book.find({"mode": "push"})\
                .sort("createdAt", pymongo.DESCENDING)\
                .limit(HOME_LIMIT).to_list(None)

            _upload_books = yield self.db.book.find({"mode": "upload"}) \
                .sort("createdAt", pymongo.DESCENDING) \
                .limit(HOME_LIMIT).to_list(None)
        else:
            index = yield self.db.tags.find_one({"index": tag})
            if not index:
                self.render("404.html")

            _push_books = yield self.db.book.find({"mode": "push", "tag": index["name"]})\
                .sort("createdAt", pymongo.DESCENDING)\
                .limit(HOME_LIMIT).to_list(None)

            _upload_books = yield self.db.book.find({"mode": "upload", "tag": index["name"]})\
                .sort("createdAt", pymongo.DESCENDING) \
                .limit(HOME_LIMIT).to_list(None)

        self.render("main.html",
                    count=_count,
                    push_title="最新推送图书",
                    upload_title="最新上传图书",
                    push_books=_push_books,
                    upload_books=_upload_books,
                    tags=_tag,
                    mode="main",
                    online=_online,
                    )

class PushIndexHandler(BaseHandler):
    """
        Push Page
    """
    @tornado.gen.coroutine
    def get(self, tag, page):
        _tag = yield self.db.tags.find().to_list(None)
        _count = yield self.db.user.count()
        _online = yield self.db.user.find() \
            .sort("loginAt", pymongo.DESCENDING) \
            .limit(HOME_ACTIVE).to_list(None)

        _skip = (int(page) - 1) * UPLOAD_LIMIT

        if tag == "recent":
            _upload_books = yield self.db.book.find({"mode": "push"}) \
                .sort("createdAt", pymongo.DESCENDING) \
                .skip(_skip).limit(UPLOAD_LIMIT) \
                .to_list(None)
            _upload_count = yield self.db.book.find({"mode": "push"}).count()

        else:
            index = yield self.db.tags.find_one({"index": tag})

            _upload_books = yield self.db.book.find({"mode": "push", "tag": index["nickname"]}) \
                .sort("createdAt", pymongo.DESCENDING) \
                .skip(_skip) \
                .limit(UPLOAD_LIMIT) \
                .to_list(None)

            _upload_count = yield self.db.book.find({"mode": "push", "tag": index["nickname"]}) \
                .sort("createdAt", pymongo.DESCENDING) \
                .count()

        _page_count = 0 if _upload_count % UPLOAD_LIMIT == 0 else 1 + int(_upload_count / UPLOAD_LIMIT)

        self.render("push.html",
                    count=_count,
                    online=_online,
                    tags=_tag,
                    page_count=int(_page_count),
                    push_books=_upload_books,
                    push_title="全部推送图书",
                    mode="push",
                    index=tag,
                    )

    @tornado.gen.coroutine
    def post(self, book, name):
        _uri = self.get_argument("uri", None)

        if _uri is not None:
            _user = yield self.db.user.find_one({"username": tornado.escape.native_str(self.current_user)},
                                                {"kindle_email": 1, "push_count": 1})

            if name in _user["push_count"]:
                self.render("info.html", info="图书已经推送过", uri=_uri)
                return

            _book = yield self.db.book.find_one({"name": name, "mode": "push"})
            if not _book:
                self.render("info.html", info="推送的图书不存在", uri=_uri)
                return

            threading.Thread(target=send_email_to_kindle, args=(_user["kindle_email"], _book["file"])).start()
            yield self.db.user.update({"username": tornado.escape.native_str(self.current_user)},
                                      {"$addToSet": {"push_count": name}})
            self.render("info.html", info="推送成功", uri=_uri)
        else:
            self.redirect("/main/recent")


class UploadIndexHandler(BaseHandler):
    """
        Upload Page
    """
    @tornado.gen.coroutine
    def get(self, tag, page):

        _tag = yield self.db.tags.find().to_list(None)
        _count = yield self.db.user.count()
        _online = yield self.db.user.find()\
            .sort("loginAt", pymongo.DESCENDING)\
            .limit(HOME_ACTIVE).to_list(None)

        _skip = (int(page) - 1) * UPLOAD_LIMIT

        if tag == "recent":
            _upload_books = yield self.db.book.find({"mode": "upload"})\
                .sort("createdAt", pymongo.DESCENDING)\
                .skip(_skip).limit(UPLOAD_LIMIT)\
                .to_list(None)
            _upload_count = yield self.db.book.find({"mode": "upload"}).count()

        else:
            index = yield self.db.tags.find_one({"index": tag})

            _upload_books = yield self.db.book.find({"mode": "upload", "tag": index["nickname"]})\
                .sort("createdAt", pymongo.DESCENDING)\
                .skip(_skip)\
                .limit(UPLOAD_LIMIT)\
                .to_list(None)

            _upload_count = yield self.db.book.find({"mode": "upload", "tag": index["nickname"]})\
                .sort("createdAt", pymongo.DESCENDING)\
                .count()

        _page_count = 0 if _upload_count % UPLOAD_LIMIT == 0 else 1 + int(_upload_count / UPLOAD_LIMIT)

        self.render("upload.html",
                    count=_count,
                    online=_online,
                    tags=_tag,
                    page_count=int(_page_count),
                    upload_books=_upload_books,
                    upload_title="全部上传图书",
                    mode="upload",
                    index=tag,
                    )

    @tornado.gen.coroutine
    def post(self, book, name):

        _uri = self.get_argument("uri", None)
        if _uri is not None:
            file = self.request.files.get("book_file", None)

            if not file:
                self.render("info.html", info="请添加图书", uri=_uri)
                return

            file = file[0]
            book_name = file.get("filename", None)
            if not book_name:
                self.render("info.html", info="图书不存在", uri=_uri)
                return

            upload_path = os.path.join(self.settings["static_path"], "book")
            if not os.path.exists(upload_path):
                os.mkdir(upload_path)

            with open(os.path.join(upload_path, book_name), 'wb') as up:
                up.write(file['body'])

            yield self.db.user.update({"username": tornado.escape.native_str(self.current_user)}, {"$inc": {
                "upload_count": 1}})
            yield self.db.book.update({"name": name}, {"$set": {"mode": "push","file": "kindle push测试.pdf", "createdAt":
                                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}})

            self.render("info.html", info="上传成功", uri=_uri)
        else:
            self.redirect("/main/recent")


class RegisterHandler(BaseHandler):
    """
        User Register Page
    """
    def get(self):
        self.render("register.html", error=None)

    @tornado.gen.coroutine
    def post(self):

        username = self.get_argument("username", None)
        verify_email = self.get_argument("verify_email", None)
        kindle_email = self.get_argument("kindle_email", None)
        password = self.get_argument("password", None)

        print(username, verify_email, kindle_email, password)
        if any([username, verify_email, kindle_email, password]):
            self.render("register.html", error="请填写完整")

        # kindle_verify = re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', kindle)
        email_verify = re.compile('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$')

        # print(email_verify.match(verify_email))

        if not email_verify.match(verify_email):
            self.render("register.html", error="验证邮箱有误")

        if not email_verify.match(kindle_email):
            self.render("register.html", error="kindle邮箱有误")
        user = yield self.db.user.find_one({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)})
        print(user)

        if user:
            self.render("register.html", error="用户已存在")

        hashed_password = yield executor.submit(bcrypt.hashpw,
                                                tornado.escape.utf8(password),
                                                bcrypt.gensalt())
        user = {
            "username": username,
            "verify_email": verify_email,
            "kindle_email": kindle_email,
            "hashed_password": hashed_password,
            "createdAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "push_count": [],
            "upload_count": 0,
            "photo": "photo/default.jpg",    # 默认头像
            "_id": uuid.uuid5(uuid.NAMESPACE_DNS, username),
            "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        yield self.db.user.insert(user)
        # yield self.db.online.insert({
        #         "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #         "username": user["username"],
        #         "url": "/username/" + user["username"],
        #         "photo": user["photo"]
        #     })

        self.set_secure_cookie("test", username, expires=time.time() + expires_cookie)
        self.redirect("/username/" + user["username"])

class LoginHandlder(BaseHandler):
    """
        User Login Page
    """

    def get(self):
        self.render("login.html", error=None)

    @tornado.gen.coroutine
    def post(self):
        username = self.get_argument("username", None)

        user = yield self.db.user.find_one({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)})
        if not user:
            self.render("login.html", error="用户不存在")

        password = self.get_argument("password")
        hashed_password = yield executor.submit(bcrypt.hashpw,
                                                escape.utf8(password),
                                                escape.utf8(user.get("hashed_password")))

        if hashed_password != user.get('hased_password'):
            self.render("login.html", error="密码错误")


            # yield self.db.online.insert({
            #     "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            #     "username": user["username"],
            #     "url": "/username/" + user["username"],
            #     "photo": user["photo"]
            # })
        yield self.db.user.update({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)},
                                  {"$set": {"loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}})

        self.set_secure_cookie("test", user["username"], expires=time.time() + expires_cookie)
        self.redirect("/main/recent")

class LogoutHandler(BaseHandler):
    """
        User Logout Page
    """
    def get(self):
        self.clear_cookie("test")
        self.redirect("/main/recent")

class UserInfoHandler(BaseHandler):
    """
        Personal Info Page
    """
    @tornado.gen.coroutine
    def get(self, username):

        user = yield self.db.user.find_one({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)})
        if not user:
            self.redirect("/auth/login")
        self.render("user.html", user=user, cur_user=username)

    @tornado.gen.coroutine
    def post(self, username):

        verify_email = self.get_argument("verify_email", None)
        kindle_email = self.get_argument("kindle_email", None)
        password = self.get_argument("password", None)

        user = {}

        if verify_email:
            user["verify_email"] = verify_email
        if kindle_email:
            user["kindle_email"] = kindle_email
        if password:
            user["hashed_password"] = yield executor.submit(bcrypt.hashpw,
                                                            escape.utf8(password),
                                                            bcrypt.gensalt())
        if user:
            yield self.db.user.update({"_id": uuid.uuid5(uuid.NAMESPACE_DNS, username)}, {"$set": user})
        self.redirect("/username/" + username)

class AvatarHandler(BaseHandler):
    """
        Personal Avatar Page
    """
    @tornado.gen.coroutine
    def post(self, name):
        _uri = self.get_argument("uri", "None")
        file = self.request.files["avatar_file"][0]
        if not file or not _uri:
            self.render("info.html", info="修改头像失败", uri=_uri)
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
                                    {"$set": {"photo": "photo/" + img_name, "loginAt":
                                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") }}, multi=True)

        if not _uri:
            self.redirect("/main/recent")

        #self.set_secure_cookie("test", _uri)
        self.redirect("/username/" + _uri)


class BookHandler(BaseHandler):
    """
        Book Info Page
    """
    @tornado.gen.coroutine
    def post(self, bookname):
        _uri = self.get_argument("uri", None)

        if _uri:
            _book = yield self.db.book.find_one({"name": bookname})
            self.render("book.html", uri=_uri, book=_book)
        else:
            self.redirect("/main/recent")



