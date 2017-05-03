#! /usr/bin/env python3
# -*- coding: UTF-8 -*-
import os
import sys
import urllib.request
import urllib.error
from urllib.request import urlopen
import http.client
import json
import time
import re
import socket
import argparse
import threading
import subprocess

sAPI0 = 'http://space.bilibili.com/ajax/live/getLive?mid='
sAPI1 = 'http://live.bilibili.com/api/player?id=cid:';
sAPI2 = 'http://live.bilibili.com/live/getInfo?roomid=';
sAPI3 = 'http://live.bilibili.com/api/playurl?cid=';

DOWNLOAD = False;
COMMAND = '';

running = True;

def resolveUrl(nRoom):
    with urlopen(sAPI3 + str(nRoom)) as res:
        bData = res.read();
    sUrl = re.search(rb'<url><!\[CDATA\[(.+)\]\]><\/url>', bData).group(1).decode('utf-8');
    return sUrl;

def downStream(sUrl, sFile):
    try:
        res = urlopen(sUrl, timeout=10);
        f = open(sFile, 'wb');
        display('    starting download from:\n{}\n    to:\n{}'
                .format(sUrl, sFile));
        nSize = 0;
        bBuffer = res.read(1024 * 256);
        while bBuffer:
            f.write(bBuffer);
            nSize += len(bBuffer);
            sys.stdout.write('\r{:<4.2f} MB downloaded'.format(nSize/1024/  1024));
            sys.stdout.flush();
            bBuffer = res.read(1024 * 256);
    finally:
        if ('res' in locals()): res.close();
        if ('f' in locals()): f.close();
        if (os.path.isfile(sFile) and os.path.getsize(sFile) == 0):
            os.remove(sFile);

def display(*args, **kargs):
    try:
        print(*args, **kargs);
    except UnicodeEncodeError as e:
        args = (str(x).encode('gbk', 'replace').decode('gbk') for x in args);
        print(*args, **kargs);

def getRoom(nRoom, isVerbose=True):
    def fetchRealRoom(nRoom):
        try:
            f1 = urllib.request.urlopen('http://live.bilibili.com/'+ str(nRoom));
            bData = f1.read(5000);
            nRoom = int(re.search(b'var ROOMID = (\\d+)?;', bData).group(1));
            return nRoom
        except urllib.error.HTTPError as e:
            if (e.code == 404):
                display('房间不存在');
                running = False;
                sys.exit();
            else:
                raise
        finally:
            if ('f1' in locals()): f1.close();
    try:
        f1 = urllib.request.urlopen(sAPI2 + str(nRoom));
        bRoomInfo = f1.read();
        mData = json.loads(bRoomInfo.decode('utf-8'));
        if (mData['code'] == -400):
            nRoom = fetchRealRoom(nRoom);
            f1.close();
            f1 = urllib.request.urlopen(sAPI2 + str(nRoom));
            bRoomInfo = f1.read();
            mData = json.loads(bRoomInfo.decode('utf-8'));
        sHoster = mData['data']['ANCHOR_NICK_NAME'];
        sTitle = mData['data']['ROOMTITLE'];
        sStatus = mData['data']['LIVE_STATUS'];
        _status = mData['data']['_status'];
        if (isVerbose):
            display('播主：{}\n房间：{}\n状态：{}'.format(sHoster, sTitle, sStatus))
    except Exception as e:
        display('获取房间信息失败');
        raise;
    finally:
        if ('f1' in locals()): f1.close();
    return _status, nRoom, (sHoster, sTitle, sStatus);

def monitor(nRoom, wait):
    global running;
    global DOWNLOAD;
    global COMMAND;
    _status, nRoom, aInfo = getRoom(nRoom);

    while (running):
        sStatus, nRoom, aInfo = getRoom(nRoom, False);
        sAction = 'download' if DOWNLOAD else 'run' if COMMAND else 'play';
        display(time.ctime(), end=' - ');
        display('{} {}, status {}'.format(sAction, nRoom, sStatus));
        while sStatus == 'on':
            sName = aInfo[0] + '-' + aInfo[1];
            sName = re.sub(r'[^\w_\-.()]', '-', sName);
            sTime = time.strftime('%y%m%d_%H%M%S-');
            sName = '{}{}.flv'.format(sTime, sName);
            sUrl = resolveUrl(nRoom);
            if (DOWNLOAD):
                display('    downloading room ' + str(nRoom));
                downStream(sUrl, sName);
            elif (COMMAND):
                sCom = COMMAND.format(sUrl, sName);
                display('    run command "{}"'.format(sCom));
                subprocess.run(sCom, shell=True);
            else:
                display('    playing room {}\nmpv {}'.format(nRoom, sUrl));
                subprocess.run(['mpv', sUrl]);
                display('mpv exited.');

            wait(2);
            sStatus, nRoom, aInfo = getRoom(nRoom, False);
            #if (args.down):
            #else:
            #    while sStatus == 'on':
            #        sUrl = resolveUrl(nRoom);

            #        display('    playing room {}\nmpv {}'.format(nRoom, sUrl));
            #        if (COMMAND):
            #            subprocess.run(COMMAND.format(sUrl), shell=True);
            #        else:
            #            subprocess.run(['mpv', sUrl]);
            #            display('mpv exited.');

            #        wait(2);
            #        sStatus, nRoom, aInfo = getRoom(nRoom, False);
        wait(30);

def main():
    global args;
    global running;
    global DOWNLOAD;
    global COMMAND;
    socket.setdefaulttimeout(30);
    parser1 = argparse.ArgumentParser(description='use you-get to monitor and download bilibili live');
    group1 = parser1.add_mutually_exclusive_group()
    group1.add_argument('-r', '--room', type=int, help='the room ID');
    group1.add_argument('-u', '--uid', type=int, help='the user id of the room hoster');
    group2 = parser1.add_mutually_exclusive_group()
    group2.add_argument('-d', '--down', action='store_true', help='use download live stream');
    group2.add_argument('-p', '--play', action='store_true', help='use mpv to play live stream; it is the default operation so can be omitted');
    group2.add_argument('-c', '--command',
            help='handling the resolved stream with the given COMMAND; variables will be inserted using format syntax: COMMAND.format(URL, FILE), in which URL is the resolved stream url and FILE is the file name that would be used if the -d flag instead were set; take care of quoting: "{1}" "{0}"'
    );
    parser1.add_argument('-v', '--verbose', action='store_true', help='show you-get debug info');
    args = parser1.parse_args();
    nRoom = None;
    if (args.room):
        nRoom = args.room;
    elif (args.uid):
        try:
            f1 = urllib.request.urlopen(sAPI0 + str(args.uid));
            bData = f1.read();
            sData = bData.decode('utf-8');
            mData = json.loads(sData);
            if (mData['status']):
                nRoom = int(mData['data']);
        finally:
            if ('f1' in locals()): f1.close();
    if (args.down):
        DOWNLOAD = True;
    elif (args.command):
        COMMAND = args.command;
    if (not nRoom):
        nRoom = int(input('room ID:'));
    if (sys.platform == 'win32'):
        wait = time.sleep;
    else:
        wait = threading.Event().wait;
    while running:
        try:
            monitor(nRoom, wait);
        except socket.timeout as e:
            display('\n连接超时\n');
            wait(5);
            continue;
        except (http.client.HTTPException, urllib.error.URLError, ConnectionError, TimeoutError, json.JSONDecodeError, AssertionError) as e:
            display('网络错误', e,'程序将在十秒后重启', sep='\n');
            wait(10);
            #time.sleep(10);
            continue;

if __name__ == '__main__':
    try:
        main();
    except KeyboardInterrupt as e:
        running = False;
        display('\nexiting...');
