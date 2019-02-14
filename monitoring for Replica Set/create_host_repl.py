#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
'@file: create_host_repl.py
'@author: liyunting
'@version: 1
'@lastModify: 2019-02-14 15:34
'
'''

import json
import sys
import getopt
import requests


def zabbix_call(payload, zabbix_server):
	'''Call zabbix web api by json-rpc.

	Args:
		payload        dict    the parameter to be passed  
		zabbix_server  string  the ip of zabbix server 

	Returns:
		the request response object  
	'''
	url = "http://" + zabbix_server + "/zabbix/api_jsonrpc.php"
	headers = {'content-type': 'application/json'}
	response = requests.post(url, data=json.dumps(payload), headers=headers).json()
	return response


def zabbix_auth(user, pwd, zabbix_server):
	'''Connect to zabbix server and authenticate by the given username and password.

	Args:
		user           string   the zabbix server username
		pwd            string   the zabbix server password
		zabbix_server  string   the ip of zabbix server

	Returns:
		the authentication token
	'''
	auth = ''
	payload = {
	    "method": "user.login",
	    "params": {
	    	"user": user,
	    	"password": pwd
	    },
	    "jsonrpc": "2.0",
	    "id": 1,
	    "auth": None
	}
	res = zabbix_call(payload, zabbix_server) 
	if 'result' in res :
		auth = res['result']
	else:
		print(res['error'])
	return auth


def zabbix_create_group(auth, groupname, zabbix_server):
	'''Connect to zabbix server and create host group.

	If the host group exists, it will be failed. And if it does not exist, then create it and return
	the id of the host group.

	Args:
		auth           string   your authentication token
		groupname      string   the name of the hostgroup
		zabbix_server  string   the ip of zabbix server

	Returns:
		the host group id
	'''
	host_group_id = ''
	payload = {
		"jsonrpc": "2.0",
		"method": "hostgroup.create",
		"params": {
		    "name": groupname
		},
		"auth": auth,
		"id": 1
	}
	res = zabbix_call(payload, zabbix_server)
	if 'result' in res :
		host_group_id = res['result']['groupids'][0]
		print('create hostgroup:', groupname, 'successfully')
	else:
		print("error in creating hostgroup:", groupname)
		print(res['error'])
	return host_group_id


def zabbix_import_template(auth, filepath, zabbix_server):
	'''Connect to zabbix server and import the MongoDB template.

	Args:
		auth          string   your authentication token
		filepath      string   the whole path of the xml file(e.g. '/root/liyunting/example.xml')
		zabbix_server string   the ip of zabbix server
	'''
	with open(filepath,'r') as f:
		content = f.read()
	payload = {
		"jsonrpc": "2.0",
		"method": "configuration.import",
		"params": {
			"format": "xml",
			"rules": {
				"applications": {
						"createMissing": True,
						"deleteMissing": False
				},
				"templates": {
					"createMissing": True,
					"updateExisting": True
				},
				"screens": {
					"createMissing": True,
					"updateExisting": True
				},
				"valueMaps": {
					"createMissing": True,
					"updateExisting": False
				},
				"graphs": {
					"createMissing": True,
					"updateExisting": True,
					"deleteMissing": True
				},
				"triggers": {
					"createMissing": True,
					"updateExisting": True,
					"deleteMissing": True
				},
				"items": {
					"createMissing": True,
					"updateExisting": True,
					"deleteMissing": True
				}
			},
			"source": content
		},
		"auth": auth,
		"id": 1
	}
	res = zabbix_call(payload, zabbix_server)
	if 'result' in res :
		if res['result']:
			print('template import successfully')
	else :
		print('error in importing the template')
		print(res['error'])


def zabbix_get_template(auth, templatename, zabbix_server):
	'''Connect to zabbix server and get the id of the template.

	Args:
		auth          string   your authentication token
		templatename  string   the name of the template
		zabbix_server string   the ip of zabbix server

	Returns:
		the template id
	'''
	template_id = ''
	if auth != '':
		payload = {
    		"jsonrpc": "2.0",
    		"method": "template.get",
    		"params": {
    		    "output": "extend",
    		    "filter": {
    		        "host": [
    		            templatename
    		        ]
    		    }
    		},
    		"auth": auth,
    		"id": 1
		}
		res = zabbix_call(payload, zabbix_server)
		if 'result' in res :
			template_id = res['result'][0]['templateid']
		else:
			print(res['error'])
	return template_id


def zabbix_create_host(auth, hostname, hostip, host_group_id, template_id, zabbix_server):
	'''Create host and link template.

	Args:
		auth          string    your authentication token
		hostname      string    the name of the host to be created
		hostip        string    the ip of the host to be created
		host_group_id string    the id of host group
		template_id   string    the id of template
		zabbix_server string    the ip of zabbix server
	'''
	host_id = ''
	payload = {
	    "jsonrpc": "2.0",
	    "method": "host.create",
	    "params": {
	        "host": hostname,
	        "interfaces": [
	            {
	                "type": 1,
	                "main": 1,
	                "useip": 1,
	                "ip": hostip,
	                "dns": "",
	                "port": "10050"
	            }
	        ],
	        "groups": [
	            {
	                "groupid": host_group_id
	            }
	        ],
	        "templates": [
	            {
	                "templateid": template_id
	            }
	        ]		        
	    },
	    "auth": auth,
	    "id": 1
	}
	res = zabbix_call(payload, zabbix_server)
	if 'result' in res :
		host_id = res['result']['hostids'][0]
		print("create host:", hostname , "successfully")
	else:
		print('error in creating host:', hostname)
		print(res['error'])


def parseArg(argv):
	'''Parse python command line arguments and return arguments.

	Args:
		argv   string  command line arguments

	Returns:
		zabbix_server  string  the ip of zabbix server
		zabbix_user    string  the user of zabbix, default: Admin
		zabbix_pwd     string  password for user, default: zabbix
	'''
	zabbix_user = 'Admin'
	zabbix_pwd = 'zabbix'
	zabbix_server = ''
	try:
		opts, args = getopt.getopt(argv,"hz:u:p:",["help"])
	except getopt.GetoptError:
		print('invalid option\nplease use python create_host_repl.py --help for more information\n')
		sys.exit(2)
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print('usage:\n  python create_host_repl.py -z <zabbix_server_ip> -u <zabbix_user> -p <zabbix_password>\n')
			print('  if no user and password input, then user:Admin and password:zabbix will be used by default')
			sys.exit()
		elif opt == '-z':
			zabbix_server = arg
		elif opt == '-u':
			zabbix_user = arg
		elif opt == '-p':
			zabbix_pwd = arg
	return zabbix_server, zabbix_user, zabbix_pwd


# the main method
def main(argv):
	zabbix_server, user, pwd = parseArg(argv)
	if zabbix_server == '':
		print('invalid input!\nplease check and use python create_host_repl.py --help for more information\n')
		sys.exit(2)

	auth = zabbix_auth(user, pwd, zabbix_server)
	if auth == '':
		print('\nzabbix server authentication failed\n')
		sys.exit()

	#import template
	zabbix_import_template(auth, './mongodb_repl_arbiter.xml', zabbix_server)
	zabbix_import_template(auth, './mongodb_repl_notarbiter.xml', zabbix_server)
	arbiter_template_id = zabbix_get_template(auth, 'Template MongoDB Repl Arbiter', zabbix_server)	
	notarbiter_template_id = zabbix_get_template(auth, 'Template MongoDB Repl Notarbiter', zabbix_server)

	#read the json file
	with open('./repl.json', 'r') as f:
		repl = json.load(f)
	members = repl['members']
	name = repl['name']

	#create host group 
	group_id = zabbix_create_group(auth, 'Mongodb Repl ' + name, zabbix_server)
	hostname_first = 'repl_'


	if group_id != '' and arbiter_template_id != '' and notarbiter_template_id != '':
		for m in members:
			mongo_ip = m['ip']
			role = m['role']
			hostname = hostname_first + m['ip']
			if role == 'not arbiter':
				zabbix_create_host(auth, hostname, mongo_ip, group_id, notarbiter_template_id, zabbix_server)
			if role == 'arbiter':
				zabbix_create_host(auth, hostname, mongo_ip, group_id, arbiter_template_id, zabbix_server)
	else:
		print("can not complete creating all the hosts in your replica set, please check and try again")



if __name__ == '__main__':
	main(sys.argv[1:])
