#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

import os, sys
from os.path import split, join, exists, abspath, isdir, expanduser
import re
import logging
import json
import threading
import urllib.request
import urllib.error
from urllib.request import urlopen#, Request
import time
import io
import socket
import subprocess
import argparse

ROOMS = '';
USERS = '';
FILEDIR = '';
DEBUGLEVEL = logging.DEBUG;
SCRIPT = '';
COMMAND = '';
INTERVAL = 20;

sApi0 = 'http://space.bilibili.com/ajax/live/getLive?mid={}'
sApi1 = 'http://live.bilibili.com/api/player?id=cid:{}';
sApi2 = 'http://live.bilibili.com/live/getInfo?roomid={}';  # obsolete
sApi3 = 'http://live.bilibili.com/api/playurl?cid={}';
sAPI4 = 'https://api.live.bilibili.com/room/v1/Room/room_init?id={}'
sApi5 = 'http://api.live.bilibili.com/room/v1/Room/get_info?room_id={}'
sApi6 = 'http://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid={}'

aRooms = [];
sHome = '';
sSelfDir = '';
sLogDir = '';
log = None;
sleepEvent = None;
wait = None;

def prepare():
    global sHome
    global sSelfDir
    global sLogDir
    global log
    global sleepEvent
    global wait
    sHome = expanduser('~')
    sSelfDir = split(__file__)[0];
    sLogDir = join(sSelfDir, 'multilisten.log.d');
    logging.basicConfig(format='    %(asctime)s %(levelname)-5s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S');
    log = logging.getLogger(__name__);
    log.setLevel(DEBUGLEVEL);
    sleepEvent = threading.Event();
    wait = sleepEvent.wait;
    opener = urllib.request.build_opener();
    opener.addheaders = [('User-agent', 'Mozilla/5.0')];
    urllib.request.install_opener(opener);
    socket.setdefaulttimeout(30);
prepare();

def display(*args, **kargs):
    try:
        print(*args, **kargs);
    except UnicodeEncodeError as e:
        sEnc = sys.stdout.encoding;
        args = (str(x).encode(sEnc, 'replace').decode(sEnc) for x in args);
        print(*args, **kargs);

class Room():
    def __init__(self, nRoom=None, nUser=None):
        global log
        self.nRoom = int(nRoom or 0);
        self.nUser= int(nUser or 0);
        self.nId = self.nRoom;
        self.sUrl = None;
        self.sTitle = None;
        self.sUser = None;
        self.sStatus = None;
        self._stream = io.StringIO();
        self.thread = None;
        #log.debug({key: value for key, value in vars(self).items() if not key.startswith('_') and value});
    def getRoomByUser(self):
        assert self.nUser;
        try:
            res = urlopen(sApi0.format(self.nUser));
            sData = res.read().decode('utf-8');
            assert sData;
            mData = json.loads(sData);
            if (mData['status']):
                self.nId = self.nRoom = int(mData['data']);
                return True;
            else:
                display('不存在的播主: ', self.nUser);
                return False;
        finally:
            if ('res' in locals()): res.close();
    def getRealId(self):
        global log
        try:
            #sUrl = 'http://live.bilibili.com/{}'.format(self.nRoom);
            #res = urlopen(sUrl);
            #bData = res.read(5000);
            #match = re.search(rb'var ROOMID = (\d+);', bData);
            #if (match):
            #    nId = int(match.group(1));
            #else:
            #    nId = self.nRoom;
            res = urlopen(sAPI4.format(self.nRoom));
            bData = res.read();
            mData = json.loads(bData.decode());
            nId = mData['data']['room_id'];
        except urllib.error.HTTPError as e:
            if (e.code == 404):
                log.error('room {} not exists'.format(self.nRoom));
                return False
            else:
                raise
        else:
            self.nId = nId;
            return True
        finally:
            if ('res' in locals()): res.close();
    def getHost(self):
        if (self.sUser is None):
            try:
                f1 = urllib.request.urlopen(sApi6.format(self.nId));
                bData = f1.read();
                mData = json.loads(bData.decode());
                self.sUser = mData['data']['info']['uname'];
            except Exception as e:
                display('获取播主失败: ', e);
                self.sUser = '';
            finally:
                if ('f1' in locals()): f1.close();
    def getInfo(self):
        global log
        global sApi5, sApi6
        try:
            self.getRealId();
            res = urlopen(sApi5.format(self.nId));
            sRoomInfo = res.read().decode('utf-8');
            mData = json.loads(sRoomInfo);
            self.getHost();
            self.sTitle = sTitle = mData['data']['title'];
            nStatus = mData['data']['live_status'];
            _status = 'on' if nStatus == 1 else 'off';
            self.sStatus = _status;
        except Exception as e:
            log.error('failed to get room info: {}'.format(e));
            #raise;
        else:
            return _status;
        finally:
            if ('res' in locals()): res.close();
    def getStream(self):
        global sApi3
        with urlopen(sApi3.format(self.nId)) as res:
            sData = res.read().decode('utf-8');
        iMatches = re.finditer(r'<(?:b\d)?url><!\[CDATA\[(.+)\]\]><\/(?:b\d)?url>', sData);
        aMatches = list(iMatches);
        if (aMatches):
            self.aUrls = [x.group(1) for x in aMatches];
            sUrl = self.sUrl = self.aUrls[0];
            return sUrl;
        else:
            return False;
    def download(self, sPath, stream=sys.stdout, nVerbose=1):
        global log
        def adaptName(sPath):
            if (os.path.exists(sPath)):
                sName, sExt = os.path.splitext(sPath)
                i = 1;
                sOutPath = '{}{}{}'.format(sName, i, sExt);
                while os.path.exists(sOutPath):
                    i += 1;
                    sOutPath = '{}{}{}'.format(sName, i, sExt);
            else:
                sOutPath = sPath;
            return sOutPath;
        assert self.sUrl or self.aUrls;
        sUrl = self.sUrl;
        sPath = adaptName(sPath);
        #iUrls = iter(aUrls);
        #sUrl = next(iUrls);
        try:
            f1 = open(sPath, 'wb');
            res = urlopen(sUrl, timeout=20);
            log.info('{} starting download from:\n{}\n    to:\n{}'.format(self.nId, sUrl, sPath));
            if (nVerbose):
                stream.write('\n');
            nSize = 0;
            n = 1024*1024;
            bBuffer = res.read(1024 * 128);
            while bBuffer:
                nSize += f1.write(bBuffer);
                if (nVerbose):
                    stream.write('\r{:<4.2f} MB downloaded'.format(nSize/n));
                bBuffer = res.read(1024 * 128);
            if (nVerbose):
                stream.write('\n');
        except socket.timeout as e:
            log.warning('{} donwloading timeout'.format(self.nId));
        except ConnectionResetError as e:
            log.warning('downloading reset: {}'.format(e));
        finally:
            if ('res' in locals()): res.close();
            if ('f1' in locals()): f1.close();
            if (os.path.isfile(sPath) and os.path.getsize(sPath) == 0):
                os.remove(sPath);
                return False;
        return True;

def doCleanup(room, sPath, sScript=None, sCom=None, sLogFile=None):
    # execute external script
    # maybe in a new thread
    global COMMAND, SCRIPT
    global log
    global sSelfDir
    global sLogDir
    sScript = (sScript or SCRIPT or '').strip();
    sCom = (sCom or COMMAND or '').strip();
    sLogFile = '{}.log'.format(room.nId);
    if (sLogDir):
        if (not exists(sLogDir)):
            os.mkdir(sLogDir);
        if (isdir(sLogDir)):
            sLogFile = join(sLogDir, sLogFile);
        else:
            sLogFile = os.devnull;
    else:
        sLogFile = os.devnull;
    try:
        file = open(sLogFile, 'a');
        if (sScript):
            sScriptOri = sScript;
            if (not exists(sScript)):
                sScript = join(sSelfDir, sScriptOri);
            sScript = abspath(sScript);
            try:
                subprocess.Popen(
                        [sys.executable, sScript, sPath],
                        stdout=file,
                        stderr=subprocess.STDOUT
                );
            except FileNotFoundError as e:
                log.error('executing script {} failed: {}'.format(sScript, e));
            else:
                log.info(r'executing cleanup script "{}" with file "{}", logging to "{}"'
                        .format(sScript, sPath, sLogFile)
                );
        if (sCom):
            sCom = sCom.format(sPath);
            try:
                subprocess.Popen(
                        sCom,
                        stdout=file,
                        stderr=subprocess.STDOUT,
                        shell=True
                );
            except FileNotFoundError as e:
                log.error('executing command {} failed: {}'.format(sCom, e));
            else:
                log.info(r'execute cleanup command "{}", logging to "{}"'
                        .format(sCom, sLogFile)
                );
    finally:
        if ('file' in locals()): file.close();
    return True;

def doDownload(room):
    global FILEDIR, sHome;
    global wait;
    global sLogDir;
    sDir = expanduser(FILEDIR) or sHome;
    while (room.getInfo() == 'on'):
        sTime = time.strftime('%y%m%d_%H%M%S');
        sName = '{}-{}-{}.flv'.format(sTime, room.sUser, room.sTitle);
        sName = re.sub(r'[^\w_\-.()]', '_', sName);
        if (not exists(sDir)):
            os.mkdir(sDir);
        assert isdir(sDir);
        sPath = os.path.join(sDir, sName);
        isSuccess = room.getStream();
        if (isSuccess):
            isSuccess = room.download(sPath, room._stream, 1)
            if (isSuccess):
                log.info('{} downloaded to {}'.format(room.nId, sPath));
                try:
                    doCleanup(room, sPath);
                except Exception as e:
                    if (sLogDir):
                        if (not exists(sLogDir)):
                            os.mkdir(sLogDir);
                        if (isdir(sLogDir)):
                            sLogFile = 'threaderror.log'
                            sLogFile = join(sLogDir, sLogFile);
                            with open(sLogFile, 'a') as file:
                                file.write('\n{}:\n  {}\n'.format(time.ctime(), e));
                            log.error('error "{}" is logged to file "{}"'
                                    .format(e, sLogFile)
                            );
                    raise
        wait(2);
    room._stream.seek(0);
    room._stream.truncate();
    log.info('{} download thread ended'.format(room.nId));
    return True;

def synMonitor(aIds=None, aUsers=None):
    global log
    global wait
    global aRooms;
    global INTERVAL;
    if (not aIds): aIds = [];
    if (not aUsers): aUsers = [];
    aRooms = [];
    for sId in aIds:
        sId = sId.strip();
        if (sId):
            room = Room(int(sId));
            room.getInfo();
            aRooms.append(room);
    for sUser in aUsers:
        sUser = sUser.strip();
        if (sUser):
            room = Room(None, int(sUser));
            if (room.getRoomByUser()):
                room.getInfo();
                aRooms.append(room);
    for room in aRooms:
        display('id: {}\nUser: {}\nroom: {}\nstatus: {}\n'.format(room.nId, room.sUser, room.sTitle, room.sStatus))
    log.debug('check interval: {}s'.format(INTERVAL));
    while True:
        for room in aRooms:
            isOn = (room.getInfo() == 'on');
            log.debug('{} {} {}'.format(room.nId, room.sUser, room.sStatus));
            if (isOn):
                if (room.thread and room.thread.is_alive()):
                    sProcess = room._stream.getvalue();
                    log.debug('{} downloading process: {}'.format(room.nId, sProcess));
                else:
                    log.info('{} starting download process...'.format(room.nId));
                    downThread = threading.Thread(
                            target=doDownload,
                            name=str(room.nId),
                            args=(room,),
                            daemon=True
                    );
                    room.thread = downThread;
                    downThread.start();
            else:
                pass
        wait(INTERVAL);

def run():
    global ROOMS
    global USERS
    sIds = ROOMS or '';
    aIds = sIds.split(',');
    sUsers = USERS or '';
    aUsers = sUsers.split(',');
    synMonitor(aIds, aUsers);

def parseArg():
    global ROOMS, USERS, FILEDIR, DEBUGLEVEL, SCRIPT, COMMAND, INTERVAL
    global log
    parser = argparse.ArgumentParser(description='simultaneously monitor status of plural rooms at live.bilibili.com, and download streaming ones');
    parser.add_argument('-r', '--room',
            help='IDs of rooms to listen, separated by comma'
    );
    parser.add_argument('-u', '--user',
            help='IDs of users who host the rooms to listen, separated by comma'
    );
    parser.add_argument('-d', '--dir',
            help='directory to be downloaded into'
    );
    parser.add_argument('-v', '--verbose',
            action='store_true',
            help='show verbose debug information'
    );
    parser.add_argument('-s', '--script',
            help='python scripts to be executed after a successful download; the downloaded file path will be passed as the first script argument ( sys.argv[1] )'
    );
    parser.add_argument('-c', '--command',
            help='the command to be executed after a successful download; the downloaded file path will replace "{0}" within the command, using format syntax ( COMMAND.format(FILEPATH) )'
    );
    parser.add_argument('-i', '--interval',
            type=int,
            help='the interval, in seconds, between each status poll round'
    );
    args = parser.parse_args();
    ROOMS = '{},{}'.format(ROOMS or '', args.room or '');
    USERS = '{},{}'.format(USERS or '', args.user or '');
    FILEDIR = args.dir or FILEDIR or '';
    if (args.verbose):
        DEBUGLEVEL = logging.DEBUG;
    else:
        DEBUGLEVEL = logging.INFO;
    log.setLevel(DEBUGLEVEL);
    SCRIPT = args.script or SCRIPT or '';
    COMMAND = args.command or COMMAND or '';
    INTERVAL = args.interval or INTERVAL or 20;
    log.debug('passed command line arguments: {}'.format(
        {key: value for (key, value) in vars(args).items() if value is not None}
    ));
    return True;

def main():
    try:
        parseArg();
        run();
    except KeyboardInterrupt as e:
        display('\nexiting...');

if __name__ == '__main__':
    main();
