import threading
import json
from sseclient import SSEClient as EventSource
import smtplib
from email.mime.text import MIMEText
import yaml
from flask import Flask, render_template, redirect, request, jsonify
app = Flask(__name__)
app.config.update(yaml.load(open('config.yml')))

class ReadStream(threading.Thread):
	def __init__(self):
		global thread
		threading.Thread.__init__(self)
		self.ips = {}
		self.stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
		self.wikis = ['cswiki']

	def register_new_ip(self, ip, email):
		self.ips[ip] = [email]

	def deregister_ip(self, ip, email):
		if ip in self.ips:
			if email in self.ips[ip]:
				self.ips[ip].remove(email)

	def get_ips_per_user(self, email):
		res = []
		for ip in self.ips:
			if email in self.ips[ip]:
				res.append(ip)
		return res

	def run(self):
		for event in EventSource(self.stream):
			if event.event == 'message':
				try:
					change = json.loads(event.data)
				except ValueError:
					continue
				if change['wiki'] in self.wikis:
					if change['user'] in self.ips:
						text = """Vazeny sledovaci,
						Vami sledovana IP adresa provedla zmenu, vizte link.

						S pozdravem,
						pratelsky system
						"""
						msg = MIMEText(text)

						mailfrom = 'tools.urbanecmbot@tools.wmflabs.org'
						rcptto = self.ips[change['user']]
						msg['Subject'] = 'Test'
						msg['From'] = mailfrom
						msg['To'] = rcptto
						s = smtplib.SMTP('localhost')
						s.sendmail(mailfrom, [rcptto], msg.as_string())
						s.quit()

@app.route("/")
def main():
	return render_template('index.html')

@app.route("/table", methods=['POST'])
def table():
	global thread
	if request.form.get('ip'):
		thread.register_new_ip(request.form('ip'), request.form.get('email'))
	return render_template('table.html', ips=thread.get_ips_per_user(request.form.get('email')), email=request.form.get('email'))

@app.route('/newip', methods=['POST'])
def newip():
	global thread
	thread.register_new_ip(request.form('ip'), request.form.get('email'))
	return 'ok'

@app.route('/delip', methods=['POST'])
def delip():
	global thread
	thread.deregister_ip(request.form('ip'), request.form.get('email'))
	return 'ok'

@app.route('/getip')
def getip():
	global thread
	return jsonify(thread.get_ips_per_user(request.args.get('email')))

if __name__ == "__main__":
	thread = threading.Thread()
	thread = ReadStream()
	thread.daemon = True
	thread.start()
	app.run(host="0.0.0.0")
