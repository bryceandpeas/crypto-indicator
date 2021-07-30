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
		
		self.new_selection = False

	def create_menu(self):
		# Init menu
		main_menu = Gtk.Menu()
		
		# Get all protocols from loaded config
		protocols = []
		for key, value in CONFIG.cryptos.items():
			if value['protocol'] not in protocols:
				protocols.append(value['protocol'])
		
		# Create protocol sub-menu items from listed crypto protocols
		for protocol in protocols:
			protocol_menu = Gtk.Menu()
			protocol_item = Gtk.MenuItem.new_with_label(protocol)
			protocol_item.set_submenu(protocol_menu)
			main_menu.append(protocol_item)
			
			# Create sub-menu items from loaded Crypto JSON
			for k, v in CONFIG.cryptos.items():
				if protocol == v['protocol']:
					menu_item = Gtk.MenuItem.new_with_label(k.title())
					menu_item.connect('activate', self.init_updater, k)
					protocol_menu.append(menu_item)
			
		menu_seperator = Gtk.SeparatorMenuItem()
		menu_quit = Gtk.MenuItem.new_with_label('Quit')
		menu_quit.connect('activate', self.stop)
		
		main_menu.append(menu_seperator)
		main_menu.append(menu_quit)
		
		# Show all menu items
		main_menu.show_all()
		
		return main_menu
		
	def get_pricing(self, crypto):
		r = requests.get('https://api.kraken.com/0/public/Ticker?pair={0}'.format(CONFIG.cryptos[crypto]['pair']))
		crypto_json = r.json()
		crypto_price = crypto_json['result'][CONFIG.cryptos[crypto]['kraken_token']]['a'][0]
		return round(float(crypto_price), 2)
		
	def init_updater(self, source, crypto):
		if self.new_selection == False:
			# Set new_selection to True to break previous loop and end thread
			self.new_selection = True
			# Wait update_time before creating new thread 
			sleep(CONFIG.update_time)
			self.new_selection = False
			self.update = Thread(name=crypto, target=self.update_pricing, kwargs={'crypto': crypto, 'new_selection': self.new_selection, 'source': source})
			self.update.setDaemon(True)
			self.update.start()
		elif self.new_selection == True:
			self.new_selection = False
			print(self.new_selection)
			self.update = Thread(name=crypto, target=self.update_pricing, kwargs={'crypto': crypto, 'new_selection': self.new_selection, 'source': source})
			self.update.setDaemon(True)
			self.update.start()
			
		return None
	
	# Call the get_pricing function and append set the indicator label to the returned price
	def update_pricing(self, source, new_selection, crypto):
		icon = CONFIG.cryptos[crypto]['icon']
		name = crypto.title()
		pair = CONFIG.cryptos[crypto]['pair']
		symbol = CONFIG.cryptos[crypto]['code']
		
		self.update_label(name, icon)
		
		while True:
			if self.new_selection == True:
				break
			else:
				price = symbol + ' ' + name + ': £' + str(self.get_pricing(crypto))
				GLib.idle_add(
					self.indicator.set_label,
					price, self.app,
					priority=GLib.PRIORITY_DEFAULT
					)
				sleep(CONFIG.update_time)
	
	# Update the label to display the selected crypto name and associated icon			
	def update_label(self, name, icon):
		iconpath = str(CONFIG.icon_dir) + 'blank.png'

		self.indicator.set_icon_full(iconpath, self.app)
		self.indicator.set_label("Updating...", self.app)

	# Call to quit the program
	def stop(self, source):
		Gtk.main_quit()
		

if __name__ == "__main__":
	CONFIG = load_configuration()
	CryptoIndicator()
	signal(SIGINT, SIG_DFL)
	Gtk.main()
