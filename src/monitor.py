# -*- coding: utf-8 -*-

from sseclient import SSEClient as EventSource
import yaml
import pymysql
import os
import json
import requests

stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
wikis = ['cswiki']
ips = {}

def getconfig():
	return yaml.load(open('config.yml'))

def wplogin():
	s = requests.Session()
	config = getconfig()
	payload = {
		"action": "query",
		"format": "json",
		"meta": "tokens",
		"type": "login"
	}
	r = s.get(config['API_MWURI'], params=payload)
	token = r.json()['query']['tokens']['logintoken']
	payload = {
		"action": "login",
		"format": "json",
		"lgname": config['BOT_ACCOUNT_USERNAME'],
		"lgpassword": config['BOT_ACCOUNT_BOTPASSWORD'],
		"lgtoken": token
	}
	r = s.post(config['API_MWURI'], data=payload)
	return s

def connect():
	config = getconfig()
	return pymysql.connect(
		database=config['DB_NAME'],
		host='tools-db',
		read_default_file=os.path.expanduser("~/replica.my.cnf"),
		charset='utf8mb4',
	)

def get_ips():
	conn = connect()
	ips = {}
	with conn.cursor() as cur:
		cur.execute('SELECT ip, mail FROM ips')
		data = cur.fetchall()
	for row in data:
		if row[0] in ips:
			ips[row[0]].append(row[1])
		else:
			ips[row[0]] = [row[1]]
	return ips

if __name__ == "__main__":
	for event in EventSource(stream):
		if event.event == 'message':
			try:
				change = json.loads(event.data)
			except ValueError:
				continue
			if change['wiki'] in wikis:
				ips = get_ips()
				if change['user'] in ips:
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
					token = r.json()['query']['tokens']['csrftoken']
					payload = {
						"action": "emailuser",
						"format": "json",
						"target": user,
						"subject": "[ipwatcher] Proběhla změna",
						"text": text,
						"token": token
					}
					s.post(config['API_MWURI'], data=payload)
