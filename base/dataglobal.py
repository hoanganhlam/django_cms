#!/usr/bin/python
# -*- coding: utf8 -*-

import time
import os
import logging
import json
import datetime
import threading
import asyncio
from core.db.redis.rediscontroller import RedisController
from device.models import Device
from modules.lighting.models import LightingDevLine
from modules.accesscontrol.models import AccCardReader
logger = logging.getLogger('django')


class GlobalDeviceStatus:
    def __new__(cls):
        if not GlobalDeviceStatus.__instance:
            GlobalDeviceStatus.__instance = GlobalDeviceStatus.__GlobalDeviceStatus()
        return GlobalDeviceStatus.__instance
    def __getattr__(self, value):
        return getattr(self.__instance, value)
    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)

    class __GlobalDeviceStatus:
        _KEY = 'DEVICE_STATUS'
        _rdis = None
        _default = {
            'id': -1,
            'system': -1,
            'ip': '',
            'mac': '',
            'time': None,
            'status': False,
        }

        def __init__(self):
            self._rdis = RedisController()
            self._rdis.start()

        def updateModel(self, id, status, ip, mac):
            if id > 0 :
                qs = Device.objects.get(id=id)
                if qs:
                    qs.dev_online = status
                    qs.dev_ip = ip
                    qs.dev_mac = mac
                    qs.save()

        def delAll(self):
            self._rdis.delete(self._KEY)

        def create(self, lstData):
            self.delAll()
            self.update(lstData)

        # {'122344':
        #   {
        #       'id': 1,
        #       'system': 'LIGHTING',
        #       'ip': '192.168.8.22',
        #       'mac': '00:11:22:33:44:55',
        #       'time': '2018-09-18 18:09:00',
        #       'status': 0}
        #   }
        def getAll(self, status=None):
            lstItem = self._rdis.get(self._KEY)
            if lstItem is None:
                return {}
            lstRes = {}
            if status is not None:
                for key, val in lstItem.items():
                    if val['status'] == status:
                        lstRes[key] = val
                return lstRes
            else:
                return lstItem

        def detectStatusOffline(self):
            # get all device online
            lstDeviceOn = self.getAll(status=True)
            timeNow = datetime.datetime.now()
            for key, val in lstDeviceOn.items():
                time = datetime.datetime.strptime(val['time'], '%Y-%m-%d %H:%M:%S')
                timediff = timeNow - time
                seconds = timediff.total_seconds()
                if int(seconds) > 5:
                    val['status'] = False
                    # send update status of device
                    self.updateModel(
                        id = val['id'],
                        status = val['status'],
                        mac = val['mac'],
                        ip = val['ip']
                    )
            self.update(lstDeviceOn)

        def detectStatusChange(self, lstNewItemStatus):
            lstItem = self.getAll()
            for key, val in lstNewItemStatus.items():
                if key in lstItem:
                    if val['ip'] != lstItem[key]['ip'] \
                            or val['mac'] != lstItem[key]['mac'] \
                            or val['status'] != lstItem[key]['status']:
                        # update device
                        self.updateModel(
                            id=val['id'],
                            status=val['status'],
                            mac=val['mac'],
                            ip=val['ip']
                        )

        # params : {'122344': {'ip': '192.168.8.22', 'mac': '00:11:22:33:44:55', 'status': 1}, ...}
        def update(self, lstData):
            lstItem = self.getAll()
            for key, val in lstData.items():
                if str(key) in lstItem:
                    lstItem[str(key)] = {**lstItem[str(key)], **val}
                else:
                    val['time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    lstItem[str(key)] = val

            # self.detectStatusChange(lstItem)
            return self._rdis.set(self._KEY, lstItem)

        def updateRealtime(self, lstData):
            lstItem = self.getAll()
            for key, val in lstData.items():
                val['time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if str(key) in lstItem:
                    lstItem[str(key)] = {**lstItem[str(key)], **val}

            self.detectStatusChange(lstItem)
            return self._rdis.set(self._KEY, lstItem)

        def getElement(self, ident):
            lstItem = self.getAll()
            return lstItem[ident]

        def delElement(self, ident):
            lstItem = self.getAll()
            if ident in lstItem:
                del lstItem[ident]
            self.create(lstItem)

    __instance = None


class GlobalLightingLineStatus:
    def __new__(cls):
        if not GlobalLightingLineStatus.__instance:
            GlobalLightingLineStatus.__instance = GlobalLightingLineStatus.__GlobalLightingLineStatus()
        return GlobalLightingLineStatus.__instance
    def __getattr__(self, value):
        return getattr(self.__instance, value)
    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)

    # {'123454222': {'system': 'LIGHTING', 'lines': [
    #   {'id': 1, 'ident': 123, 'status': False, 'lighting': 1, error: False}
    # ], 'time': '2018-09-18 18:09:00'}}
    class __GlobalLightingLineStatus:
        _KEY = 'LIGHTING_LINE_STATUS'
        _rdis = None
        _default = {
            'id': -1,
            'system': -1,
            'lines': []
        }
        _linedefault = {
            'id': -1,
            'status': False,
            'error': False,
            'lighting': -1,
            'time': None,
        }

        def __init__(self):
            self._rdis = RedisController()
            self._rdis.start()

        def updateModel(self, devId, LightinglineId, status, error):
            ins = LightingDevLine.objects.get(id=LightinglineId)
            if ins:
                ins.ldl_state = status
                ins.ldl_error = error
                ins.save()
                try:
                    zone = ins.ldl_zone
                    zone.lsz_state = status
                    zone.save()
                except Exception as ex:
                    logger.error(str(ex))

        def delAll(self):
            self._rdis.delete(self._KEY)

        def create(self, lstData):
            self.delAll()
            self.update(lstData)

        def getAll(self):
            lstItem = self._rdis.get(self._KEY)
            if lstItem is None:
                return {}
            return lstItem

        def detectStatusChange(self, lstNewItemStatus):
            lstItem = self.getAll()
            for key, val in lstNewItemStatus.items():
                if key in lstItem and 'lines' in val:
                    for lineIdent, lineVal in val['lines'].items():
                        if lineIdent in lstItem[key]['lines'] \
                                and lineVal['status'] != lstItem[key]['lines'][str(lineIdent)]['status']:
                            # update database
                            logger.info('update status of the line have changed to database')
                            self.updateModel(key, lineVal['lighting'], lineVal['status'], lineVal['error'])

        # {'123454222': {'lines': {'1': 0, '2': 1...}}}
        def update(self, lstData):
            lstItem = self.getAll()
            timeNow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for key, val in lstData.items():
                if 'lines' in val:
                    if str(key) in lstItem:
                        for lineIdent, lineVal in val['lines'].items():
                            if str(lineIdent) in lstItem[str(key)]['lines']:
                                lstItem[str(key)]['lines'][str(lineIdent)] = {**lstItem[str(key)]['lines'][str(lineIdent)], **lineVal}
                            else:
                                lstItem[str(key)]['lines'][str(lineIdent)] = {**self._linedefault, **lineVal}
                    else:
                        for lineIdent, lineVal in val['lines'].items():
                            lineVal['time'] = timeNow
                        lstItem[str(key)] = val
            return self._rdis.set(self._KEY, lstItem)

        def updateRealtime(self, lstData):
            lstItem = self.getAll()
            timeNow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for key, val in lstData.items():
                if 'lines' in val:
                    if str(key) in lstItem:
                        for lineIdent, lineVal in val['lines'].items():
                            lineVal['time'] = timeNow
                            if str(lineIdent) in lstItem[str(key)]['lines']:
                                lstItem[str(key)]['lines'][str(lineIdent)] = {**lstItem[str(key)]['lines'][str(lineIdent)], **lineVal}
            self.detectStatusChange(lstItem)
            return self._rdis.set(self._KEY, lstItem)

        def getElement(self, ident):
            lstItem = self.getAll()
            return lstItem[ident]

        # {'12344455':
        #   {
        #       'lines': ['1', '2', ...]
        #   }
        # }
        def delElement(self, data):
            lstItem = self.getAll()
            for key, val in lstItem.items():
                if key not in data:
                    return False
                else:
                    for lineIdent in data[str(key)]['lines']:
                        if str(lineIdent) in val['lines']:
                            del val['lines'][str(lineIdent)]
            self.create(lstItem)

        # {'12344455', '12233445'}
        def delAllOfDev(self, idents):
            lstItem = self.getAll()
            for ident in idents:
                del lstItem[ident]
            self.create(lstItem)
    __instance = None


class GlobalACCDoorStatus:
    def __new__(cls):
        if not GlobalACCDoorStatus.__instance:
            GlobalACCDoorStatus.__instance = GlobalACCDoorStatus.__GlobalACCDoorStatus()
        return GlobalACCDoorStatus.__instance
    def __getattr__(self, value):
        return getattr(self.__instance, value)
    def __setattr__(self, key, value):
        return setattr(self.__instance, key, value)

    # {'123454222': {'system': 'ACC', 'lines': [
    #   {'id': 1, 'ident': 123, 'status': False, 'cardreader': 1, 'time': '2018-09-18 18:09:00'}
    # ], 'time': '2018-09-18 18:09:00'}}
    class __GlobalACCDoorStatus:
        _KEY = 'ACC_DOOR_STATUS'
        _rdis = None
        _default = {
            'id': -1,
            'system': -1,
            'lines': []
        }
        _linedefault = {
            'id': -1,
            'status': False,
            'cardreader': -1,
            'time': None,
        }

        def __init__(self):
            self._rdis = RedisController()
            self._rdis.start()

        def updateModel(self, devId, cardReaderId, status):
            ins = AccCardReader.objects.get(id=cardReaderId)
            if ins:
                ins.acccr_state = status
                ins.save()
                try:
                    door = ins.acccr_door
                    door.door_state = status
                    door.save()
                except Exception as ex:
                    logger.error(str(ex))

        def delAll(self):
            self._rdis.delete(self._KEY)

        def create(self, lstData):
            self.delAll()
            self.update(lstData)

        def getAll(self):
            lstItem = self._rdis.get(self._KEY)
            if lstItem is None:
                return {}
            return lstItem

        def detectStatusChange(self, lstNewItemStatus):
            lstItem = self.getAll()
            for key, val in lstNewItemStatus.items():
                if key in lstItem and 'lines' in val:
                    for lineIdent, lineVal in val['lines'].items():
                        if lineIdent in lstItem[key]['lines'] \
                                and lineVal['status'] != lstItem[key]['lines'][str(lineIdent)]['status']:
                            # update database
                            logger.info('update status of the line have changed to database')
                            self.updateModel(key, lineVal['cardreader'], lineVal['status'])

        # {'123454222': {'lines': {'1': 0, '2': 1...}}}
        def update(self, lstData):
            lstItem = self.getAll()
            timeNow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for key, val in lstData.items():
                if 'lines' in val:
                    if str(key) in lstItem:
                        for lineIdent, lineVal in val['lines'].items():
                            if str(lineIdent) in lstItem[str(key)]['lines']:
                                lstItem[str(key)]['lines'][str(lineIdent)] = {
                                **lstItem[str(key)]['lines'][str(lineIdent)], **lineVal}
                            else:
                                lstItem[str(key)]['lines'][str(lineIdent)] = {**self._linedefault, **lineVal}
                    else:
                        for lineIdent, lineVal in val['lines'].items():
                            lineVal['time'] = timeNow
                        lstItem[str(key)] = val
            return self._rdis.set(self._KEY, lstItem)

        def updateRealtime(self, lstData):
            lstItem = self.getAll()
            timeNow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for key, val in lstData.items():
                if 'lines' in val:
                    if str(key) in lstItem:
                        for lineIdent, lineVal in val['lines'].items():
                            lineVal['time'] = timeNow
                            if str(lineIdent) in lstItem[str(key)]['lines']:
                                lstItem[str(key)]['lines'][str(lineIdent)] = {
                                **lstItem[str(key)]['lines'][str(lineIdent)], **lineVal}
            self.detectStatusChange(lstItem)
            return self._rdis.set(self._KEY, lstItem)

        def getElement(self, ident):
            lstItem = self.getAll()
            return lstItem[ident]

        # {'12344455':
        #   {
        #       'lines': ['1', '2', ...]
        #   }
        # }
        def delElement(self, data):
            lstItem = self.getAll()
            for key, val in lstItem.items():
                if key not in data:
                    return False
                else:
                    for lineIdent in data[str(key)]['lines']:
                        if str(lineIdent) in val['lines']:
                            del val['lines'][str(lineIdent)]
            self.create(lstItem)

        # {'12344455', '12233445'}
        def delAllOfDev(self, idents):
            lstItem = self.getAll()
            for ident in idents:
                del lstItem[ident]
            self.create(lstItem)

    __instance = None
