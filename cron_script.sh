#!/usr/bin/bash

process=$(ps aux | grep server.py | grep -v grep | awk '{ print $2 }')

echo "$process"
if [ "$process" = "" ];
then
echo "no such process to kill as server.py, restart server"
screen python3 server.py
else
kill $process
echo "process killed"
sleep 2
screen python3 server.py
fi
