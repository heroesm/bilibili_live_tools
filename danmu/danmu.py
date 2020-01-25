#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

'''
refer from http://www.lyyyuna.com/2016/03/14/bilibili-danmu01/:

    connect:
        00 00 00 35 00 10 00 01  00 00 00 07 00 00 00 01
        {"roomid":1016,"uid":155973685728160}

    response:
        00 00 00 10 00 10 00 01  00 00 00 08 00 00 00 01

    online count:
        00 00 00 14 00 10 00 01  00 00 00 03 00 00 00 01
        00 00 3c 49

    heartbeat (30s interval):
        00 00 00 10 00 10 00 01  00 00 00 02 00 00 00 01

    message:
        00 00 00 d4 00 10 00 00  00 00 00 05 00 00 00 00
        {"info": [[0,1,25,1677721 5,1457958374,"14 57955655",0,"afa 9f72d",0],"..... ........ ..02..." ,[614943,"...... ......",0,0,0],[ 9,"..... .",".... ........ ...",115 ,12225255],[21,2 5827],[]],"cmd": "DANMU_MSG"}
'''
#from __future__ import print_function
#from __future__ import unicode_literals
import os.path
import sys
import socket
import json
import struct
import urllib.parse
import urllib.request
import urllib.error
import re
import random
from binascii import hexlify, unhexlify
import time
import threading
import select

from configParser import ConfigParser
from utility import Displayer, SetInterval

#import colorama
#colorama.init()

sAPI0 = 'https://space.bilibili.com/ajax/live/getLive?mid='
# using user ID to get the live status and the live room ID of that user
sAPI1 = 'https://live.bilibili.com/api/player?id=cid:';
# where to get the hostname of danmu server particular to certain room
sAPI2 = 'https://live.bilibili.com/live/getInfo?roomid=';    # obsolete
# where to get room-related information

sAPI4 = 'https://api.live.bilibili.com/room/v1/Room/room_init?id='
sAPI5 = 'https://api.live.bilibili.com/room/v1/Room/get_info?room_id='
sAPI6 = 'https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room?roomid='
sAPI7 = 'https://api.live.bilibili.com/room/v1/Danmu/getConf?platform=pc&player=web&room_id='

# the path to the configuration file
sPath = 'config.ini'
# log is the verbose level display function
log = None;
# the room ID
nRoom = None;
# the population of online audience, seems useless currently
nPop = None;
# flag that the programme is running, used to control the recursion in threads
running = False;
# flag that the danmu-related TCP socket is connected
alive = False;
# the character colour actually being used
aColour = [3, 17];
# the local file object to be written
localFile = None;
# the list of messages to be blocked
aBlock = [];
# the indicator of online counter notification; 0 means not notifying temporarily; 1 means notifying next time; 2 means notifying constantly
notifyMode = 2;
# the threading event corresonding to the manual activating of the online-counter
beatClock = None;

mRoom2Host = {};

# the default programme configuration
mConfig = {
        'gift': 0,
        # Note that colour is implemented using ANSI escape character, which is not completedly supported in windows, meaning that it may not work by running it directly or with powershell. Run the programme through cmd(which support win32api) to bypass the problem. Otherwise set it to 0 to roll back to monochrome mode.
        'colour': 1,
        'aColour': [3, 17],
        'nRoom': 0,
        'nDelay': 0,
        'singleLine': 0,
        'timeStamp': 1,
        'verbose': 0,
        'write': 0,
        'block': 1,
        'notify': 1
}

# explanation of configuration option, of format:
# <key> : (<description>, <shorthand>)
# <shorthand> could equal False meaning absence of shorthand, but the tuple must have two items
mExplain = {
        'gift': ('whether to display gift notification; should be equivalent to 0 or 1', 'g'),
        'colour': ('whether to use colour scheme, not fully supported in windows; should be equivalent to 0 or 1 ### Note that colour is implemented using ANSI escape character, which is not completedly supported in windows, meaning that it may not work by running it directly or with powershell. Run the programme through cmd(which support win32api) to bypass the problem. Otherwise set it to 0 to roll back to monochrome mode.', 'c'),
        'aColour': ('if colour scheme (see -c) is used, this option will determine the scheme specification; the value is of format: <sender colour>,<content colour> , i.e., two colour tokens separated by a comma; the colour token, specifying which colour to use, is represented in integer; there are 16 alternative colours in total, specified by 16 integer number: the integer from 0 to 7 represents Black, Red, Green, Yellow, Blue, Magenta, Cyan and White, respectively; then the integer from 10 to 17 represents the similar-named but brighter colour; note that 17 means pure white while 7 is shallow gray visually; learn more from ANSI escape code', 'a'),
        'nRoom': ('the default room ID; while enable it, room ID will not be read from command line; should be positive integer; zero defaults to get room ID from command line', 'r'),
        'nDelay': ('the separation time between every single danmu message; while used, the recommended value is 0.1 or 0.2; set to 0 to disable separation; should be zero or positive float', 'd'),
        'singleLine': ('whether to display every danmu message in a single line; should be equivalent to 0 or 1; defaults to 0 meaning displaying message in two lines', 's'),
        'timeStamp': ('whether to show receiving time of danmu message; should be equivalent to 0 or 1; defaluts to 1 meaning that, appending time stamp to sender name while singleLine is 0, and prepend time stamp to sender namer while singleLine is 1', 't'),
        'verbose': ('whether to display diagnostic information to console; should be equivalent to 0 or 1; defaults to 0', 'v'),
        'write': ('whether to write danmu messages to a local file, whose name will consists of the time, the hoster name and the room title; should be equivalent to 0 or 1; defaults to 0', 'w'),
        'block': ('whether to block flooding messages induced by toy television or tempo storm; should be equivalent to 0 or 1; defaults to 1', 'b'),
        'notify': ('whether to notify the number of online audiences every 30 seconds; should be equivalent to 0 or 1; defaults to 1', 'n')
}

# type specification of configuration option
mMap = {
        # doing type conversion of configuration
        'gift': lambda x: int(x),
        'colour': lambda x: int(x),
        'aColour': lambda x: [int(n) if (int(n) in list(range(0,8))+list(range(10,18)) and len(x.split(',')) == 2) else int(None) for n in x.split(',')],
        'nRoom': lambda x: int(x),
        'nDelay': lambda x: float(x),
        'singleLine': lambda x: int(x),
        'timeStamp': lambda x: int(x),
        'verbose': lambda x: int(x),
        'write': lambda x: int(x),
        'block': lambda x: int(x),
        'notify': lambda x: int(x)
}

def prepare():
    os.chdir(os.path.split(__file__)[0]);
prepare();

class SocketDied(OSError):
    # the socket connection to the danmu server has been closed
    pass;

# receive CR from stdin to send heartbeat message, which induce a online count response
def notify():
    'beatClock is the thread event instance which is involved in sending of heartbeat'
    global alive;
    global nPop;
    global notifyMode;
    global beatClock;
    try:
        while alive:
            input();
            if (notifyMode == 0):
                notifyMode = 1;
            if (beatClock): beatClock.set();
    except EOFError:
        beatClock.set();
        # send the last heartbeat while quitting the programme, receiving immediate  response to prevent from being blocked by socket.recv or socketfile.read
        display1('退出中');

def getHost(nRoom):
    global mRoom2Host;
    sHost = mRoom2Host.get(nRoom);
    if (sHost is None):
        try:
            f1 = urllib.request.urlopen(sAPI6 + str(nRoom));
            bData = f1.read();
            mData = json.loads(bData.decode());
            sHost = mData['data']['info']['uname'];
        except Exception as e:
            display('获取播主失败: ', e);
            sHost = '';
        finally:
            if ('f1' in locals()): f1.close();
    return sHost;

def getRoom(nRoom):
    'get real room ID and related information'
    def fetchRealRoom(nRoom):
        # 3 digit room IDs are all fake, so get the real room ID from the webpage
        try:
            #f1 = urllib.request.urlopen('http://live.bilibili.com/'+ str(nRoom));
            #bData = f1.read(5000);
            #nRoom = int(re.search(b'var ROOMID = (\\d+)?;', bData).group(1));
            f1 = urllib.request.urlopen(sAPI4 + str(nRoom));
            bData = f1.read();
            mData = json.loads(bData.decode());
            nRoom = mData['data']['room_id'];
            return nRoom
        finally:
            if ('f1' in locals()): f1.close();
    try:
        sServer = 'broadcastlv.chat.bilibili.com'
        nPort = 2243
        with urllib.request.urlopen(sAPI7 + str(nRoom)) as res:
            res_str = res.read().decode();
        obj = json.loads(res_str)
        data = obj ['data']
        sServer = data['host']
        nPort = data['port']
        # bRoomInfo = f1.read();
        # sRoomInfo = bRoomInfo.decode('utf-8');
        # f1 = urllib.request.urlopen(sAPI1 + str(nRoom));
        # bRoomInfo = f1.read();
        # sRoomInfo = bRoomInfo.decode('utf-8');
        # match = re.search('<server>(.*?)</server>', sRoomInfo)
        # if match:
        #     sServer = match.group(1);
        # hostname of danmu server
    except Exception as e:
        display1('获取弹幕服务器时连接超时',
                '尝试使用默认弹幕服务器地址',
                sep='\n');
        sServer = 'livecmt-1.bilibili.com';
    finally:
        if ('f1' in locals()): f1.close();
    if (not sServer):
        # not expected to happen
        raise Exception('Error: wrong server: '+repr(sServer));
    try:
        # get room information, e.g. room title and hoster
        nRoom = fetchRealRoom(nRoom);
        f1 = urllib.request.urlopen(sAPI5 + str(nRoom));
        bRoomInfo = f1.read();
        mData = json.loads(bRoomInfo.decode('utf-8'));
        sHost = getHost(nRoom);
        sTitle = mData['data']['title'];
        nStatus = mData['data']['live_status'];
        _status = 'on' if nStatus == 1 else 'off';
        display1('播主：{}\n房间：{}\n状态：{}'.format(sHost, sTitle, _status));
    except Exception as e:
        # not expected to happen
        display1('获取房间信息失败');
        raise;
        log(bRoomInfo);
    finally:
        if ('f1' in locals()): f1.close();
    return sServer, nPort, nRoom, sHost, sTitle;

def handler1(sock1):
    'handle danmu-related TCP socket with socket makefile'
    global alive;
    sock1.settimeout(None);
    try:
        fSock = sock1.makefile('rb');
        bLength = fSock.read(4);
        if (bLength == b''):
            raise SocketDied;
        nLength = struct.unpack('>I', bLength)[0];
        # the total length of the a single danmu message; the next 4 bytes is the header length
        bContent = fSock.read(nLength - 4);
        if (hexlify(bContent).startswith(b'001000010000000800000001')):
            # welcome message
            display1('已接入弹幕服务器', '按回车显示在线人数', 'ctrl-c退出');
            while alive:
                try:
                    bLength = fSock.read(4);
                    if (bLength == b''):
                        raise SocketDied;
                    nLength = struct.unpack('>I', bLength)[0];
                    bContent = fSock.read(nLength - 4);
                    handleDanmu(bContent);
                except TimeoutError as e:
                    log(e);
    finally:
        if ('fSock' in locals()): fSock.close();

def handler2(sock1):
    'handle danmu-related TCP socket with select'
    global alive;
    bData = sock1.recv(16);
    sock1.settimeout(0);
    if (hexlify(bData) == b'00000010001000010000000800000001'):
        # welcome message
        display1('已接入弹幕服务器', '按回车显示在线人数', 'ctrl-c退出');
    bBuff = b'';
    while alive:
        r, w, e = select.select([sock1], [], []);
        if (sock1 in r):
            # the danmu server may respond randomly splited danmu messgae aggregation, so using buffer to joint separated danmu message is necessary
            if (len(bBuff) < 4):
                bBuff += sock1.recv(4 - len(bBuff));
                if (len(bBuff) == 0):
                    raise SocketDied;
                if (len(bBuff) == 4):
                    nLength = struct.unpack('>I', bBuff)[0];
            else:
                bBuff += sock1.recv(nLength - len(bBuff));
                if (len(bBuff) == nLength):
                    handleDanmu(bBuff[4:]);
                    bBuff = b'';

def handleDanmu(bContent):
    'deal with separate danmu message and output them accordingly'
    global nPop;
    global nRoom;
    global aColour;
    global localFile;
    global aBlock;
    global notifyMode;
    if (bContent[0:4] == unhexlify('00100001')):
        # control info
        if (bContent[4:8] == unhexlify('00000003')):
            # online counter
            assert (bContent[8:12] == unhexlify('00000001'));
            nPop = struct.unpack('>I', bContent[12:16])[0];
            if (notifyMode):
                display1('在线数:',nPop, ' 房间号:', nRoom, sep='');
                if (notifyMode == 1):
                    notifyMode = 0;
        else:
            log('unknown control info', bContent, sep='\n');
    elif (bContent[0:4] == unhexlify('00100000')):
        if (bContent[4:8] == unhexlify('00000005')):
            # notification
            assert (bContent[8:12] == unhexlify('00000000'));
            mData = json.loads(bContent[12:].decode('utf-8'));
            #if (re.match(r'welcome|sys_gift|sys_msg|send_top|add_vt_member|bet_bettor|bet_banker', mData['cmd'].lower())):
            if ('cmd' not in mData):
                pass
            elif (mData['cmd'].lower() in ['welcome', 'welcome_guard', 'sys_gift', 'send_top', 'add_vt_member', 'bet_bettor', 'bet_banker', 'tv_start', 'tv_end', 'combo_end', 'room_rank', 'notice_msg', 'activity_banner_red_notice_close', 'week_star_clock', 'entry_effect']):
                # welcome message | system-wide gift message 1 | system-wide gift message 2 | virtual audience?
                log(mData)
            elif (mData['cmd'].lower() in ['sys_msg',]):
                if not '应援喵' in mData.get('msg', ''):
                    log(mData)
            elif (mData['cmd'].lower() == 'special_gift'):
                # add danmu storm message to blocked list
                if (aBlock):
                    mStorm = mData['data'].get('39');
                    if (mStorm):
                        if (mStorm['action'] == 'start'):
                            aBlock.append(mStorm['content']);
                            display('节奏风暴： ' + mStorm['content']);
                            cleanupTimer = threading.Timer(90,
                                lambda: aBlock.pop() if (len(aBlock) > 2) else 0
                            );
                            cleanupTimer.daemon = True;
                            cleanupTimer.start();
                else:
                    pass;
            elif (mData['cmd'].lower().startswith('danmu_msg')):
                # text message
                sSender = sRawSender = mData['info'][2][1];
                sMessage = sRawMessage = mData['info'][1];
                # block flooding message
                if (sMessage.strip() in aBlock):
                    return;
                if (mConfig['timeStamp']):
                    sTime = time.strftime("(%H:%M:%S)");
                else:
                    sTime = '';
                if (mConfig['colour']):
                    # ANSI escape charcter, preceded by \x1b (\033 or namely Escape character) and [, followed by m, 30-37 accord to colours - Black, Red, Green, Yellow, Blue, Magenta, Cyan and White; 90-97 accord to the same named but much brighter colours
                    colour = lambda x,y: '\x1b[{}m{}\x1b[00m'.format(y, x);
                    sSender = colour(sSender, aColour[0]);
                    sMessage = colour(sMessage, aColour[1]);
                if (mConfig['singleLine']):
                    display('{1} {0}: {2}'.format(sSender, sTime, sMessage));
                    if (localFile):
                        localFile.write('{1} {0}: {2}\n'.format(
                            sRawSender, sTime, sRawMessage
                        ));
                        #localFile.flush();
                else:
                    display('{0}: {1}\n    {2}'.format(sSender, sTime, sMessage));
                    if (localFile):
                        localFile.write('{0}: {1}\n    {2}\n'.format(
                            sRawSender, sTime, sRawMessage
                        ));
                        #localFile.flush();
            elif (mData['cmd'].lower() in ['combo_send', 'send_gift']):
                # gift message
                if (mConfig['gift']):
                    display( '{0} 赠送 {1} {2}'.format(
                        mData['data'].get('uname'),
                        mData['data'].get('num'),
                        mData['data'].get('giftName')
                    ));
            elif (mData['cmd'].lower() == 'room_block_msg'):
                display('{} 已被禁言'.format(mData['uname']));
            elif (mData['cmd'].lower() == 'room_silent_on'):
                # sType maybe means the user level under which users will be silent
                sType = str(mData['type']) if mData.get('type') and mData['type'] != -1 else '全局';
                display('开启{}禁言 {} 秒'.format(sType, mData.get('countdown')));
            elif (mData['cmd'].lower() == 'room_silent_off'):
                display('全局禁言已取消');
            elif (mData['cmd'].lower() == 'live'):
                display('直播开启');
            elif (mData['cmd'].lower() == 'preparing'):
                display('直播结束');
            else:
                # record unknown cmd field in response message, that possibly has been overlooked by me or newly added by bilibili
                with open('unknown_message.txt', 'a', encoding='utf-8') as f2:
                    f2.write('\n' + time.strftime("%m%d_%H%M%S-") + str(mData));
                log(mData);
        else:
            log('unknown notification', bContent, sep='\n');
    else:
        log('unknown type', bContent, sep='\n');


def show_history_msg(nRoom):
    try:
        api = 'https://api.live.bilibili.com/ajax/msg'
        data_bytes = urllib.parse.urlencode({'roomid': nRoom}).encode()
        with urllib.request.urlopen(api, data=data_bytes) as res:
            res_str = res.read().decode()
        obj = json.loads(res_str)
        item_list = obj['data']['room']
        display('历史弹幕:')
        for item in item_list:
            sSender = item['nickname']
            sMessage = item['text']
            display('  {}: {}'.format(sSender, sMessage));
    except Exception as err:
        display('failed to show history msg of room {}: {}'.format(nRoom, repr(err)))


def main():
    global sPath;
    global alive;
    global running;
    global mConfig, mMap, mExplain;
    global display, display1, display2;
    global log;
    global nRoom;
    global aColour;
    global localFile;
    global aBlock;
    global notifyMode;
    global beatClock;
    # use crafted display function to ease the migration from python3 to python2 and to accommodate to different terminal coding in different system
    # display1 is normal displayer, while display2 is a separate displayer running in special thread, implementing the display interval
    # in each case, display1 shall be a instant displayer; thus, use display1 to output diagnostic message
    display1 = Displayer(0).display;
    display = display1;
    mConfigBak = mConfig.copy();
    try:
        parser1 = ConfigParser(mConfig, mExplain, mMap, 'display danmu message in bilibili live');
        useCLI = True if len(sys.argv) > 1 else False;
        if (not os.path.exists(sPath)):
            sDir = os.path.split(sys.argv[0])[0];
            sFile = os.path.join(sDir, sPath);
            if (os.path.exists(sFile)):
                sPath = sFile;
            else:
                display1('配置文件 {} 不存在'.format(sPath));
                sPath = None;
        # parse configuration from file and from command line option
        mData = parser1.parse(sPath, useCLI);
        mConfig = mData;
    except Exception as e:
        display1('读取配置出错：', e, sep='\n');
        display1('退回默认配置');
        mConfig = mConfigBak;
    if (mConfig['nDelay'] > 0):
        # danmu message display interval is enabled, using threaded displayer
        display2 = Displayer(1, mConfig['nDelay']).display;
        display = display2;
    aColour = [(x + 30 if x < 10 else x + 80) for x in mConfig['aColour']];
    if (mConfig['verbose']):
        log = display1;
    else:
        def log(*aArgs, **mArgs): pass;
    if (mConfig['block']):
        # it seems that two format of flooding messages are existing
        aBlock = ['bilibili-(゜-゜)つロ乾杯~',
                  '- ( ゜- ゜)つロ 乾杯~ - bilibili',
                  '哔哩哔哩 (゜-゜)つロ 干杯~',
                  '哔哩哔哩 ( ゜ -゜)つロ 干杯~',
                  '忽如一夜春风来，千树万树樱花开！',
                  '送你一片樱花雨，生生世世陪伴你~',
                  '送你一片樱花雨，生生世世陪伴你～',
                  '一定要变强哦！(ง >o<)ง',
                  '忽如一夜春风来，千树万树樱花开！',
                  '你是我这一生都要守护的人~',
                  '能和你相遇真是太好啦！',
                  '你的魅力，喵不可言！',
                  '请问，需要来点兔子吗(*/ω＼*)？',
                  '今晚月色真美，风也温柔~',
        ];
    if (mConfig['notify']):
        notifyMode = 2;
    else:
        notifyMode = 1;
    log(mConfig);
    nRoom = mConfig['nRoom'] or int(input('room ID:'));
    running = True;
    socket.setdefaulttimeout(10);
    while running:
        try:
            try:
                sServer, nPort, nRoom, sHoster, sTitle = getRoom(nRoom);
                nPort = nPort or 788
            except urllib.error.HTTPError as e:
                if (e.code == 404):
                    display1('找不到该房间，请重新输入房间号');
                    nRoom = int(input('room ID:'));
                    continue;
                else:
                    raise;
            show_history_msg(nRoom)
            if (mConfig['write']):
                sTime = time.strftime('%y%m%d_%H%M%S-');
                sName = sHoster + '-' + sTitle;
                sName = re.sub(r'[^\w_\-.()]', '-', sName);
                sFileName = '{}{}.txt'.format(sTime, sName);
                localFile = open(sFileName, 'a', encoding='utf-8');
            log('弹幕服务器 ' + sServer);
            aAddr1 = (sServer, nPort);
            sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
            try:
                sock1.connect(aAddr1);
            except TimeoutError as e:
                sock1.close();
                display1('到弹幕服务器的连接失败，尝试更换地址');
                if (sServer == 'livecmt-1.bilibili.com'):
                    sServer = 'livecmt-2.bilibili.com';
                else:
                    sServer = 'livecmt-1.bilibili.com';
                log('弹幕服务器 ' + sServer);
                aAddr1 = (sServer, nPort);
                sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM);
                sock1.connect(aAddr1);
            log('地址为 ', *sock1.getpeername());
            nUid = int(100000000000000 + 200000000000000*random.random());
            # a random meaningless user ID
            #bPayload = b'{"roomid":%d,"uid":%d}' % (nRoom, nUid);
            bPayload = ('{"roomid":%d,"uid":%d}' % (nRoom, nUid)).encode('utf-8');
            nLength = len(bPayload) + 16;
            bReq = struct.pack('>IIII', nLength, 0x100001, 0x7, 0x1);
            bReq += bPayload;
            sock1.sendall(bReq);
            alive = True;
            bHeartBeat = struct.pack('>IIII', 0x10, 0x100001, 0x2, 0x1);
            sock1.sendall(bHeartBeat);
            # send heartbeat message per 30 seconds
            interval = SetInterval(lambda:(sock1.sendall(bHeartBeat)), 30);
            interval.start();
            # capture CR in stdin to send hearbeat in order to fetch freshed online count
            if (not beatClock):
                beatClock = interval.clock;
                t = threading.Thread(target=notify);
                t.daemon = 1;
                t.start();
            else:
                beatClock = interval.clock;
            handler1(sock1);
        except (socket.timeout, TimeoutError) as e:
            display1('连接超时，重试...');
            continue;
        except (OSError, SocketDied) as e:
            display1('连接被关闭，程序重启...');
            continue;
        except BaseException as e:
            if (isinstance(e, KeyboardInterrupt)):
                display1('程序退出');
                running = False;
            elif (sys.version[0] == '3' and isinstance(e, ConnectionResetError)):
                # ConnectionResetError is not supported in python2
                display1(e);
                display1('到服务器的连接被断开，尝试重新连接...');
                continue;
            else:
                with open('danmu_error.log', 'ab') as f1:
                    # record error log
                    f1.write(('\n'+(str(e))).encode('utf-8'));
                raise;
        finally:
            alive = False;
            if ('interval' in locals()): interval.stop();
            if ('sock1' in locals()): sock1.close();
            if (localFile):
                display1('弹幕已保存到文件 {}'.format(localFile.name));
                localFile.close();
                fn = localFile.name
                if (os.path.isfile(fn) and os.path.getsize(fn) == 0):
                    try:
                        display1('删除空弹幕文件 {}'.format(fn))
                        os.remove(fn);
                    except Exception as err:
                        display1(repr(err))

if __name__ == '__main__':
    main();
