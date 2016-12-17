# bilibili直播监听

## 简介
该python脚本按照所给的bilibili直播房间号或播主ID监听其直播状态，当对方开启直播时调用you-get进行下载，或配合mpv进行观看

## 需求
* 安装you-get以下载直播流 `sudo -H pip3 install you-get` (注：因最近的bilibili直播的改动导致you-get失效，我添加了直接下载直播视频流的方法，现在该脚本不需依赖于you-get也可运行了）
* 安装mpv以直接观看直播

## 使用
直接打开脚本，输入房间号调用mpv观看直播视频流，命令行使用 -d 选项加房间号下载视频流，使用 --help 选项查看所有命令行参数。
