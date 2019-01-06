#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
'@file mongodb_zabbix_noauth.py
'@author liyunting
'@version 1
'@lastModify: 2019-01-05 17:00:25
'
'''

import json
import subprocess
from pymongo import *
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure


#zabbix server ip
zabbix_server = '10.0.86.252'

#zabbix_host
zabbix_host = {'10.0.200.100' : 'mongoserver_0', '10.0.200.101' : 'mongoserver_1','10.0.200.102' : 'mongoserver_2', '10.0.200.103' : 'mongoserver_3'}


'''
'function: send_value
'description: send certain value to the zabbix host by zabbix_sender process 
'parameter: item_key    string   the key of a certain zabbix item 
'           ip          string   the corresponding server ip of the zabbix host
'           item_value  string   the value to be send to zabbix server          
''
'''
def send_value(item_key, ip, item_value):
	send = subprocess.getstatusoutput('zabbix_sender -z ' + zabbix_server + ' -s ' + zabbix_host[ip] + ' -k ' + item_key + ' -o ' + item_value)
	print(send[1])
	if send[0] == 0:
		print(item_key, ip , zabbix_host[ip], 'send successfully')
	else:
		print(item_key, ip , zabbix_host[ip], 'failed to send')


'''
'function: getServerStatus
'description: get the serverStatus of the mongod or mongos instance 
'parameter: ip    string   the server ip that the mongod or mongos instance is located 
'           port  int      the port that is used by the mongod or mongos instance 
'return: status code and result dict       
'''
def getServerStatus(ip, port):
	server_status = {}
	try:
		client = MongoClient(ip, port)
		db = client.admin
		is_master = db.command('ismaster')
		server_status = db.command('serverStatus')
		return 0, server_status
	except ConnectionFailure:
		return 1, server_status
	except OperationFailure:
		return 2, server_status


'''
'function: getRSStatus
'description: get the replica set's status 
'parameter: ip    string   a server ip that a member's mongod instance is located 
'           port  int      the port that is used by the mongod instance  
'return status code and result dict    
'''
def getRSStatus(ip, port):
	rs_status = {}
	try:
		client = MongoClient(ip, port)
		db = client.admin
		is_master = db.command('ismaster')
		rs_status = db.command('replSetGetStatus')
		return 0, rs_status
	except ConnectionFailure:
		return 1, rs_status
	except OperationFailure:
		return 2, rs_status


'''
'function: process_mongos
'description: process a mongos instance in cluster
'parameter: ip    string   the server ip that the mongos instance is located
'           port  int   the port that is used by the mongos instance     
'''
def process_mongos(ip, port):
	status_result =  getServerStatus(ip, port)
	if status_result[0]  == 0:
		send_value('mongos.alive', ip, str(1))
		send_value('mongos.connections.current', ip, str(status_result[1]['connections']['current']))
		send_value('mongos.connections.available', ip, str(status_result[1]['connections']['available']))
		send_value('mongos.cursor.open', ip, str(status_result[1]['metrics']['cursor']['open']['total']))
		send_value('mongos.cursor.timeout', ip, str(status_result[1]['metrics']['cursor']['timedOut']))
		send_value('mongos.memory.resident', ip, str(status_result[1]['mem']['resident']))
		send_value('mongos.memory.virtual', ip, str(status_result[1]['mem']['virtual']))
		send_value('mongos.network.in', ip, str(status_result[1]['network']['bytesIn']))
		send_value('mongos.network.out', ip, str(status_result[1]['network']['bytesOut']))
		send_value('mongos.op.delete', ip, str(status_result[1]['opcounters']['delete']))
		send_value('mongos.op.getmore', ip, str(status_result[1]['opcounters']['getmore']))
		send_value('mongos.op.insert', ip, str(status_result[1]['opcounters']['insert']))
		send_value('mongos.op.query', ip, str(status_result[1]['opcounters']['query']))
		send_value('mongos.op.update', ip, str(status_result[1]['opcounters']['update']))
		send_value('mongos.page_faults', ip, str(status_result[1]['extra_info']['page_faults']))
		send_value('mongos.uptime', ip, str(status_result[1]['uptime']))
	elif status_result[0]  == 1:
		send_value('mongos.alive', ip, str(0))
		print('Cound not connect to the server', ip, str(port))
	else:
		print('\nCound not get the server status', ip, str(port))


'''
'function: process_mongod
'description: process a mongod instance in cluster
'parameter: ip    string   the server ip that the mongod instance is located
'           port  int      the port that is used by the mongod instance
'           name  string   the name of the mongod in cluster(e.g. config, shard0)  
'''
def process_mongod(ip, port, name):
	status_result =  getServerStatus(ip, port)
	if status_result[0]  == 0:
		send_value(name + '.connections.available', ip, str(status_result[1]['connections']['available']))
		send_value(name + '.connections.current', ip, str(status_result[1]['connections']['current']))
		send_value(name + '.cursor.open', ip, str(status_result[1]['metrics']['cursor']['open']['total']))
		send_value(name + '.cursor.timeout', ip, str(status_result[1]['metrics']['cursor']['timedOut']))
		send_value(name + '.doc.delete', ip, str(status_result[1]['metrics']['document']['deleted']))
		send_value(name + '.doc.insert', ip, str(status_result[1]['metrics']['document']['inserted']))
		send_value(name + '.doc.return', ip, str(status_result[1]['metrics']['document']['returned']))
		send_value(name + '.doc.update', ip, str(status_result[1]['metrics']['document']['updated']))
		send_value(name + '.lockqueue.read', ip, str(status_result[1]['globalLock']['currentQueue']['readers']))
		send_value(name + '.lockqueue.total', ip, str(status_result[1]['globalLock']['currentQueue']['total']))
		send_value(name + '.lockqueue.write', ip, str(status_result[1]['globalLock']['currentQueue']['writers']))
		send_value(name + '.memory.resident', ip, str(status_result[1]['mem']['resident']))
		send_value(name + '.memory.virtual', ip, str(status_result[1]['mem']['virtual']))
		send_value(name + '.network.in', ip, str(status_result[1]['network']['bytesIn']))
		send_value(name + '.network.out', ip, str(status_result[1]['network']['bytesOut']))
		send_value(name + '.op.delete', ip, str(status_result[1]['opcounters']['delete']))
		send_value(name + '.op.getmore', ip, str(status_result[1]['opcounters']['getmore']))
		send_value(name + '.op.insert', ip, str(status_result[1]['opcounters']['insert']))
		send_value(name + '.op.query', ip, str(status_result[1]['opcounters']['query']))
		send_value(name + '.op.update', ip, str(status_result[1]['opcounters']['update']))
		send_value(name + '.oprepl.delete', ip, str(status_result[1]['opcountersRepl']['delete']))
		send_value(name + '.oprepl.insert', ip, str(status_result[1]['opcountersRepl']['insert']))
		send_value(name + '.oprepl.update', ip, str(status_result[1]['opcountersRepl']['update']))
		send_value(name + '.page_faults', ip, str(status_result[1]['extra_info']['page_faults']))
		send_value(name + '.scan.objects', ip, str(status_result[1]['metrics']['queryExecutor']['scannedObjects']))
		send_value(name + '.uptime', ip, str(status_result[1]['uptime']))
	elif status_result[0]  == 1:
		send_value(name + '.alive', ip, str(0))
		print('Cound not connect to the server', ip, str(port))
	else:
		print('\nCound not get the server status', ip, str(port))



'''
'function: process_alivestatus
'description: process a replica set, get the alive status of all the members and send
'parameter: ip    string   the server ip that the mongod instance is located
'           port  int      the port that is used by the mongod instance  
'           name  string   the name of the replica set(e.g. config, shard0) 
'return: status code     
'''
def process_alivestatus(ip, port, name):
	nodemap = {'ip100': '10.0.200.100', 'ip101': '10.0.200.101', 'ip102': '10.0.200.102', 'ip103': '10.0.200.103'}
	alivestatus = getRSStatus(ip, port)
	if alivestatus[0] == 0:
		members = alivestatus[1]['members']
		for m in members:
			mname = m['name']
			health = m['health']
			mip = nodemap[mname.split(':')[0]]
			send_value(name + '.alive', mip, str(health))
	elif alivestatus[0] == 1:
		send_value(name + '.alive', ip, str(0))
	else:
		print('\nCound not get the server status', ip, str(port))
	return alivestatus[0]


# the main method 
def main():
	with open('cluster_structure.json', 'r') as f:
		cluster = json.load(f)

	mongos_list = cluster["mongos"]
	config_list = cluster["config"]
	shard_list = cluster["shard"]

	for mongos in mongos_list:
		process_mongos(mongos['ip'], mongos['port'])

	for config in config_list:
		config_rs = process_alivestatus(config['ip'], config['port'], 'config')
		if config_rs == 0:
			break

	for shard in shard_list:
		name = shard['name']
		members = shard['members']
		for m in members:
			shard_rs = process_alivestatus(m['ip'], m['port'], name)
			if shard_rs == 0:
				break

	for config in config_list:
		process_mongod(config['ip'], config['port'], 'config')

	for shard in shard_list:
		name = shard['name']
		members = shard['members']
		for m in members:
			process_mongod(m['ip'], m['port'], name)





if __name__ == '__main__':
	main()



	

