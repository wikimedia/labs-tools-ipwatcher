#!/usr/bin/env python3

import json
from sseclient import SSEClient as EventSource
import smtplib
from email.mime.text import MIMEText

class ReadStream():
	def __init__(self):
		self.ips = {}
		self.stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
		self.wikis = ['cswiki']

	def register_new_ip(self, ip, email):
		self.ips[ip] = email

	def run(self):
		for event in EventSource(self.stream):
			if event.event == 'message':
				try:
					change = json.loads(event.data)
				except ValueError:
					continue
				if change['wiki'] in self.wikis:
					print(json.dumps(change))
					text = """Vazeny sledovaci,
					Vami sledovana IP adresa provedla zmenu, vizte link.

					S pozdravem,
					pratelsky system
					"""
					msg = MIMEText(text)

					mailfrom = 'tools.urbanecmbot@tools.wmflabs.org'
					rcptto = 'test@wikimedia.cz'
					msg['Subject'] = 'Test'
					msg['From'] = mailfrom
					msg['To'] = rcptto
					s = smtplib.SMTP('localhost')
					s.sendmail(mailfrom, [rcptto], msg.as_string())
					s.quit()
					import sys
					sys.exit()

if __name__ == '__main__':
	rs = ReadStream()
	rs.run()
