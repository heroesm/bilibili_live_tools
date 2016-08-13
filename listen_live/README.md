# bilibili直播监听

## 简介
该python脚本按照所给的bilibili直播房间号或播主ID监听其直播状态，当对方开启直播时调用you-get进行下载，或配合mpv进行观看

## 需求
* 安装you-get以下载直播流 `sudo -H pip3 install you-get`
* 安装mpv以直接观看直播

## 使用
直接打开脚本，输入房间号以调用you-get及mpv下载、观看直播，或使用 --help 命令行选项查看命令行参数。
