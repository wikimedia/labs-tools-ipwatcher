import json
import yaml
import pymysql
import requests
import os
from flask import Flask, render_template, redirect, request, jsonify, session, url_for, flash
import flask
import mwoauth
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__, static_folder='../static')

app.config.update(yaml.load(open('config.yml')))
app.secret_key = app.config.get('SECRET_KEY')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Watcher(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	ip = db.Column(db.Text, nullable=False)
	username = db.Column(db.Text, nullable=False)
	notify_via_mail = db.Column(db.Boolean, nullable=False, default=True)
	notify_via_irc = db.Column(db.Boolean, nullable=False, default=False)

class IrcServer(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	irc_server = db.Column(db.Text)

class IrcPreferences(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.Text)
	irc_server = db.Column(db.Integer, db.ForeignKey(IrcServer.id))

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
	return render_template('tool.html', ips=Watcher.query.filter_by(username=getusername()).all())

@app.route('/addip', methods=['POST'])
def addip():
	ip = Watcher(username=getusername(), ip=request.form.get('ip'))
	db.session.add(ip)
	db.session.commit()
	return redirect(url_for('index'))

@app.route('/delip', methods=['POST'])
def delip():
	Watcher.query.filter_by(username=getusername(), ip=request.form.get('ip')).delete()
	db.session.commit()
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
