from sseclient import SSEClient as EventSource
import smtplib
from email.mime.text import MIMEText
import yaml
import threading
import pymysql
import os
import json

stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
wikis = ['cswiki']
ips = {}

def connect():
	config = yaml.load(open('config.yml'))
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
			print(change['wiki'])
			if change['wiki'] in wikis:
				ips = get_ips()
				print(change['user'])