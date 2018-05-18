# -*- coding: utf-8 -*-

from sseclient import SSEClient as EventSource
import yaml
import pymysql
import os
import json
import requests
import logging

stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
wikis = ['cswiki']
ips = {}

def getconfig():
	logging.info('Config was loaded')
	return yaml.load(open('config.yml'))

def wplogin():
	logging.info('Logging to IP Watcher bot user was requested')
	s = requests.Session()
	config = getconfig()
	payload = {
		"action": "query",
		"format": "json",
		"meta": "tokens",
		"type": "login"
	}
	r = s.get(config['API_MWURI'], params=payload)
	logging.debug('Login token received, response is %s', r.json())
	token = r.json()['query']['tokens']['logintoken']
	payload = {
		"action": "login",
		"format": "json",
		"lgname": config['BOT_ACCOUNT_USERNAME'],
		"lgpassword": config['BOT_ACCOUNT_BOTPASSWORD'],
		"lgtoken": token
	}
	r = s.post(config['API_MWURI'], data=payload)
	logging.debug('I should be logged in. Response was %s', r.json())
	return s

def connect():
	config = getconfig()
	logging.info("I'm connecting to the local database")
	return pymysql.connect(
		database=config['DB_NAME'],
		host='tools-db',
		read_default_file=os.path.expanduser("~/replica.my.cnf"),
		charset='utf8mb4',
	)

def get_ips():
	conn = connect()
	logging.info("I'm fetching IPs and users needed")
	ips = {}
	with conn.cursor() as cur:
		cur.execute('SELECT ip, username FROM ips')
		data = cur.fetchall()
	for row in data:
		if row[0] in ips:
			ips[row[0]].append(row[1])
		else:
			ips[row[0]] = [row[1]]
	return ips

if __name__ == "__main__":
	logging.basicConfig(filename='/data/project/ipwatcher/logs/ipwatcher.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
	logging.info("I waked up from a long sleep")
	for event in EventSource(stream):
		if event.event == 'message':
			try:
				change = json.loads(event.data)
			except ValueError:
				continue
			if change['wiki'] in wikis:
				logging.debug("I detected a change that's from approved wiki")
				ips = get_ips()
				if change['user'] in ips:
					logging.debug("I detected a change that was made by stalked user.")
					text = """Milý sledovači,
proběhla změna. 

IPWatcher
tools.ipwatcher@tools.wmflabs.org
"""
					s = wplogin()
					config = getconfig()
					users = ips[change['user']]
					for user in users:
						payload = {
							"action": "query",
							"format": "json",
							"meta": "tokens",
							"type": "csrf"
						}
						r = s.get(config['API_MWURI'], params=payload)
						logging.debug('CSRF token received, response is %s', r.json())
						token = r.json()['query']['tokens']['csrftoken']
						payload = {
							"action": "emailuser",
							"format": "json",
							"target": user,
							"subject": "[ipwatcher] Proběhla změna",
							"text": text,
							"token": token
						}
						r = s.post(config['API_MWURI'], data=payload)
						logging.debug('Mail was sent. Response was  %s', r.json())
