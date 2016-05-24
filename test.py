# -*- coding: UTF-8 -*- 
# Created by qiu on 16-5-2
#

"""
from pymongo import MongoClient
import datetime
import hashlib
from urllib import request
import os

from bs4 import BeautifulSoup
import requests
from PIL import Image, ImageDraw


class Test():
    def __init__(self):
        self.client = MongoClient()
        self.db = self.client.zqreadDB

    def insert_user(self):

        for i in range(10):
            m = hashlib.md5()
            m.update("qiu0130".encode("utf-8"))
            self.db.user.insert({'photo': 'photo/3152ca324dda20cb320ca71e79a2ba44.jpg',
                                 'kindle_email': '8615545995928@kindle.cn',
                                 'hashed_password': b'$2b$12$jbtDTnU0d2xIczdKuDwznuF5RISUMAu4I7InJUXsCTXldlCSyTVDG',
                                 'push_count': 0,
                                 'email': '1051704885@qq.com',
                                 'upload_count': 0, 'createAt': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 'username': 'qiu0130',
                                 'id': m.hexdigest(),
                                })
        print("insert user ")
    def drop_user(self):
        self.db.user.drop()
        print("drop user")

    def insert_book(self):

        for i in range(16):
            self.db.book.insert({"id": "123456", "name": "西游记", "author": "吴承恩,清代","photo":
                "photo/3152ca324dda20cb320ca71e79a2ba44.jpg",
                                 "tag": "文学", "createAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "type": "push"})
        for i in range(16):
             self.db.book.insert({"id": "123456", "name": "西游记", "author": "吴承恩,清代","photo":
                "photo/3152ca324dda20cb320ca71e79a2ba44.jpg",
                                 "tag": "文学", "createAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  "type": "upload"})
        print("insert book ")

    def drop_book(self):
        self.db.book.drop()
        print("drop book")

    def book_image(self, url, book_tag, book_type):

        doc = requests.get(url).text

        items = BeautifulSoup(doc, "lxml").find_all(class_ = "u-bookitm1 j-bookitm")

        for item in items:
            img = item.find(class_ = "cover").find("img").get("src")
            tmp = item.find(class_ = "info")
            name = tmp.find("a").text
            author = tmp.find(class_ = "u-author").text

            m2 = hashlib.md5()
            m2.update(img.split("/")[-1].split(".")[0].encode("utf-8"))
            ob = img.split("/")[-1].split(".")[-1]

            dir = os.path.join(os.path.join(os.getcwd(), "static/image/"))
            if not os.path.exists(dir):
                os.mkdir(dir)

            if ob not in ["jpg", "png", "gif"]:
                ob = "jpg"

            im = m2.hexdigest() + '.' + (ob)

            try:
                request.urlretrieve(img, os.path.join(dir, im))
            except Exception as e:
                print(e)
            else:

                m1 = hashlib.md5()
                m1.update(name.encode("utf-8"))
                self.db.book.insert(
                    { "id": m1.hexdigest(), "name": "七周七语言", "author": "Bruce A.Tate","photo":
                    "image/" + im, "tag": book_tag, "createAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  "type": book_type,
                     }
                )
                img = Image.open(os.path.join(dir, im))
                img = img.resize((170,150), Image.ANTIALIAS)
                img.save(os.path.join(dir, im))




    def test_online(self):
        import time
        self.db.online.drop()
        self.db.anaylze.drop()

        self.db.create_collection("online", max = 6, size = 1024, capped = True)
        self.db.anaylze.insert({"online": 0})
        for i in range(20):
            time.sleep(1)
            self.db.online.insert({"username": "qiu013"+ str(i),
                                   "photo": "photo/3152ca324dda20cb320ca71e79a2ba44.jpg",
                                  "loginAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    def test_tags(self):


        names = ["计算机艺术", "文学小说", "古典名著", "人文艺术"]
        uris = ['it-art', 'liter-novel', 'history', 'human-art']

        self.db.tags.drop()

        for name, uri in zip(names, uris):
            self.db.tags.insert({"name": name, "uri": uri})


    def change_upload(self):

        books = self.db.book.find()
        for book in books:
            book["mode"] = "upload"
            del book["_id"]
            self.db.book.insert(book)

        print("end ..")



def make_img(filepath):
    for file in os.listdir(filepath):

        img = Image.open(os.path.join(filepath, file))
        # img.thumbnail((150, 180), Image.ANTIALIAS)
        # if file.split(".")[-1] == "jpg":
        #     img.save(os.path.join(filepath, file))

        img = img.resize((150, 160), Image.ANTIALIAS)

        if file.split(".")[-1]  in ["jpg"]:
            img.save(os.path.join(filepath, file))
            print('---------resize pic ...' + file)

"""

from envelopes import Envelope
import os

def send_kindle_book(kindle_email):
    envelope = Envelope(
        from_addr=(u'zqkindle@126.com', u"from qiu"),
        to_addr=(kindle_email, u"to qiu0130"),
        subject=u"book",
        text_body=u"test"
    )

    envelope.add_attachment(os.path.join(os.getcwd(), "README.md"))

    # Send the envelope using an ad-hoc connection...
    try:
        envelope.send('smtp.126.com', login='zqkindle@126.com',
              password='qiu63876092', tls=True, port = 25)
    except Exception as e:

        print(e)
    else:
        print("end..")


if __name__ == "__main__":
    import threading
    threading.Thread(target=send_kindle_book, args = (u"1051704885@qq.com", )).start()








