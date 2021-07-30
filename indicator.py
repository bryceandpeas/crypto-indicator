#!/usr/bin/env python3

import base64, configparser, hashlib, hmac, json, os, urllib.request
from collections import namedtuple
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

# Load Config File

def load_configuration():
	config = configparser.ConfigParser()
	config.read('config/config.ini')
	config.get('UPDATE_TIME', 'TIME')

	api_key = config['API']['KEY']
	api_sign = config['API']['SIGN']
	cryptos = json.loads(config['CRYPTOS']['UK'])
	icon_dir = config['ICONPATH']['PATH']
	update_time = int(config['UPDATE_TIME']['TIME'])
	
	config = namedtuple("config", "api_key api_sign cryptos icon_dir update_time")
	CONFIG = config(api_key, api_sign, cryptos, icon_dir, update_time)

	return CONFIG
	
def get_kraken_auth():
	""" Modified from: 
		https://support.kraken.com/hc/en-us/articles/360034437672-How-to-retrieve-a-WebSocket-authentication-token-Example-code-in-Python-3
	"""
	api_nonce = bytes(str(int(time()*1000)), "utf-8")
	api_request = urllib.request.Request("https://api.kraken.com/0/private/GetWebSocketsToken", b"nonce=%s" % api_nonce)
	api_request.add_header("API-Key", CONFIG.api_key)
	api_request.add_header("API-Sign", base64.b64encode(hmac.new(base64.b64decode(CONFIG.api_sign), b"/0/private/GetWebSocketsToken" + hashlib.sha256(api_nonce + b"nonce=%s" % api_nonce).digest(), hashlib.sha512).digest()))

	return(json.loads(urllib.request.urlopen(api_request).read())['result']['token'])


class CryptoIndicator():

	def __init__(self):
		self.app = 'CryptoIndicator'
		iconpath = CONFIG.icon_dir + "money.png"
		
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
		menu_bitcoin.connect('activate', self.init_updater, CONFIG.cryptos['bitcoin'])
		menu_ethereum.connect('activate', self.init_updater, CONFIG.cryptos['ethereum'])
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
		icon = crypto['icon']
		name = crypto['name'].title()
		pair = crypto['pair']
		
		self.update_label(name, icon)
		price = str(self.get_pricing(crypto))
		
		while True:
			price = name + ': £' + str(self.get_pricing(crypto))
			GLib.idle_add(
				self.indicator.set_label,
				price, self.app,
				priority=GLib.PRIORITY_DEFAULT
				)
			sleep(CONFIG.update_time)
	
	# Update the label to display the selected crypto name and associated icon			
	def update_label(self, name, icon):
		iconpath = str(CONFIG.icon_dir) + icon

		self.indicator.set_icon_full(iconpath, self.app)
		self.indicator.set_label(name, self.app)

	# Call to quit the program
	def stop(self, source):
		Gtk.main_quit()

if __name__ == "__main__":
	CONFIG = load_configuration()
	print(CONFIG.icon_dir)
	CryptoIndicator()
	signal(SIGINT, SIG_DFL)
	Gtk.main()
