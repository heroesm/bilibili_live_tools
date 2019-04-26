#! /usr/bin/env python3

import sys
import os
import re
import time
import socket
import urllib.request
from urllib.request import Request, urlopen
import urllib.parse
#from pprint import pprint
import http.client
import http.cookies
import http.cookiejar
import json
import logging

try:
    import readline
except ImportError:
    pass

ROOM = 0;

FILE = 'bilicookies.txt';
UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
COOKIES = '';
DOMAIN = 'https://live.bilibili.com'
LOGLEVEL = logging.INFO;
#LOGLEVEL = logging.DEBUG;

log = None;
sDir = '';
sHome = '';

def prepare():
    global LOGLEVEL;
    global log, sDir, sHome;
    sHome = os.path.expanduser('~');
    sDir = os.path.split(__name__)[0];
    if (sDir): os.chdir(sDir);
    if ('readline' in globals()):
        sInputrc = os.path.join(sHome, '.inputrc');
        if (os.path.isfile(sInputrc)):
            readline.read_init_file(sInputrc);
        sInputrc = '/etc/inputrc';
        if (os.path.isfile(sInputrc)):
            readline.read_init_file(sInputrc);
    logging.basicConfig();
    log = logging.getLogger(__name__);
    log.setLevel(LOGLEVEL);
    socket.setdefaulttimeout(30);
prepare();

class TextCookieJar(http.cookiejar.LWPCookieJar):
    def __init__(self, sCookies, sDomain, filename=None, delayload=None, policy=None):
        super().__init__(filename, delayload, policy);
        self.loadCookies(sCookies, sDomain);
    class dummyRes():
        def __init__(self, message):
            self.message = message;
        def info(self):
            return self.message;
    def loadCookies(self, sCookies, sDomain):
        cookies = http.cookies.SimpleCookie(sCookies);
        msg = http.client.HTTPMessage();
        for morsel in cookies.values():
            msg['set-cookie'] = morsel.output(header='').strip();
        res = self.dummyRes(msg);
        req = urllib.request.Request(sDomain);
        self.extract_cookies(res, req);
        log.debug('load cookies from string input: {}'.format(self));

def loadFromFile(sFile):
    try:
        file = open(sFile, 'rb');
        sData = file.read().decode();
        match = re.search(r'^(?:Cookie:)? ?(.+)$', sData);
        if (match):
            sCookies = match.group(1);
            log.debug('extracted cookies: {}'.format(sCookies));
            return sCookies;
    except Exception as e:
        print(e);
    finally:
        file.close();
    return False;

class Room():
    def __init__(self, nRoom):
        global log
        self.nRoom = int(nRoom);
        self.nId = self.nRoom;
        self.sTitle = None;
        self.sUser = None;
        self.sStatus = None;
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
            sAPI4 = 'https://api.live.bilibili.com/room/v1/Room/room_init?id={}'
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
        sApi6 = 'http://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid={}'
        if (self.sUser is None):
            try:
                f1 = urllib.request.urlopen(sApi6.format(self.nId));
                bData = f1.read();
                mData = json.loads(bData.decode());
                self.sUser = mData['data']['info']['uname'];
            except Exception as e:
                print('获取播主失败: ', e);
                self.sUser = '';
            finally:
                if ('f1' in locals()): f1.close();
    def getInfo(self):
        global log
        sApi5 = 'http://api.live.bilibili.com/room/v1/Room/get_info?room_id={}'
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

def get_cookie_value(jar, key):
    for cookie in jar:
        if cookie.name == key:
            return cookie.value

def sendMsg(sMsg, nRoom):
    global UA, COOKIES, DOMAIN, FILE;
    sApi = 'https://api.live.bilibili.com/msg/send';
    sUa = UA or 'Mozilla/5.0'
    sDomain = DOMAIN;
    sFile = FILE;
    sCookies = '';
    if (os.path.isfile(sFile)):
        sCookies = loadFromFile(sFile);
    sCookies = sCookies or COOKIES;
    jar = TextCookieJar(sCookies, sDomain);
    bili_jct = get_cookie_value(jar, 'bili_jct')
    assert bili_jct
    mData = {
            'msg': sMsg,
            'roomid': nRoom,
            'fontsize': 25,
            'rnd': int(time.time()),
            'color': '16777215',
            'mode': 1,
            'csrf': bili_jct,
            'csrf_token': bili_jct,
    }
    bData = urllib.parse.urlencode(mData, True).encode();
    req = Request(sApi, data=bData, method='POST');
    jar.add_cookie_header(req);
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));
    opener.addheaders = [
        ('User-Agent', sUa),
        ('referer', 'https://live.bilibili.com/{}'.format(nRoom)),
        ('Origin', 'https://live.bilibili.com'),
    ];
    try:
        res = opener.open(req);
    except Exception as e:
        print(e);
    else:
        sRes = res.read().decode();
        mRes = json.loads(sRes)
        #jar.save('danmucookiesLWP.txt', True, True);
        print(mRes);
        if (mRes['code'] == -101):
            print('登录信息无效或已过期，请重新将cookies存入同目录的bilicookies.txt文件中');
        return sRes;
    finally:
        res.close();

def main():
    global ROOM;
    nRoom = ROOM
    if (sys.argv[1:2]):
        nRoom = sys.argv[1];
    if (not nRoom):
        nRoom = input('room: ');
    #print('room: {}'.format(nRoom));
    room = Room(nRoom);
    room.getInfo();
    print('id: {}\nUser: {}\nroom: {}\nstatus: {}\n'.format(room.nId, room.sUser, room.sTitle, room.sStatus))
    nTime0 = time.monotonic();
    try:
        while True:
            sInput = input('> ')
            nTime1 = time.monotonic();
            nDelta = nTime1 - nTime0;
            #print(nDelta)
            if (nDelta < 1):
                time.sleep(1 - nDelta);
            sendMsg(sInput, room.nId);
            nTime0 = time.monotonic();
    except (KeyboardInterrupt, EOFError):
        print();
        sys.exit();

if __name__ == '__main__':
    main();
