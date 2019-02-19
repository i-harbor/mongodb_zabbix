#!/usr/bin/python36
#-*- coding: utf-8 -*-

'''
'@file mongodb_sh_auth.py
'@author liyunting
'@version 1
'@lastModify: 2019-02-17 15:38
'
'''

import json
import sys, getopt
import subprocess
from pymongo import *
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure


#the prefix of hosts that are created
hostname_first = 'sh_'


def getServerStatus(ip, port, user, pwd):
	'''Get the serverStatus of the mongos or mongod instance.

	Try to get the information of mongodb server by command.
	You can refer to MongoDB manual for more details about serverStatus command.

	Args:
		ip    string   the server ip that the mongos or mongod instance is located
		port  int      the port that is used by the monhos or mongod instance
		user  string   the user of mongodb
		pwd   string   the password of mongodb

	Returns:
		status code    int    0/1/2
		server_status  dict   the status result
	'''
	server_status = {}
	try:
		client = MongoClient(ip, port)
		db = client.admin
		is_master = db.command('ismaster')
		db.authenticate(user, pwd)
		server_status = db.command('serverStatus')
		return 0, server_status
	except ConnectionFailure:
		return 1, server_status
	except OperationFailure:
		return 2, server_status


def getArbiterStatus(ip, port):
	'''Get the status of an arbiter.

	Try to get the information of mongodb server by command.
	You can refer to MongoDB manual for more details about ismaster command.

	Args:
		ip    string   the ip of the arbiter
		port  int      the port that is used by the arbiter

	Returns:
		status code    int    0/1
	'''
	try:
		client = MongoClient(ip, port)
		db = client.admin
		is_master = db.command('ismaster')
		return 0
	except ConnectionFailure:
		return 1


def parseArg(argv):
	'''Parse python command line arguments and return arguments.

	Args:
		argv   string  command line arguments

	Returns:
		zabbix_server  string  the ip of zabbix server
		user           string  the user of mongodb
		pwd            string  the password of mongodb
	'''
	zabbix_server = ''
	user = ''
	pwd = ''
	try:
		opts, args = getopt.getopt(argv,"hz:u:d:",["help"])
	except getopt.GetoptError:
		print('invalid option\nplease use python mongodb_sh_auth.py --help for more information\n')
		sys.exit(2)
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print('usage:\n  python mongodb_sh_auth.py -z <zabbix_server_ip> -u <mongodb_user> -d <mongodb_password>\n')
			sys.exit()
		elif opt == '-z':
			zabbix_server = arg
		elif opt == '-u':
			user = arg
		elif opt == '-d':
			pwd = arg
	return zabbix_server, user, pwd


def send_value(item_key, zabbix_server, item_value, zabbix_host):
	'''Send certain value to a zabbix host by zabbix_sender process.

	Args:
		item_key      string   the key of a certain zabbix item
		zabbix_server string   the ip of zabbix server
		item_value    string   the value to be send to zabbix server
		zabbix_host   string   the hostname in zabbix
	'''
	send = subprocess.getstatusoutput('zabbix_sender -z ' + zabbix_server + ' -s ' + zabbix_host + ' -k ' + item_key + ' -o ' + item_value)
	print(send[1])
	if send[0] == 0:
		print('\n', item_key, zabbix_host, 'send successfully\n')
	else:
		print('\n', item_key, zabbix_host, 'failed to send\n')


def process_notarbiter(ip, port, zabbix_server, hostname, component, user, pwd):
	'''Get the status data from a not arbiter component(e.g. mongos, config, shard1 not arbiter) of the sharded cluster and send them to zabbix server.

	And you can refer to MongoDB manual for more details about the returns of serverStatus command.

	Args:
		ip            string   the ip of mongo server
		port          int      the port of mongo server
		zabbix_server string   the ip of zabbix server
		hostname      string   the host name in zabbix
		component     string   the name of the component(e.g. mongos, config, shard0)
		user          string   the user of mongodb
		pwd           string   the password of mongodb
	'''
	status_result =  getServerStatus(ip, port, user, pwd)
	if status_result[0]  == 0:
		send_value(component + '.alive', zabbix_server, str(1), hostname)
		send_value(component + '.conn.current', zabbix_server, str(status_result[1]['connections']['current']), hostname)
		send_value(component + '.network.in', zabbix_server, str(status_result[1]['network']['bytesIn']), hostname)
		send_value(component + '.network.out', zabbix_server, str(status_result[1]['network']['bytesOut']), hostname)
		send_value(component + '.op.delete', zabbix_server, str(status_result[1]['opcounters']['delete']), hostname)
		send_value(component + '.op.getmore', zabbix_server, str(status_result[1]['opcounters']['getmore']), hostname)
		send_value(component + '.op.insert', zabbix_server, str(status_result[1]['opcounters']['insert']), hostname)
		send_value(component + '.op.query', zabbix_server, str(status_result[1]['opcounters']['query']), hostname)
		send_value(component + '.op.update', zabbix_server, str(status_result[1]['opcounters']['update']), hostname)
		send_value(component + '.uptime', zabbix_server, str(status_result[1]['uptime']), hostname)
		send_value(component + '.version', zabbix_server, str(status_result[1]['version']), hostname)
	elif status_result[0]  == 1:
		send_value(component + '.alive', zabbix_server, str(0), hostname)
		print('Cound not connect to the server', ip, str(port))
	else:
		print('\nCound not get the server status', ip, str(port))


def process_arbiter(ip, port, zabbix_server, hostname, component):
	'''Get the status data from an arbiter component of the sharded cluster and send them to zabbix server.

	Args:
		ip            string   the ip of mongo server
		port          int      the port of mongo server
		zabbix_server string   the ip of zabbix server
		hostname      string   the host name in zabbix
		component     string   the name of the component
	'''
	status =  getArbiterStatus(ip, port)
	if status  == 0:
		send_value(component + '.alive', zabbix_server, str(1), hostname)
	elif status  == 1:
		send_value(component + '.alive', zabbix_server, str(0), hostname)
		print('Cound not connect to the server', ip, str(port))


# the main method 
def main(argv):
	zabbix_server, user, pwd= parseArg(argv)
	if zabbix_server == '' or user == '' or pwd == '':
		print('invalid input!\nplease check and use python mongodb_sh_auth.py --help for more information\n')
		sys.exit(2)

	with open('/root/liyunting/cluster.json', 'r') as f:
		cluster = json.load(f)

	mongos_list = cluster["mongos"]
	config_list = cluster["config"]
	shard_list = cluster["shard"]

	for mongos in mongos_list:
		process_notarbiter(mongos['ip'], mongos['port'], zabbix_server, hostname_first + mongos['ip'], 'mongos', user, pwd)

	for config in config_list:
		process_notarbiter(config['ip'], config['port'], zabbix_server, hostname_first + config['ip'], 'config', user, pwd)

	for shard in shard_list:
		name = shard['name']
		members = shard['members']
		for m in members:
			if m['role'] == 'not arbiter':
				process_notarbiter(m['ip'], m['port'], zabbix_server, hostname_first + m['ip'], name, user, pwd)
			if m['role'] == 'arbiter':
				process_arbiter(m['ip'], m['port'], zabbix_server, hostname_first + m['ip'], name)


if __name__ == '__main__':
	main(sys.argv[1:])


