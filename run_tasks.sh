#!/bin/sh

nohup /usr/sbin/run.sh & #not sure if needed
/usr/sbin/httpd &
python3 ./stats_gatherer/main.py

# Exit with status of process that exited first
exit $?