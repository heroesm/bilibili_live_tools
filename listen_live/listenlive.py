#! /usr/bin/env python3
import os
import urllib.request
from urllib.request import urlopen
import json
import time
import re
import socket
import argparse

sAPI0 = 'http://space.bilibili.com/ajax/live/getLive?mid='
sAPI1 = 'http://live.bilibili.com/api/player?id=cid:';
sAPI2 = 'http://live.bilibili.com/live/getInfo?roomid=';


running = True;

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
            f1.close();
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
        f1.close();
    return sServer, nRoom, (sHoster, sTitle, sStatus);

def monitor(nRoom):
    global args;
    global running;
    sServer, nRoom, aInfo = getRoom(nRoom);

    while (running):
        with urlopen('http://live.bilibili.com/live/getInfo?roomid=' + str(nRoom)) as f:
            bData = f.read();
            mData = json.loads(bData.decode());
            sStatus = mData['data']['_status'];
            display(time.ctime(), end=' ');
            if (sStatus == 'on'):
                print(sStatus);
                sCom = 'you-get ';
                if (args.verbose):
                    sCom += '-d ';
                if (args.down):
                    sTime = time.strftime('%m%d_%H%M%S-');
                    sName = aInfo[0] + '-' + aInfo[1];
                    sName = re.sub(r'[^\w_\-.()]', '-', sName);
                    sCom += '-O "{}{}.flv" '.format(sTime, sName);
                    sCom += 'http://live.bilibili.com/' + str(nRoom);
                    print(sCom);
                    os.system(sCom);
                else:
                    sCom += '-p mpv http://live.bilibili.com/' + str(nRoom);
                    print(sCom);
                    os.system(sCom);
            else:
                print('live off');
            display(time.ctime(), end=' ');
            print('end');
        time.sleep(30);

def main():
    global args;
    global running;
    parser1 = argparse.ArgumentParser(description='use you-get to monitor and download bilibili live');
    group1 = parser1.add_mutually_exclusive_group()
    group1.add_argument('-r', '--room', type=int, help='the room ID');
    group1.add_argument('-u', '--uid', type=int, help='the user id of the room hoster');
    group2 = parser1.add_mutually_exclusive_group()
    group2.add_argument('-d', '--down', action='store_true', help='use you-get to download live stream');
    group2.add_argument('-p', '--play', action='store_true', help='use combination of you-get and mpv to play live stream');
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
    if (not nRoom):
        nRoom = int(input('room ID:'));
    monitor(nRoom);


if __name__ == '__main__':
    try:
        main();
    except KeyboardInterrupt as e:
        running = False;
        print('exiting...');
