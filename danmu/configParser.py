#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

#from __future__ import print_function
#from __future__ import unicode_literals

import argparse
import re
import os.path

def display(*args, **kargs):
    try:
        print(*args, **kargs);
    except UnicodeEncodeError as e:
        args = (str(x).encode('gbk', 'replace').decode('gbk') for x in args);
        print(*args, **kargs);

class ConfigParser():
    ''' ConfigParser will not violate the input mConfig
    every key or values in the returned dictionary is of string type
    the mConfig argument is the model configuration dictionary
    the mExplan argument is the specification of documents responding to --help command line option
    the mMap argument is the dictionary containing check and conversion functions according to each configuration option
    '''
    def __init__(self, mConfig, mExplain=None, mMap=None, sDoc=None):
        self.mOriginConfig = mConfig;
        self.sDoc = sDoc;
        if (mConfig):
            self.mConfig = mConfig.copy();
        else:
            self.mConfig = {};
        if (mExplain):
            self.mExplain = mExplain.copy();
        else:
            self.mExplain = {};
        if (mMap):
            self.mMap = mMap.copy();
        else:
            self.mMap = {};

    def parse(self, sPath=None, isCLI=False):
        if (sPath):
            self.parseFile(sPath);
        if (isCLI):
            self.parseCLI();
        return self.mConfig;

    def parseFile(self, sPath):
        try:
            if (not os.path.exists(sPath)):
                display('找不到指定的配置文件 {}'.format(sPath));
                return;
            configFile = open(sPath, 'r', encoding='utf-8');
            mData = {};
            for sLine in configFile:
                sData = sLine;
                nEnd = sData.find('#')
                if (nEnd != -1):
                    sData = sData[:nEnd];
                result = re.search('^\\s*(\\w+)\\s*=\\s*([\\w.,]+)\\s*$', sData);
                if (result):
                    sKey = result.group(1);
                    sValue = result.group(2);
                    mData[sKey] = sValue;
            if (not self.mConfig):
                self.mConfig = mData;
            else:
                for x in self.mConfig.keys():
                    if x in mData.keys():
                        t = mData[x];
                        if (x in self.mMap.keys()):
                            t = self.mMap[x](t);
                        self.mConfig[x] = t;
            display('已载入配置文件 {}'.format(sPath));
        #except FileNotFoundError as e:
        #    display('配置文件 {} 不存在，使用默认值'.format(sPath));
        finally:
            if ('configFile' in locals()): configFile.close();

    def parseCLI(self):
        parser1 = argparse.ArgumentParser(description=self.sDoc);
        if (self.mExplain):
            for x in self.mExplain.keys():
                sShort = self.mExplain[x][1];
                sExplain = self.mExplain[x][0];
                if (sShort):
                    parser1.add_argument('-' + sShort, '--' + x.lower(), help=sExplain, dest=x);
                else:
                    parser1.add_argument('--' + x.lower(), help=sExplain, dest=x);

        elif (self.mConfig):
            for x in self.mConfig.keys():
                parser1.add_argument('--' + x);
        argsNamespace = parser1.parse_args();
        mData = vars(argsNamespace);
        sFeedback = '';
        for x in mData.keys():
            if (mData[x]):
                t = mData[x];
                if (x in self.mMap.keys()):
                    t = self.mMap[x](t);
                self.mConfig[x] = t;
                sFeedback += ' {} = {};'.format(x, mData[x]);
        if (sFeedback):
            sFeedback = '命令行设置:' + sFeedback;
            display(sFeedback);

def test():
    sFilePath = 'config.ini';
    configParser = ConfigParser(None);
    display(configParser.parse(sFilePath, True));

if __name__ == '__main__':
    test();
