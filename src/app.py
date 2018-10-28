import json
import yaml
import pymysql
import requests
import os
from flask import Flask, render_template, redirect, request, jsonify, session, url_for, flash
import flask
import mwoauth

app = Flask(__name__, static_folder='../static')

app.config.update(yaml.load(open('config.yml')))
app.secret_key = app.config.get('SECRET_KEY')

ua = "IP Watcher (https://tools.wmflabs.org/ipwatcher; martin.urbanec@wikimedia.cz)"
requests.utils.default_user_agent = lambda: ua

@app.before_request
def force_https():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(
            'https://' + request.headers['Host'] + request.headers['X-Original-URI'],
            code=301
        )

@app.before_request
def check_permission():
	notRequireLoginIn = [
		'/login',
		'/oauth-callback'
	]
	if logged() or request.path in notRequireLoginIn:
		if blocked()['blockstatus']:
			return render_template('blocked.html')
	else:
		return render_template('login.html')


@app.context_processor
def inject_base_variables():
    return {
        "logged": logged(),
        "username": getusername(),
    }

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
			'status': 'ok',
			'blockstatus': False # Anons are treated as unblocked
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
	ips = []
	conn = connect()
	with conn.cursor() as cur:
		sql = 'SELECT ip, notify_via_mail, notify_via_irc FROM ips WHERE username=%s'
		cur.execute(sql, (getusername()))
		data = cur.fetchall()
	for row in data:
		notify_via_mail = row[1] == 1
		notify_via_irc = row[2] == 1
		ips.append({
			"ip": row[0],
			"notify_via_mail": notify_via_mail,
			"notify_via_irc": notify_via_irc,
		})
	return render_template('tool.html', ips=ips)

@app.route('/irc-preferences', methods=['GET', 'POST'])
def irc_preferences():
	conn = connect()
	with conn.cursor() as cur:
		cur.execute('SELECT irc_server, irc_channel FROM irc_preferences WHERE username=%s', getusername())
		irc_preferences = cur.fetchall()
	if len(irc_preferences) == 1:
		irc_server = irc_preferences[0][0]
		irc_channel = irc_preferences[0][1]
	else:
		irc_server = -1
		irc_channel = ""
	with conn.cursor() as cur:
		cur.execute('SELECT id, irc_server FROM ircservers')
		data = cur.fetchall()
	servers = []
	for row in data:
		servers.append({
			"id": row[0],
			"server": row[1],
		})
	if request.method == 'GET':
		return render_template('irc_preferences.html', servers=servers, irc_channel=irc_channel, irc_server=irc_server)
	else:
		irc_server = int(request.form.get('irc_server', -1))
		irc_channel = request.form.get('irc_channel')
		if irc_server == -1 or irc_channel == "":
			with conn.cursor() as cur:
				cur.execute('DELETE FROM irc_preferences WHERE username=%s', getusername())
				irc_server = -1
				irc_channel = ""
		else:
			with conn.cursor() as cur:
				cur.execute('SELECT id from irc_preferences WHERE username=%s', getusername())
				data = cur.fetchall()
			if len(data) == 0:
				with conn.cursor() as cur:
					cur.execute('INSERT INTO irc_preferences(username, irc_server, irc_channel) VALUES(%s, %s, %s)', (getusername(), irc_server, irc_channel))
			else:
				with conn.cursor() as cur:
					cur.execute('UPDATE irc_preferences SET irc_server=%s, irc_channel=%s WHERE id=%s', (irc_server, irc_channel, data[0][0]))
		conn.commit()
		return render_template('irc_preferences.html', messages=[{"type": "success", "text": "Your IRC preferences were changed"}], irc_server=irc_server, irc_channel=irc_channel, servers=servers)

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
