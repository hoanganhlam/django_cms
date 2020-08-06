#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import os
import logging
import threading
from pymongo import MongoClient, errors
logger = logging.getLogger('django')


class MongoController:
    def __new__(cls):
        if not MongoController.__instance:
            MongoController.__instance = MongoController.__MongoController()
        return MongoController.__instance
    def __getattr__(self, value):
        return getattr(self.__instance, value)
    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)

    class __MongoController:
        client = None
        db = None
        running = False
        def __init__(self):
            pass

        def __reconnect(self):
            self.config = {
                'host': os.getenv('MONGO_HOST', 'localhost'),
                'port': int(os.getenv('MONGO_PORT', 27017)),
                # 'maxPoolSize': int(os.getenv('MONGO_MAXPOOLSIZE')),
                'maxPoolSize': None,
            }
            try:
                while self.client is None:
                    try:
                        logger.info('Mongo is trying connect ...')
                        self.client = MongoClient(host=self.config['host'], port=self.config['port'],
                                                  maxPoolSize=self.config['maxPoolSize'])
                        # self.client.server_info()
                    except Exception as ex:
                        logger.warning('Mongo is connected failed')
                    if self.client is not None:
                        break
                    time.sleep(2)
                self.running = True

            except errors.ServerSelectionTimeoutError as err:
                print(err)
                self.running = False

            except Exception as ex:
                print(str(ex))
                self.running = False

            finally:
                if self.running == False:
                    logger.info('Mongo is connected failed')
                else:
                    logger.info('Mongo connected successfull')

        def close(self):
            self.client.close()

        def start(self):
            if not self.running:
                self.pthead = threading.Thread(target=self.__reconnect)
                self.pthead.start()
                # self.pthead.join()

        def checkConnecting(self):
            # assert not self.running, 'MONGO DB has be not connected yet'
            return self.running

        def useTable(self, tableName):
            if self.checkConnecting():
                self.db = self.client[tableName]
                # if db.authenticate(DB_USER, DB_PASS, source=DB_SOURCE):
                    # authenticated, do ...
                # else:
                    # not authenticated, not connected, do something else
                return self

        def objects(self, collection):
            if self.checkConnecting():
                return self.db[collection]

        # def find

    __instance = None