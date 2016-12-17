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

running = True;
noYouget = 1;

def resolveUrl(nRoom):
      with urlopen(sAPI3 + str(nRoom)) as res:
          bData = res.read();
      sUrl = re.search(rb'<url><!\[CDATA\[(.+)\]\]><\/url>', bData).group  (1).decode('utf-8');
      return sUrl;

def downStream(sUrl, sFile):
      with open(sFile, 'wb') as f:
          with urlopen(sUrl, timeout=5) as res:
              print('    starting download from:\n{}\n    to:\n{}'
                      .format(sUrl, sFile));
              nSize = 0;
              bBuffer = res.read(1024 * 256);
              while bBuffer:
                  f.write(bBuffer);
                  nSize += len(bBuffer);
                  sys.stdout.write('\r{:<4} MB downloaded'.format(nSize/1024/  1024));
                  sys.stdout.flush();
                  bBuffer = res.read(1024 * 256);

def display(*args, **kargs):
    try:
        print(*args, **kargs);
    except UnicodeEncodeError as e:
        args = (str(x).encode('gbk', 'replace').decode('gbk') for x in args);
        print(*args, **kargs);

def getRoom(nRoom):
    def fetchRealRoom(nRoom):
        try:
            f1 = urllib.request.urlopen('http://live.bilibili.com/'+ str(nRoom));
            bData = f1.read(5000);
            nRoom = int(re.search(b'var ROOMID = (\\d+)?;', bData).group(1));
            return nRoom
        finally:
            if ('f1' in locals()): f1.close();
    try:
        f1 = urllib.request.urlopen(sAPI1 + str(nRoom));
        bRoomInfo = f1.read();
        sRoomInfo = bRoomInfo.decode('utf-8');
        sServer = re.search('<server>(.*?)</server>', sRoomInfo).group(1);
    except socket.timeout as e:
        display('获取弹幕服务器时连接超时',
                '尝试使用默认弹幕服务器地址',
                sep='\n');
        sServer = 'livecmt-1.bilibili.com';
    except urllib.error.HTTPError as e:
        if ('f1' in locals()): f1.close();
        if (e.code != 404):
            raise;
        nRoom = fetchRealRoom(nRoom);
        f1 = urllib.request.urlopen(sAPI1 + str(nRoom));
        bRoomInfo = f1.read();
        sRoomInfo = bRoomInfo.decode('utf-8');
        sServer = re.search('<server>(.*?)</server>', sRoomInfo).group(1);
    finally:
        if ('f1' in locals()): f1.close();
    if (not sServer):
        raise Exception('Error: wrong server: '+repr(sServer)); 
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
        display('播主：{}\n房间：{}\n状态：{}'.format(sHoster, sTitle, sStatus))
    except Exception as e:
        display('获取房间信息失败');
        raise;
        display(bRoomInfo);
    finally:
        if ('f1' in locals()): f1.close();
    return sServer, nRoom, (sHoster, sTitle, sStatus);

def monitor(nRoom, wait):
    global args;
    global running;
    global noYouget;
    sServer, nRoom, aInfo = getRoom(nRoom);

    while (running):
        with urlopen(sAPI2 + str(nRoom)) as f:
            bData = f.read();
        mData = json.loads(bData.decode());
        sStatus = mData['data']['_status'];
        display(time.ctime(), end=' ');
        if (sStatus == 'on'):
            print(sStatus);
            sCom = 'you-get ';
            if (args.verbose):
                sCom += ' -d';
            if (args.down):
                sName = aInfo[0] + '-' + aInfo[1];
                sName = re.sub(r'[^\w_\-.()]', '-', sName);
                while sStatus == 'on':
                    sTime = time.strftime('%m%d_%H%M%S-');
                    sOpt = ' -O "{}{}.flv" http://live.bilibili.com/{}'.format(sTime, sName, nRoom);
                    if(noYouget):
                        sUrl = resolveUrl(nRoom);
                        downStream(sUrl, '{}{}.flv'.format(sTime, sName));
                    else:
                        print(sCom + sOpt);
                        os.system(sCom + sOpt);
                    wait(1);
                    with urlopen(sAPI2 + str(nRoom)) as f:
                        bData = f.read();
                    mData = json.loads(bData.decode());
                    sStatus = mData['data']['_status'];
            else:
                sOpt = ' -p mpv http://live.bilibili.com/{}'.format(nRoom);
                while sStatus == 'on':
                    if(noYouget):
                        sUrl = resolveUrl(nRoom);
                        print('mpv ' + sUrl);
                        subprocess.run(['mpv', sUrl]);
                        print('mpv exited.');
                    else:
                        print(sCom + sOpt);
                        os.system(sCom + sOpt);
                    wait(1);
                    with urlopen(sAPI2 + str(nRoom)) as f:
                        bData = f.read();
                    mData = json.loads(bData.decode());
                    sStatus = mData['data']['_status'];
        else:
            print('live off');
        display(time.ctime(), end=' ');
        print('end');
        wait(30);
        #time.sleep(30);

def main():
    global args;
    global running;
    global noYouget;
    parser1 = argparse.ArgumentParser(description='use you-get to monitor and download bilibili live');
    group1 = parser1.add_mutually_exclusive_group()
    group1.add_argument('-r', '--room', type=int, help='the room ID');
    group1.add_argument('-u', '--uid', type=int, help='the user id of the room hoster');
    group2 = parser1.add_mutually_exclusive_group()
    group2.add_argument('-d', '--down', action='store_true', help='use you-get to download live stream');
    group2.add_argument('-p', '--play', action='store_true', help='use combination of you-get and mpv to play live stream');
    parser1.add_argument('-v', '--verbose', action='store_true', help='show you-get debug info');
    args = parser1.parse_args();
    #noYouget = subprocess.run('you-get --version', shell=1).returncode;
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
    if (not nRoom):
        nRoom = int(input('room ID:'));
    if (sys.platform == 'win32'):
        wait = time.sleep;
    else:
        wait = threading.Event().wait;
    while running:
        try:
            monitor(nRoom, wait);
        except (http.client.HTTPException, urllib.error.URLError, ConnectionError, json.JSONDecodeError) as e:
            if (isinstance(e, urllib.error.HTTPError) and e.code == 404):
                display('房间不存在');
                running = False;
            else:
                display('网络错误', e,'程序将在十秒后重启', sep='\n');
                wait(10);
                #time.sleep(10);
                continue;

if __name__ == '__main__':
    try:
        main();
    except KeyboardInterrupt as e:
        running = False;
        print('exiting...');
