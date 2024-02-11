
#!/bin/bash

# Copy source files to netdata directories
echo "Copy plugin"
cp netdata/repstats-b.chart.py /usr/libexec/netdata/python.d/
cp netdata/repstats_v21.chart.py /usr/libexec/netdata/python.d/

echo "Copy plugin configs"
cp netdata/repstats-b.conf /usr/lib/netdata/conf.d/python.d/

mkdir -p /var/www/localhost/htdocs/json/
cp netdata/json/stats.json /var/www/localhost/htdocs/json/stats.json
cp netdata/json/monitors.json /var/www/localhost/htdocs/json/monitors.json

# echo "Copy custom themes"
# cp netdata/css/bootstrap-darkest.css /usr/share/netdata/web/css/
# cp netdata/css/bootstrap-darkly.css /usr/share/netdata/web/css/
# cp netdata/css/dashboard.darkest.css /usr/share/netdata/web/css/
# cp netdata/css/dashboard.darkly.css /usr/share/netdata/web/css/

cp netdata/dashboard_custom.js /usr/share/netdata/web/
