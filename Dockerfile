FROM netdata/netdata:v1.38.0


RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

WORKDIR /usr/src/app
#RUN apk add git
#RUN git clone https://github.com/gr0vity-dev/nanoticker.git
WORKDIR /usr/src/app/nanoticker
#RUN git checkout 
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

#Enable netdata graphs
RUN echo "repstats_v21: yes" >> /usr/lib/netdata/conf.d/python.d.conf
RUN cp netdata/python.d.conf /etc/netdata/python.d.conf
RUN cp netdata/repstats_v21.conf /etc/netdata/python.d/

# Replace placeholder in index.html
ARG ENV
ARG NETDATA_SERVER
ARG EXPLORER_BASE_URL
# Replace placeholder in index.html for NETDATA_SERVER
RUN sed -i 's#%%NETDATA_SERVER%%#'"$NETDATA_SERVER"'#g' public_html/index.html
RUN sed -i 's#%%EXPLORER_BASE_URL%%#'"$EXPLORER_BASE_URL"'#g' public_html/index.html

RUN cp -r public_html/* /var/www/localhost/htdocs/

#Reset netdata base container entrypoint
ENTRYPOINT ["/usr/bin/env"]
#start apache2 and  calc-reps python script
CMD ./run_tasks.sh


#DEBUG netdata : /usr/libexec/netdata/plugins.d/python.d.plugin repstats_v21 debug


