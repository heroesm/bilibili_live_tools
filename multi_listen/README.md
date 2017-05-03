```
$ python3 multilisten.py -h
usage: multilisten.py [-h] [-r ROOM] [-u USER] [-d DIR] [-v] [-s SCRIPT]
                      [-c COMMAND] [-i INTERVAL]

simultaneously monitor status of plural rooms at live.bilibili.com, and
download streaming ones

optional arguments:
  -h, --help            show this help message and exit
  -r ROOM, --room ROOM  IDs of rooms to listen, separated by comma
  -u USER, --user USER  IDs of users who host the rooms to listen, separated
                        by comma
  -d DIR, --dir DIR     directory to be downloaded into
  -v, --verbose         show verbose debug information
  -s SCRIPT, --script SCRIPT
                        python scripts to be executed after a successful
                        download; the downloaded file path will be passed as
                        the first script argument ( sys.argv[1] )
  -c COMMAND, --command COMMAND
                        the command to be executed after a successful
                        download; the downloaded file path will replace "{0}"
                        within the command, using format syntax (
                        COMMAND.format(FILEPATH) )
  -i INTERVAL, --interval INTERVAL
                        the interval, in seconds, between each status poll
                        round
```
