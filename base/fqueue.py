#!/usr/bin/python
# -*- coding: utf8 -*-


import queue
import threading
from core.message import FObject

JOBQ_EVT_NONE = 0x0001

class MessageQueueFormat(FObject):
    def __init__(self, **kwargs):
        self.evt = None
        self.token = None
        self.provider = None
        self.sender = None
        self.payload = None
        self.callback = None

        super.__init__(MessageQueueFormat, **kwargs)


class FQueue(object):
    def __init__(self, threadnumb = 1):
        self.threadnumb = threadnumb
        self.job = queue.Queue()
        self.threads = []

    def handJob(self):
        while True:
            item = self.job.get()
            if item is None:
                break
            print(item)
            self.job.task_done()

    def start(self):
        for i in range(self.threadnumb):
            print('start thread job')
            pthead = threading.Thread(target=self.handJob)
            pthead.start()
            self.threads.append(pthead)

        # block until all tasks are done
        self.job.join()

    def stop(self):
        # stop workers
        for i in range(self.threadnumb):
            self.job.put(None)

        for pthead in self.threads:
            pthead.join()

    def publish(self, item = None):
        self.job.put(item)



class FQueueJobSinger(object):
    instance = None

    class __FQueueJobSinger:
        def __init__(self, threadnumb=1):
            self.fqueue = FQueue(threadnumb)

        def start(self):
            self.fqueue.start()

        def stop(self):
            self.fqueue.stop()

        def add(self, item):
            assert isinstance(item, MessageQueueFormat)
            self.fqueue.publish(item)

    def __new__(cls, threadnumb):
        if not FQueueJobSinger.instance:
            FQueueJobSinger.instance = FQueueJobSinger.__FQueueJobSinger(threadnumb = threadnumb)
        return FQueueJobSinger.instance

    def __getattr__(self, value):
        return getattr(self.__instance, value)

    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)
