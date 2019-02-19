#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
'@file: create_host_sh.py
'@author: liyunting
'@version: 2
'@lastModify: 2019-02-17 14:30
'
'''

import json
import requests
import getopt
import sys
from collections import defaultdict


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
		print('invalid option\nplease use python create_host_sh.py --help for more information\n')
		sys.exit(2)
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print('usage:\n  python create_host_sh.py -z <zabbix_server_ip> -u <zabbix_user> -p <zabbix_password>\n')
			print('  if no user and password input, then user:Admin and password:zabbix will be used by default')
			sys.exit()
		elif opt == '-z':
			zabbix_server = arg
		elif opt == '-u':
			zabbix_user = arg
		elif opt == '-p':
			zabbix_pwd = arg
	return zabbix_server, zabbix_user, zabbix_pwd


def parseCluster(filepath):
	'''Parse the cluster.json file to find out all the hosts to be created.

	Args:
		filepath   string   the path of the json file that describes the sharded cluster

	Returns:
		hosts      dict     the information of hosts to be created
		shards     list     the names of all the shards in the cluster(e.g. ['shard0', 'shard1', 'shard2', 'shard3'])
	'''
	hosts = defaultdict(list)
	shards = []
	with open(filepath, 'r') as f:
		cluster = json.load(f)
	# get mongos, config and all the shard
	mongos_list = cluster['mongos']
	config_list = cluster['config']
	shard_list = cluster['shard']

	for mongos in mongos_list:
		m_ip = mongos['ip']
		hosts[m_ip].append('mongos')

	for config in config_list:
		c_ip = config['ip']
		hosts[c_ip].append('config')

	for shard in shard_list:
		s_name = shard['name']
		shards.append(s_name)
		s_mem = shard['members']
		for m in s_mem:
			m_ip = m['ip']
			m_role = m['role']
			hosts[m_ip].append(s_name + ' ' + m_role)
	return hosts, shards


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


def zabbix_import_template(auth, content, zabbix_server):
	'''Connect to zabbix server and import the MongoDB template.

	Args:
		auth          string   your authentication token
		content       string   the content of the template file
		zabbix_server string   the ip of zabbix server
	'''
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


def zabbix_create_host(auth, hostname, hostip, host_group_id, zabbix_server):
	'''Create host in zabbix.

	Args:
		auth          string    your authentication token
		hostname      string    the name of the host
		hostip        string    the ip of the host
		host_group_id string    the id of host group
		zabbix_server string    the ip of zabbix server

	Returns:
		host_id      string   the id of the host
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
	return host_id


def zabbix_link_template(auth, templateid, hostid, zabbix_server):
	''' Connect to zabbix server and link templates to the host.

	Args:
		auth          string     the authentication token
		templateid    string     the id of template to be linked
		hostid        string     the id of the host
		zabbix_server string     the ip of the zabbix server
	'''
	payload = {
		"jsonrpc": "2.0",
		"method": "host.massadd",
		"params": {
			"hosts": [
				{
					"hostid": hostid
				}
			],
			"templates": [
				{
					"templateid": templateid
				}
			]
		},
		"auth": auth,
		"id": 1
	}
	res = zabbix_call(payload, zabbix_server)
	if 'result' in res :
		print("link template:", templateid, "for host:", hostid, "successfully")
	else:
		print("error in linking template")
		print(res['error'])


def main(argv):
	zabbix_server, user, pwd = parseArg(argv)
	if zabbix_server == '':
		print('invalid input!\nplease check and use python create_host_sh.py --help for more information\n')
		sys.exit(2)

	auth = zabbix_auth(user, pwd, zabbix_server)
	if auth == '':
		print('\nzabbix server authentication failed\n')
		sys.exit()

	# create host group
	groupname = 'Mongodb Sh Cluster'
	group_id = zabbix_create_group(auth, groupname, zabbix_server)
	if group_id == '':
		print('can not complete creating all the hosts in your sharded cluster, please check and try again')
		sys.exit()

	# get the structure of sharded cluster
	hosts, shards= parseCluster('./cluster.json')
	# import template
	template = {}
	with open('./sh_mongos.xml', 'r') as f1: 
		zabbix_import_template(auth, f1.read(), zabbix_server)
	mongos_template_id = zabbix_get_template(auth, 'Template MongoDB Sh Mongos', zabbix_server)
	template['mongos'] = mongos_template_id
	with open('./sh_config.xml', 'r') as f2: 
		zabbix_import_template(auth, f2.read(), zabbix_server)
	config_template_id = zabbix_get_template(auth, 'Template MongoDB Sh Config', zabbix_server)
	template['config'] = config_template_id
	with open('./sh_shard_na.xml','r') as f3:
		shard_na = f3.read()
	with open('./sh_shard_a.xml','r') as f4:
		shard_a = f4.read()
	for sh in shards:
		sh_temp1 = shard_na.replace('shard', sh)
		sh_content1 = sh_temp1.replace('Shard', sh.capitalize())
		zabbix_import_template(auth, sh_content1, zabbix_server)
		sh_template_id = zabbix_get_template(auth, 'Template MongoDB Sh ' + sh.capitalize() + ' Notarbiter', zabbix_server)
		template[sh + ' not arbiter'] = sh_template_id
		sh_temp2 = shard_a.replace('shard', sh)
		sh_content2 = sh_temp2.replace('Shard', sh.capitalize())
		zabbix_import_template(auth, sh_content2, zabbix_server)
		sh_template_id = zabbix_get_template(auth, 'Template MongoDB Sh ' + sh.capitalize() + ' Arbiter', zabbix_server)
		template[sh + ' arbiter'] = sh_template_id

	# create hosts and link templates
	try:
		for host in hosts:
			hostname = 'sh_' + host
			host_id = zabbix_create_host(auth, hostname, host, group_id, zabbix_server)
			if host_id != '':
				for component in hosts[host]:
					zabbix_link_template(auth, template[component], host_id, zabbix_server)
	except Exception as e:
		print(e)
		print('can not complete creating all the hosts in your sharded cluster, please check and try again')


if __name__ == '__main__':
	main(sys.argv[1:])
