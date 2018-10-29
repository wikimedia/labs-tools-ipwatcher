# -*- coding: utf-8 -*-

import os
__dir__ = os.path.dirname(__file__)

import sys
sys.path.append(__dir__)

from sseclient import SSEClient as EventSource
import yaml
import json
import requests
import logging

from app import Watcher, IrcServer, IrcPreferences, db

stream = 'https://stream.wikimedia.org/v2/stream/recentchange'
wikis = ['cswiki'] # FIXME: T195005
ips = {}
ips_irc = {}

def getconfig():
	logging.info("I'm loading the config")
	return yaml.load(open(os.path.join(__dir__, 'config.yaml')))

def wplogin():
	logging.info('Logging to IP Watcher bot user was requested')
	s = requests.Session()
	config = getconfig()
	payload = {
		"action": "query",
		"format": "json",
		"meta": "tokens",
		"type": "login"
	}
	r = s.get(config['API_MWURI'], params=payload)
	logging.debug('Login token received, response is %s', r.json())
	token = r.json()['query']['tokens']['logintoken']
	payload = {
		"action": "login",
		"format": "json",
		"lgname": config['BOT_ACCOUNT_USERNAME'],
		"lgpassword": config['BOT_ACCOUNT_BOTPASSWORD'],
		"lgtoken": token
	}
	r = s.post(config['API_MWURI'], data=payload)
	logging.debug('I should be logged in. Response was %s', r.json())
	return s

def get_ips_email():
	logging.info("I'm fetching stalked IPs")
	db.session.commit() # TODO: Forces refreshing of newest data; Remove this dirty hack
	for watcher in Watcher.query.filter_by(notify_via_mail=True).all():
		if watcher.ip in ips:
			ips[watcher.ip].append(watcher.username)
		else:
			ips[watcher.ip] = [watcher.username]
	return ips

def notify_email(username, comment, domain, rev_id):
	text = """Dobrý den, 
Vámi sledovaná IP adresa %s provedla změnu na stránce. Shrnutí editace bylo %s. Editaci si můžete prohlédnout na %s. 

Tento e-mail byl odeslán nástrojem IP Watcher na základě sledování IP adresy %s v nástroji IP Watcher na https://tools.wmflabs.org/ipwatcher. 

S pozdravem, 

IP Watcher

Kontakt: tools.ipwatcher@tools.wmflabs.org
""" % (username, change['parsedcomment'], "https://%s/wiki/Special:Diff/%s" % (domain, rev_id), username)
	s = wplogin()
	config = getconfig()
	users = ips[username]
	for user in users:
		payload = {
			"action": "query",
			"format": "json",
			"meta": "tokens",
			"type": "csrf"
		}
		r = s.get(config['API_MWURI'], params=payload)
		logging.debug('CSRF token received, response is %s', r.json())
		token = r.json()['query']['tokens']['csrftoken']
		payload = {
			"action": "emailuser",
			"format": "json",
			"target": user,
			"subject": "[IPWatcher] IP adresa %s změnila stránku na %s" % (username, domain),
			"text": text,
			"token": token
		}
		r = s.post(config['API_MWURI'], data=payload)
		logging.debug('Mail was sent. Response was  %s', r.json())

if __name__ == "__main__":
	try:
		logging.basicConfig(filename='/data/project/ipwatcher/logs/ipwatcher.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
		#logging.info("I waked up from a long sleep") #FIXME This is not working, this should be displayed only once
		for event in EventSource(stream):
			if event.event == 'message':
				try:
					change = json.loads(event.data)
				except ValueError:
					continue
				if change['wiki'] in wikis:
					logging.debug("I detected a change that's from approved wiki, ID=%s", change['id'])
					ips = get_ips_email()
					if change['user'] in ips:
						logging.debug("I detected a change that was made by stalked user and should be announced via email; ID=%s", change['id'])
						notify_email(change['user'], change['parsedcomment'], change['meta']['domain'], change['revision']['new'])
						
	except Exception as e:
		logging.exception("Unknown exception occured while running")
