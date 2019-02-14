#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
'@file: mongodb_standalone_noauth.py
'@author: liyunting
'@version: 2
'@lastModify: 2019-02-14 14:48
'
'''

import sys, getopt
import subprocess
from pymongo import *
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure

# the prefix of host that is created
hostname_first = 'mongo_'

def getServerStatus(ip, port):
	'''Get the serverStatus of the mongod instance.

	Try to get the information of mongodb server by command.
	You can refer to MongoDB manual for more details about serverStatus command 

	Args:
		ip    string   the server ip that the mongod instance is located
		port  int      the port that is used by the mongod instance

	Returns:
		status code    int    0/1/2
		server_status  dict   the status result
	'''
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


def parseArg(argv):
	'''Parse python command line arguments and return arguments.

	Args:
		argv   string  command line arguments

	Returns:
		zabbix_server  string  the ip of zabbix server
		mongo_ip       string  the ip of mongodb server
		mongo_port     int     the port of mongodb
	'''
	zabbix_server = ''
	mongo_ip = ''
	mongo_port = ''
	try:
		opts, args = getopt.getopt(argv,"hz:m:p:",["help"])
	except getopt.GetoptError:
		print('invalid option\nplease use python mongodb_standalone_noauth.py --help for more information\n')
		sys.exit(2)
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print('usage:\n  python mongodb_standalone_noauth.py -z <zabbix_server_ip> -m <mongodb_ip> -p <mongodb_port>\n')
			sys.exit()
		elif opt == '-z':
			zabbix_server = arg
		elif opt == '-m':
			mongo_ip = arg
		elif opt == '-p':
			mongo_port = int(arg)
	return zabbix_server, mongo_ip, mongo_port


def send_value(item_key, zabbix_server, item_value, zabbix_host):
	'''Send certain value to the zabbix host by zabbix_sender process.

	Args:
		item_key      string   the key of a certain zabbix item
		zabbix_server string   the ip of zabbix server
		item_value    string   the value to be send to zabbix server
		zabbix_host   string   the hostname of the server in zabbix
	'''
	send = subprocess.getstatusoutput('zabbix_sender -z ' + zabbix_server + ' -s ' + zabbix_host + ' -k ' + item_key + ' -o ' + item_value)
	print(send[1])
	if send[0] == 0:
		print('\n', item_key, zabbix_host, 'send successfully\n')
	else:
		print('\n', item_key, zabbix_host, 'failed to send\n')


def process_mongodb(ip, port, zabbix_server, hostname):
	'''Get the status data from mongodb and send them to zabbix server.

	And you can refer to MongoDB manual for more details about the returns of serverStatus command.

	Args:
		ip            string   the ip of mongo server
		port          int      the port of mongo server
		zabbix_server string   the ip of zabbix server
		hostname      string   the hostname of mongo server in zabbix
	'''
	status_result =  getServerStatus(ip, port)
	if status_result[0]  == 0:
		send_value('mongo.alive', zabbix_server, str(1), hostname)
		send_value('mongo.conn.current', zabbix_server, str(status_result[1]['connections']['current']), hostname)
		send_value('mongo.conn.available', zabbix_server, str(status_result[1]['connections']['available']), hostname)
		send_value('mongo.mem.resident', zabbix_server, str(status_result[1]['mem']['resident']), hostname)
		send_value('mongo.network.in', zabbix_server, str(status_result[1]['network']['bytesIn']), hostname)
		send_value('mongo.network.out', zabbix_server, str(status_result[1]['network']['bytesOut']), hostname)
		send_value('mongo.op.delete', zabbix_server, str(status_result[1]['opcounters']['delete']), hostname)
		send_value('mongo.op.getmore', zabbix_server, str(status_result[1]['opcounters']['getmore']), hostname)
		send_value('mongo.op.insert', zabbix_server, str(status_result[1]['opcounters']['insert']), hostname)
		send_value('mongo.op.query', zabbix_server, str(status_result[1]['opcounters']['query']), hostname)
		send_value('mongo.op.update', zabbix_server, str(status_result[1]['opcounters']['update']), hostname)
		send_value('mongo.page_faults', zabbix_server, str(status_result[1]['extra_info']['page_faults']), hostname)
		send_value('mongo.uptime', zabbix_server, str(status_result[1]['uptime']), hostname)
		send_value('mongo.version', zabbix_server, str(status_result[1]['version']), hostname)
	elif status_result[0]  == 1:
		send_value('mongo.alive', zabbix_server, str(0), hostname)
		print('Cound not connect to the server', ip, str(port))
	else:
		print('\nCound not get the server status', ip, str(port))


# the main method 
def main(argv):
	zabbix_server, mongo_ip, mongo_port = parseArg(argv)
	if zabbix_server == '' or mongo_ip == '' or mongo_port == '':
		print('invalid input!\nplease check and use python mongodb_standalone_noauth.py --help for more information\n')
		sys.exit(2)
	process_mongodb(mongo_ip, mongo_port, zabbix_server, hostname_first + mongo_ip)
		

if __name__ == "__main__":
	main(sys.argv[1:])
