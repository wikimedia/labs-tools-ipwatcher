from sseclient import SSEClient as EventSource
import smtplib
from email.mime.text import MIMEText
import yaml
import threading
import pymysql
import os

def connect():
	config = yaml.load(open('config.yml'))
	return pymysql.connect(
		database=config['DB_NAME'],
		host='tools-db',
		read_default_file=os.path.expanduser("~/replica.my.cnf"),
		charset='utf8mb4',
	)

def refresh_ips():
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

stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
wikis = ['cswiki']
ips = {}

if __name__ == "__main__":
	refresh_ips()
	print(ips)
	for event in EventSource(stream):
		if event.event == 'message':
			try:
				change = json.loads(event.data)
			except ValueError:
				continue
			if change['wiki'] in wikis:
				if change['user'] in ips:
					text = """Vazeny sledovaci,
					Vami sledovana IP adresa provedla zmenu, vizte link.

					S pozdravem,
					pratelsky system
					"""
					msg = MIMEText(text)

					mailfrom = 'tools.ipwatcher@tools.wmflabs.org'
					rcptto = ips[change['user']]
					msg['Subject'] = 'Test'
					msg['From'] = mailfrom
					msg['To'] = ", ".join(rcptto)
					s = smtplib.SMTP('mail.tools.wmflabs.org')
					s.sendmail(mailfrom, rcptto, msg.as_string())
					s.quit()
