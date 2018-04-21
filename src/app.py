import json
import yaml
import datetime
import hashlib
import pymysql
import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, redirect, request, jsonify, session
app = Flask(__name__)

app.config.update(yaml.load(open('config.yml')))
app.secret_key = app.config.get('SECRET_KEY')

def connect():
	return pymysql.connect(
		database=app.config.get('DB_NAME'),
		host='tools-db',
		read_default_file=os.path.expanduser("~/replica.my.cnf"),
		charset='utf8mb4',
	)

@app.route("/")
def main():
	if session.get('authorized'):
		conn = connect()
		with conn.cursor() as cur:
			cur.execute('SELECT ip FROM ips WHERE mail=%s', session.get('authorized'))
			data = cur.fetchall()
			ips = []
			for row in data:
				ips.append(row[0])
		return render_template('table.html', ips=ips)
	return render_template('login.html')

@app.route('/logout')
def logout():
	session.clear()

@app.route('/validate', methods=['POST'])
def validate():
	random = hashlib.md5((request.form.get('email') + str(datetime.datetime.now())).encode('utf-8')).hexdigest()
	conn = connect()
	with conn.cursor() as cur:
		cur.execute('INSERT INTO validations(mail, random) VALUES (%s, %s)', (request.form.get('email'), random))
	conn.commit()
	link = "https://tools.wmflabs.org/ipwatcher/validate/" + request.form.get('email') + '/' + random
	text = """Vazeny sledovaci,
zadame Vas o potvrzeni pokusu o prihlaseni. Neni potreba si volit zadne heslo, prihlaseni vzdy potvrdite odkazem v e-mailu.

Link: """ + link + """

S pozdravem,
pratelsky system"""
	msg = MIMEText(text)

	msg['Subject'] = '[ipwatcher] Potvrzeni prihlaseni'
	msg['From'] = app.config.get('MAIL_FROM')
	msg['To'] = request.form.get('email')
	s = smtplib.SMTP('mail.tools.wmflabs.org')
	s.sendmail(app.config.get('MAIL_FROM'), request.form.get('email'), msg.as_string())
	s.quit()
	return render_template('validate.html', email=request.form.get('email'))

@app.route('/validate/<path:email>/<path:code>')
def validateLink(code, email):
	conn = connect()
	with conn.cursor() as cur:
		cur.execute('SELECT random FROM validations WHERE mail=%s', email)
		data = cur.fetchall()
	if len(data) == 1 and data[0][0] == code:
		with conn.cursor() as cur:
			cur.execute('DELETE FROM validations WHERE mail=%s', email)
			conn.commit()
		session['authorized'] = email
	return redirect('/ipwatcher')

if __name__ == "__main__":
	thread = threading.Thread()
	thread = ReadStream()
	thread.daemon = True
	thread.start()
	app.run(host="0.0.0.0")
