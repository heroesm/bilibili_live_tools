# bilibili直播提醒

## 简介
该javascript脚本监视 [http://live.bilibili.com/feed/getList/1](http://live.bilibili.com/feed/getList/1) （返回当前你所关注者的直播信息）页面，每30秒刷新一次，当出现符合条件（以播主昵称匹配正则表达式）的直播开启信息时，在浏览器中自动打开该直播页面。

## 使用
* 使用greasemonkey等用户脚本管理器安装该脚本并开启
* 打开页面 [http://live.bilibili.com/feed/getList/1](http://live.bilibili.com/feed/getList/1)

## 参见
* [github地址](https://github.com/heroesm/bilibili_live_tools/tree/master/bilibili_notify)
* [greasyfork地址](https://greasyfork.org/zh-CN/scripts/22383-bilibili-notify)