# -*- coding: utf-8 -*-

from tornado.web import UIModule


class PartLineModule(UIModule):
    """
       parting line ui
    """
    def render(self, line):
        return self.render_string("modules/part_line.html", line=line)


class PushBookModule(UIModule):
    """
        push book ui
    """
    def render(self, book):
        return self.render_string("modules/push_book.html", book=book)


class UploadBookModule(UIModule):
    """
        upload book ui
    """
    def render(self, book):
        return self.render_string("modules/upload_book.html", book=book)
