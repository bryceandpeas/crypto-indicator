#!/usr/bin/env python3

import base64, hashlib, hmac, json, os, urllib.request
from signal import signal, SIGINT, SIG_DFL
from threading import Thread
from time import time, sleep

import requests
from gi import require_version

# Load namespace with Gtk 3.0 and AppIndicator 0.1
# These need to be specified before importing either
require_version('Gtk', '3.0')
require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, AppIndicator3, GLib

UPDATE_TIME = 10
CRYPTO_PAIRS = {
				'bitcoin': {'name': 'bitcoin', 'pair':'BTCGBP', 'kraken_token':'XXBTZGBP', 'iconpath': '/bitcoin.png'},
				'ethereum': {'name': 'ethereum', 'pair':'ETHGBP', 'kraken_token':'XETHZGBP', 'iconpath': '/ethereum.png'}
			   }
CURR_DIR = os.getcwd()

def get_kraken_auth():
	""" Modified from: 
		https://support.kraken.com/hc/en-us/articles/360034437672-How-to-retrieve-a-WebSocket-authentication-token-Example-code-in-Python-3
	"""
	api_nonce = bytes(str(int(time()*1000)), "utf-8")
	api_request = urllib.request.Request("https://api.kraken.com/0/private/GetWebSocketsToken", b"nonce=%s" % api_nonce)
	api_request.add_header("API-Key", "")
	api_request.add_header("API-Sign", base64.b64encode(hmac.new(base64.b64decode(""), b"/0/private/GetWebSocketsToken" + hashlib.sha256(api_nonce + b"nonce=%s" % api_nonce).digest(), hashlib.sha512).digest()))

	return(json.loads(urllib.request.urlopen(api_request).read())['result']['token'])


class CryptoIndicator():

	def __init__(self):
		self.app = 'CryptoIndicator'
		iconpath = CURR_DIR + "/money.png"
		
		self.indicator = AppIndicator3.Indicator.new(
			self.app, iconpath,
			AppIndicator3.IndicatorCategory.OTHER)
		self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)	   
		self.indicator.set_menu(self.create_menu())
		self.indicator.set_label("Select Crypto", self.app)

	def create_menu(self):
		# Init menu
		menu = Gtk.Menu()
		
		# Create menu items
		menu_bitcoin = Gtk.MenuItem.new_with_label('Bitcoin')
		menu_ethereum = Gtk.MenuItem.new_with_label('Ethereum')
		menu_seperator = Gtk.SeparatorMenuItem()
		menu_quit = Gtk.MenuItem.new_with_label('Quit')
		
		# Create menu item actions
		menu_bitcoin.connect('activate', self.init_updater, CRYPTO_PAIRS['bitcoin'])
		menu_ethereum.connect('activate', self.init_updater, CRYPTO_PAIRS['ethereum'])
		menu_quit.connect('activate', self.stop)
		
		# Add items to menu
		menu.append(menu_bitcoin)
		menu.append(menu_ethereum)
		menu.append(menu_seperator)
		menu.append(menu_quit)
		
		# Show all menu items
		menu.show_all()
		
		return menu
		
	def get_pricing(self, crypto):
		r = requests.get('https://api.kraken.com/0/public/Ticker?pair={0}'.format(crypto['pair']))
		crypto_json = r.json()
		crypto_price = crypto_json['result'][crypto['kraken_token']]['a'][0]
		return round(float(crypto_price), 2)
		
	def init_updater(self, source, crypto):
		self.update = Thread(target=self.update_pricing, kwargs={'crypto': crypto, 'source': source})
		self.update.setDaemon(True)
		self.update.start()
		return None
	
	# Call the get_pricing function and append set the indicator label to the returned price
	def update_pricing(self, source, crypto):
		iconpath = crypto['iconpath']
		name = crypto['name'].title()
		pair = crypto['pair']
		
		self.update_label(name, iconpath)
		price = str(self.get_pricing(crypto))
		
		while True:
			price = name + ': £' + str(self.get_pricing(crypto))
			GLib.idle_add(
				self.indicator.set_label,
				price, self.app,
				priority=GLib.PRIORITY_DEFAULT
				)
			sleep(UPDATE_TIME)
	
	# Update the label to display the selected crypto name and associated icon			
	def update_label(self, name, iconpath):
		iconpath = CURR_DIR + iconpath
		self.indicator.set_icon_full(iconpath, self.app)
		self.indicator.set_label(name, self.app)

	# Call to quit the program
	def stop(self, source):
		Gtk.main_quit()

if __name__ == "__main__":
	CryptoIndicator()
	signal(SIGINT, SIG_DFL)
	Gtk.main()
