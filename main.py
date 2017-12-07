import threading
import json
from sseclient import SSEClient as EventSource
import smtplib
from email.mime.text import MIMEText
import yaml
from flask import Flask, render_template
app = Flask(__name__)
app.config.update(yaml.load(open('config.yml')))

class ReadStream(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.ips = {}
		self.stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
		self.wikis = ['cswiki']

	def register_new_ip(self, ip, email):
		self.ips[ip] = [email]

	def read(self):
		print ('ok')

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

@app.route("/")
def main():
	return render_template('index.html')

@app.route("/table")
def table():
	return render_template('table.html')

if __name__ == "__main__":
	thread = threading.Thread()
	thread = ReadStream()
	thread.daemon = True
	thread.start()
	app.run(host="0.0.0.0")
