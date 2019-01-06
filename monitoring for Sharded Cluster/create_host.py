#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
'@file create_host.py
'@author liyunting
'@version 2
'@lastModify: 2019-01-05 17:03:02
'
'''

import json
import requests


#zabbix server ip
zabbix_server = '10.0.86.252'

#the cluster structure by ip
structure = {}


'''
'function: create_structure
'description: just use to help rebulid the cluster structure by ip
'parameter: componentList    list     the component of the cluster get from json file(e.g. mongos_list)
'           ident            int      the identification of this component
'the identification mapping relation:
'mongos -> 0
'config -> 1
'shard0 -> 2
'shard1 -> 3
'shard2 -> 4
'shard3 -> 5   
'''
def create_structure(componentList, ident):
	for c in componentList:
		ip = c['ip']
		if ip in structure:
			structure[ip].append(ident)
		else:
			structure[ip] = [ident]


'''
'function: zabbix_call
'description: call zabbix web api by json-rpc
'parameter: payload   dict   the parameter to be passed  
'return: the request response object  
'''
def zabbix_call(payload):
	url = "http://" + zabbix_server + "/zabbix/api_jsonrpc.php"
	headers = {'content-type': 'application/json'}
	response = requests.post(url, data=json.dumps(payload), headers=headers).json()
	return response


'''
'function: zabbix_auth
'description: connect to zabbix server and authenticate
'parameter: user   string   the zabbix server username
'           pwd    string   the zabbix server password 
'return: the authentication token
'''
def zabbix_auth(user, pwd):
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
	res = zabbix_call(payload) 
	if 'result' in res :
		auth = res['result']
	else:
		print(res['error'])
	return auth


'''
'function: zabbix_create_group
'description: connect to zabbix server and create host group
'parameter: auth         string   your authentication token
'           groupname    string   the name of the hostgroup
'return:the host group id 
'''
def zabbix_create_group(auth, groupname):
	host_group_id = ''
	if auth != '':
		#create host group
		payload = {
    		"jsonrpc": "2.0",
    		"method": "hostgroup.create",
    		"params": {
    		    "name": groupname
    		},
   	 		"auth": auth,
    		"id": 1
		}
		res = zabbix_call(payload)
		if 'result' in res :
			host_group_id = res['result']['groupids'][0]
		else:
			print(res['error'])
	return host_group_id


'''
'function: zabbix_import_template
'description: connect to zabbix server and import template
'parameter: auth         string   your authentication token
'           filepath     string   the whole path of the xml file(e.g. './example.xml')
'''
def zabbix_import_template(auth, filepath):
	if auth != '':
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
		res = zabbix_call(payload)
		if 'result' in res :
			if res['result']:
				print('template import successfully')
		else:
			print(res['error'])


'''
'function: zabbix_get_template
'description: connect to zabbix server and get template
'parameter: auth          string   your authentication token
'           templatename  string   the name of the template
'return:the template id 
'''
def zabbix_get_template(auth, templatename):
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
		res = zabbix_call(payload)
		if 'result' in res :
			template_id = res['result'][0]['templateid']
		else:
			print(res['error'])
	return template_id


'''
'function: zabbix_create_host
'description: create host 
'parameter: auth          string    your authentication token
'           hostname      string    the name of the host
'           hostip        string    the ip of the host
'			host_group_id string    the id of group 
'return: host id
'''
def zabbix_create_host(auth, hostname, hostip, host_group_id):
	host_id = ''
	if auth != '' and host_group_id != '':
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
		res = zabbix_call(payload)
		if 'result' in res :
			host_id = res['result']['hostids'][0]
			print("create", hostname , "successfully")
		else:
			print(res['error'])
	return host_id


'''
'function: zabbix_link_template
'description: connect to zabbix server and link templates to host
'parameter: auth          string   your authentication token
'           template  string   the id of templates to be linked
'           hostid        string   the id of host
'''
def zabbix_link_template(auth, template, hostid):
	if auth != '':
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
	        			"templateid": template
	        		}
	        	]
	    	},
	    	"auth": auth,
	 	   	"id": 1
		}
		res = zabbix_call(payload)
		if 'result' in res :
			print("link", template, "successfully")
		else:
			print(res['error'])


#the main method
def main():
	with open('./cluster_structure.json', 'r') as f:
		cluster = json.load(f)

	mongos_list = cluster["mongos"]
	config_list = cluster["config"]
	shard_list = cluster["shard"]

	#parse the json file
	#create the cluster structure by ip
	create_structure(mongos_list, 0)
	create_structure(config_list, 1)
	i = 2
	for shard in shard_list:
		members = shard['members']
		create_structure(members, i)
		i = i + 1

	#login zabbix server
	auth = zabbix_auth("Admin","zabbix")
	#create host group
	host_group = zabbix_create_group(auth, 'Mongodb Sharded Cluster')
	#import template
	zabbix_import_template(auth, './mongos.xml')
	zabbix_import_template(auth, './config.xml')
	zabbix_import_template(auth, './shard0.xml')
	zabbix_import_template(auth, './shard1.xml')
	zabbix_import_template(auth, './shard2.xml')
	zabbix_import_template(auth, './shard3.xml')
	#get template id
	templ_id = []
	templ_name = ['Template for mongos v1', 'Template for config mongod v1', 'Template for shard0 mongod v1', 'Template for shard1 mongod v1', 'Template for shard2 mongod v1', 'Template for shard3 mongod v1']
	for templ in templ_name:
		tid = zabbix_get_template(auth, templ)
		templ_id.append(tid)
	#create host and link templates
	j = 0
	for ip in structure:
		struclist = structure[ip]
		hostid =zabbix_create_host(auth, 'mongoserver_' + str(j), ip, host_group)
		for t in struclist:
			zabbix_link_template(auth, templ_id[t], hostid)
		j = j + 1





if __name__ == '__main__':
	main()