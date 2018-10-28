from flask import render_template, redirect, request, jsonify, session, url_for, flash
from __init__ import app

@app.route('/')
def index():
	return 'ok'
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
