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

	def connect(self):
		config = yaml.load(open('config.yml'))
		return pymysql.connect(
			database=config['DB_NAME'],
			host='tools-db',
			read_default_file=os.path.expanduser("~/replica.my.cnf"),
			charset='utf8mb4',
		)

	def refresh_ips(self):
		conn = self.connect()
		self.ips = {}
		with conn.cursor() as cur:
			cur.execute('SELECT ip, mail FROM ips')
			data = cur.fetchall()
		for row in data:
			if row[0] in self.ips:
				self.ips[row[0]].append(row[1])
			else:
				self.ips[row[0]] = [row[1]]

	def run(self):
		self.refresh_ips()
		print(self.ips)
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
