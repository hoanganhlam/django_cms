#!/usr/bin/python
# -*- coding: utf8 -*-

class FObject(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            # if hasattr(self, key):
            setattr(self, key, value)
            # else:
            #     pass

    def setAttr(self, key, val):
        self.__setattr__(key, val)

    def getAttr(self):
        return self.__dict__


class PublisMessage(FObject):
    def __init__(self, **kwargs):
        # self.event = None
        self.data = None
        self.fromAddr = None
        self.toAddr = None
        self.sessionid = None
        super(PublisMessage, self).__init__(**kwargs)


class KafMsq(FObject):
    def __init__(self, **kwargs):
        self.topic = None
        self.partition = 0
        # self.offset = None
        self.timestamp = 100
        self.value = None
        self.event = None
        self.sessionid = None
        super(KafMsq, self).__init__(**kwargs)

# class MsgConsumer(FObject):
#     def __init__(self, **kwargs):
#         self.topic = None
#         self.partition = None
#         self.offset = None
#         self.timestamp = None
#         super(MsgConsumer, self).__init__(**kwargs)


class BaseMsgSyn(FObject):
    def __int__(self):
        pass

    def put_json(self):
        return ''

    def parse_json(self, value):
        return dict()
