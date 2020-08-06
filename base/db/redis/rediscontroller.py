#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import os
import logging
import threading
import json
import redis
logger = logging.getLogger('django')


class RedisController:
    def __new__(cls):
        if not RedisController.__instance:
            RedisController.__instance = RedisController.__RedisController()
        return RedisController.__instance
    def __getattr__(self, value):
        return getattr(self.__instance, value)
    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)

    class __RedisController:
        pool = None
        client = None
        db = None
        running = False
        def __init__(self):
            pass

        def __reconnect(self):
            self.config = {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', 6379)),
                'db': int(os.getenv('REDIS_DB', 0)),
                # 'password': int(os.getenv('REDIS_PASSWORD', '')),
                # 'ssl': True,
                # 'ssl_ca_certs' = 'LOCAL/PATH/TO/rackspace-ca-2016.pem'),
                # 'maxPoolSize': None,
            }
            try:
                while self.client is None:
                    try:
                        logger.info('Redis is trying connect ...')
                        logger.debug('config: {}'.format(json.dumps(self.config),))
                        # if self.pool is None:
                        #     self.pool = redis.ConnectionPool(**self.config)
                        # self.client = redis.Redis(connection_pool=self.pool)
                        self.client = redis.StrictRedis(**self.config)
                        self.client.ping()
                    except Exception as ex:
                        logger.warning('Redis is connected failed')
                    if self.client is not None:
                        break
                    time.sleep(2)
                self.running = True

            except Exception as ex:
                print(str(ex))
                self.running = False

            finally:
                if self.running == False:
                    logger.info('Redis is connected failed')
                else:
                    logger.info('Redis connected successfull')

        def close(self):
            pass

        def start(self):
            if not self.running:
                self.__reconnect()

        def checkConnecting(self):
            return self.running

        def exists(self, key):
            return self.client.exists(key)

        def set(self, key, val):
            return  self.client.set(key, json.dumps(val))

        def get(self, key):
            val = self.client.get(key)
            try:
                return json.loads(val)
            except Exception as ex:
                logger.error(str(ex))
                return None

        def delete(self, key):
            return self.client.delete(key)

        def notify(self, payload):
            channel = os.getenv('REDIS_NOTIFY_CHANNEL', 'NODE_NOTIFY')
            self.client.publish(channel, payload)

        def notify_to_user(self, user, type, data):
            channel = os.getenv('REDIS_NOTIFY_CHANNEL', 'NODE_NOTIFY')
            payload = {
                'groups': ['USER_ROOM_{}'.format(user.id)],
                'type': type,
                'data': data
            }
            self.client.publish(channel, json.dumps(payload))

    __instance = None