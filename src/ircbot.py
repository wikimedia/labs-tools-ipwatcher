#!/usr/bin/env python

##########################################################################
# This script is supposed to stay active, watch IRC queue in the DB
# and relay everything it founds in that queue.
# Author: Martin Urbanec <martin.urbanec@wikimedia.cz>
##########################################################################

import socket
import yaml
import pymysql
import os
import logging

def getconfig():
	logging.info("I'm loading the config")
	return yaml.load(open('/data/project/ipwatcher/www/python/src/config.yml'))

def connect():
	config = getconfig()
	logging.info("I'm connecting to the local database")
	return pymysql.connect(
		database=config['DB_NAME'],
		host='tools-db',
		read_default_file=os.path.expanduser("~/replica.my.cnf"),
		charset='utf8mb4',
	)


if __name__ == "__main__":
    # Set up logging
    #logging.basicConfig(filename='/data/project/ipwatcher/logs/ircbot.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

    # Required variables
    ping = 'PING '
    pong = 'PONG '

    try:
        # Fetch config
        config = getconfig()

        # Connect.
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("irc.rcm.wmflabs.org", 6667))

        # Set nickname, authenticate.
        client.send('NICK ' + config['IRC_ACCOUNT_USERNAME'] + '\r\n')
        client.send('USER ' + config['IRC_ACCOUNT_USERNAME'] + ' 0 * :IPWatcher\r\n')
        data = client.recv(1024)

        client.send('PRIVMSG NickServ :IDENTIFY ' + config['IRC_ACCOUNT_PASSWORD'] + '\r\n')
        data = client.recv(1024)

        # Join initial channel
        client.send('JOIN #Urbanecm\r\n')

        # Output and ping/pong.
        while True:
            #client.send('PRIVMSG #Urbanecm :Testing\r\n')
            #data = client.recv(1024)

            if data.startswith(ping):
                resp = data.strip(ping)
                client.send(pong + resp)
    except Exception as e:
        logging.exception("Unknown exception occured while running")
