from sseclient import SSEClient as EventSource
import smtplib
from email.mime.text import MIMEText
import yaml
import threading

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

						mailfrom = 'tools.ipwatcher@tools.wmflabs.org'
						rcptto = self.ips[change['user']]
						msg['Subject'] = 'Test'
						msg['From'] = mailfrom
						msg['To'] = ", ".join(rcptto)
						s = smtplib.SMTP('mail.tools.wmflabs.org')
						s.sendmail(mailfrom, rcptto, msg.as_string())
						s.quit()

if __name__ == "__main__":
    thread = threading.Thread()
    thread = ReadStream()
    thread.daemon = True
    thread.start()
