FROM netdata/netdata:stable

RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools


WORKDIR /usr/src/app/nanoticker
COPY . .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x autocopy.sh
RUN ./autocopy.sh

RUN apk --no-cache upgrade
RUN apk add --no-cache apache2

ENV APACHE_RUN_USER www-data
ENV APACHE_RUN_GROUP www-data
ENV APACHE_LOG_DIR /var/log/apache2
ENV APACHE_RUN_DIR /var/www/html

## Add line to pythond.d.conf
RUN echo "repstats_v21: yes" >> /usr/lib/netdata/conf.d/python.d.conf

RUN cp -r /var/www/repstat/public_html/* /var/www/localhost/htdocs/


#EXPOSE 80 19999

#CMD ["./run_tasks.sh"]





