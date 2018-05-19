import json
import yaml
import pymysql
import requests
import os
from flask import Flask, render_template, redirect, request, jsonify, session, url_for
import mwoauth
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

def logged():
	return session.get('username') != None

def getusername():
    return session.get('username')

def blocked():
	username = session.get('username')
	if username == None:
		response = {
			'status': 'error',
			'errorcode': 'anonymoususe'
		}
		return response
	payload = {
		"action": "query",
		"format": "json",
		"list": "users",
		"usprop": "blockinfo",
		"ususers": username
	}
	r = requests.get(app.config['API_MWURI'], params=payload)
	data = r.json()['query']['users'][0]
	response = {
		'status': 'ok',
		'blockstatus': 'blockid' in data
	}
	if response['blockstatus']:
		response['blockdata'] = {
			'blockedby': data['blockedby'],
			'blockexpiry': data['blockexpiry'],
			'blockreason': data['blockreason']
		}
	return response

@app.route('/')
def index():
	username = session.get('username')
	if username is not None:
		if blocked()['blockstatus']:
			return render_template('blocked.html', logged=logged(), username=getusername())
		else:
			ips = []
			conn = connect()
			with conn.cursor() as cur:
				sql = 'SELECT ip, notify_via_mail, ircserver, ircchans FROM ips WHERE username=%s'
				cur.execute(sql, (getusername()))
				data = cur.fetchall()
			for row in data:
				notify_via_mail = True
				if row[1] == 0: notify_via_mail = False
				ips.append({
					"ip": row[0],
					"notify_via_mail": notify_via_mail,
					"ircserver": row[2],
					"ircchans": row[2]
				})
			return render_template('tool.html', logged=logged(), username=getusername(), ips=ips)
	else:
		return render_template('login.html', logged=logged(), username=getusername())

@app.route('/addip', methods=['POST'])
def addip():
	conn = connect()
	with conn.cursor() as cur:
		cur.execute('INSERT INTO ips(ip, username) VALUES (%s, %s)', (request.form.get('ip'), getusername()))
	conn.commit()
	return redirect(app.config['BASE_URL'])

@app.route('/delip', methods=['POST'])
def delip():
	conn = connect()
	with conn.cursor() as cur:
		cur.execute('DELETE FROM ips WHERE username=%s AND ip=%s', (getusername(), request.form.get('ip')))
	conn.commit()
	return 'ok'

@app.route('/login')
def login():
	"""Initiate an OAuth login.
	Call the MediaWiki server to get request secrets and then redirect the
	user to the MediaWiki server to sign the request.
	"""
	consumer_token = mwoauth.ConsumerToken(
		app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'])
	try:
		redirect_url, request_token = mwoauth.initiate(
		app.config['OAUTH_MWURI'], consumer_token)
	except Exception:
		app.logger.exception('mwoauth.initiate failed')
		return redirect(url_for('index'))
	else:
		session['request_token'] = dict(zip(
		request_token._fields, request_token))
		return redirect(redirect_url)


@app.route('/oauth-callback')
def oauth_callback():
	"""OAuth handshake callback."""
	if 'request_token' not in session:
		flash(u'OAuth callback failed. Are cookies disabled?')
		return redirect(url_for('index'))
	consumer_token = mwoauth.ConsumerToken(app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'])

	try:
		access_token = mwoauth.complete(
		app.config['OAUTH_MWURI'],
		consumer_token,
		mwoauth.RequestToken(**session['request_token']),
		request.query_string)
		identity = mwoauth.identify(app.config['OAUTH_MWURI'], consumer_token, access_token)
	except Exception:
		app.logger.exception('OAuth authentication failed')
	else:
		session['request_token_secret'] = dict(zip(access_token._fields, access_token))['secret']
		session['request_token_key'] = dict(zip(access_token._fields, access_token))['key']
		session['username'] = identity['username']

	return redirect(url_for('index'))


@app.route('/logout')
def logout():
	"""Log the user out by clearing their session."""
	session.clear()
	return redirect(url_for('index'))

if __name__ == "__main__":
	app.run(host="0.0.0.0")
