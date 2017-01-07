#!/usr /bin/env python
# -*- coding: utf-8 -*-
# Created by qiu on 16-6-26
#

import os
import hashlib
import datetime
from PIL import Image
from handler import BaseHandler

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

