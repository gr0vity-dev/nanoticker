#!/bin/sh
echo "/usr/sbin/httpd &"  
/usr/sbin/httpd &
echo "nohup python3 ./script/calc-reps.py &"  
nohup python3 ./script/calc-reps.py &

# Exit with status of process that exited first
exit $?