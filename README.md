
# Nano Ticker

A real-time statistical tool to check Nano network health. Using data from public Nano Node Monitors.

[Public Site](https://nanoticker.info)

## Requirements
- nano-local test net setup
- every node needs a nanoNodeMonitor

## Install

In the context of nano-local private network run this :
-  docker run -d --network=nano-local -p 42002:80 -p 42003:19999 --name="nl_nanoticker" gr0vity/nanoticker 
-  docker exec -it nl_nanoticker /usr/sbin/httpd
-  docker exec -it nl_nanoticker nohup python3 ./script/calc-reps.py &


Many thanks to Joohansson for this beautifully looking tool. https://github.com/Joohansson/nanoticker
