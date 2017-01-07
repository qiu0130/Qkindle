# -*- coding: utf-8 -*-
import hashlib
import os
import time
import uuid
import bcrypt
import datetime
import pymongo
import requests

from PIL import Image
from bs4 import BeautifulSoup
from urllib.request import urlretrieve

class TestModel(object):

    db = pymongo.Connection(host="127.0.0.1", port=27017).qkindle
    @classmethod
    def add_book(cls, tag, mode, name, img, desc, author):

        cls.db.book.insert({
            "img": "image/" + img,
            "author": author,
            "name": name,
            "tag": tag,
            "mode": mode,
            "desc": desc,
            "file": "kindle push测试.pdf",
            "createdAt": time.time()
        })

    @classmethod
    def add_user(cls, username, uemail, kemail, pwd, photo):
        cls.db.user.insert({
            "username": username,
            "verify_email": uemail,
            "kindle_email": kemail,
            "hashed_password": bcrypt.hashpw(pwd.encode("utf-8"), bcrypt.gensalt()),
            "createdAt": time.time(),
            "push_count": [],
            "upload_count": [],
            "photo": "photo/" + photo,
        })


    @classmethod
    def add_tag(cls):
        tags = [{"nickname": "liter", "tag_name": "文学小说"},
                {"nickname": "it", "tag_name": "计算机科学"},
                {"nickname": "phil", "tag_name": "哲学宗教"},
                ]
        for item in tags:
            cls.db.tags.insert({
                "nickname": item["nickname"],
                "tag_name": item["tag_name"],
            })

    @classmethod
    def create(cls, size=2048, max=6, flag=True):
        cls.db.create_collection("online", size=size, max=max, capped=flag)


    @classmethod
    def covert_book(cls, url):
        doc = requests.get(url).text
        items = BeautifulSoup(doc, "lxml").find_all(class_="u-bookitm1 j-bookitm")
        for item in items:
            url = item.find(class_="cover").find("img").get("src")
            tmp = item.find(class_="info")
            bo_name = tmp.find("a").text.strip()
            author = tmp.find(class_="u-author").text.strip()
            page = tmp.find("a").get("href")

            html = requests.get(page).text
            desc = BeautifulSoup(html, "lxml").find(class_="cnt j-cnt").text.strip()

            m2 = hashlib.md5()
            m2.update(url.split("/")[-1].split(".")[0].encode("utf-8"))
            ob = url.split("/")[-1].split(".")[-1]
            dir = "/home/qiu/projects/qkindle_env/Qkindle/qkindle/static/image/"
            if not os.path.exists(dir):
                os.mkdir(dir)
            if ob not in ["jpg", "png", "gif"]:
                ob = "jpg"
            im = m2.hexdigest() + '.' + ob
            try:
                urlretrieve(url, os.path.join(dir, im))
            except Exception:
                im = "default.jpg"
            else:
                img = Image.open(os.path.join(dir, im))
                img = img.resize((170, 150), Image.ANTIALIAS)
                img.save(os.path.join(dir, im))
                print(im)
                cls.add_book(tag="哲学宗教", mode="upload",
                             name=bo_name, author=author, desc=desc, img=im)

def init():
   TestModel.create()
   TestModel.add_tag()

if __name__ == "__main__":

    # init()
    test = TestModel()
    for i in range(15, 18):
      TestModel.covert_book("http://www.kindlepush.com/category/5/0/" + str(i))







