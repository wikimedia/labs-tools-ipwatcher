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

app.config.update(yaml.load(open('config.yaml')))
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


if __name__ == "__main__":
	app.run(host="0.0.0.0")
