#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

#import sys
#from __future__ import print_function
#from __future__ import unicode_literals
import threading
import time
from collections import deque

class Displayer():
    lock = threading.Lock();
    def __init__(self, nMode=0, nDelay=0):
        # nMode - whether to use threaded display
        # nDelay - the interval time during threaded display
        self.nMode = nMode;
        self.nDelay = nDelay;
        if (nMode == 0):
            self.display = self.commonDisplay;
        elif (nMode == 1):
            self.queue = deque();
            self.clock = threading.Event();
            self.thread = threading.Thread(target=self.dequeue);
            self.thread.daemon = 1;
            self.thread.start();
            self.display = self.threadedDisplay;
    def commonDisplay(self, *aArgs, **mArgs):
        type(self).lock.acquire(timeout=5);
        try:
            print(*aArgs, **mArgs);
        except UnicodeEncodeError as e:
            # deal with terminals using GBK encoding, like Windos in Chinese
            aArgs = (str(x).encode('gbk', 'replace').decode('gbk') for x in aArgs);
            #sCode = sys.stdin.encoding;
            #aArgs = (str(x).encode(sCode, 'replace').decode(sCode) for x in aArgs);
            print(*aArgs, **mArgs);
        finally:
            type(self).lock.release();
    def dequeue(self):
        while 1:
            while (len(self.queue) > 0):
                t = self.queue.popleft();
                self.commonDisplay(*t[0], **t[1]);
                time.sleep(self.nDelay);
            self.clock.clear();
            self.clock.wait();
    def threadedDisplay(self, *aArgs, **mArgs):
        self.queue.append((aArgs, mArgs));
        self.clock.set();

class SetInterval():
    # use self.clock to prompt the next execution
    def __init__(self, func, nTime):
        self.flag = False;
        self.clock = threading.Event();
        def f():
            while self.flag:
                self.clock.wait(nTime);
                self.clock.clear();
                func();
        self.thread = threading.Thread(target=f);
        self.thread.daemon = True;
    def start(self):
        self.flag = True;
        self.thread.start();
    def stop(self):
        self.flag = False;
