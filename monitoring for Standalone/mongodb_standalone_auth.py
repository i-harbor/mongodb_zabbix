#!/usr/bin/python
#-*- coding: utf-8 -*-

'''
'@file: mongodb_standalone_auth.py
'@author: liyunting
'@version: 2
'@lastModify: 2019-02-01 17:26
'
'''

import sys, getopt
import subprocess
from pymongo import *
from pymongo.errors import ConnectionFailure
from pymongo.errors import OperationFailure


#the name of your zabbix host
zabbix_host = 'mongo_server'


def getServerStatus(ip, port, user, pwd):
	'''Get the serverStatus of the mongod instance.

	Try to get the information of mongodb server by command.
	You can refer to MongoDB manual for more details about serverStatus command 

	Args:
		ip    string   the server ip that the mongod instance is located
		port  int      the port that is used by the mongod instance
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


def parseArg(argv):
	'''Parse python command line arguments and return arguments.

	Args:
		argv   string  command line arguments

	Returns:
		zabbix_server  string  the ip of zabbix server
		mongo_ip       string  the ip of mongodb server
		mongo_port     int     the port of mongodb
		user           string  the user of mongodb
		pwd            string  the password of mongodb
	'''
	zabbix_server = ''
	mongo_ip = ''
	mongo_port = ''
	user = ''
	pwd = ''
	try:
		opts, args = getopt.getopt(argv,"hz:m:p:u:d:",["help"])
	except getopt.GetoptError:
		print('invalid option\nplease use python mongodb_standalone_noauth.py --help for more information\n')
		sys.exit(2)
	for opt, arg in opts:
		if opt in ('-h', '--help'):
			print('usage:\n  python mongodb_standalone_noauth.py -z <zabbix_server_ip> -m <mongodb_ip> -p <mongodb_port> -u <mongodb_user> -d <mongodb_password>\n')
			sys.exit()
		elif opt == '-z':
			zabbix_server = arg
		elif opt == '-m':
			mongo_ip = arg
		elif opt == '-p':
			mongo_port = int(arg)
		elif opt == '-u':
			user = arg
		elif opt == '-d':
			pwd = arg
	return zabbix_server, mongo_ip, mongo_port, user, pwd


def send_value(item_key, zabbix_server, item_value):
	'''Send certain value to the zabbix host by zabbix_sender process.

	Args:
		item_key      string   the key of a certain zabbix item
		zabbix_server string   the ip of zabbix server
		item_value    string   the value to be send to zabbix server
	'''
	send = subprocess.getstatusoutput('zabbix_sender -z ' + zabbix_server + ' -s ' + zabbix_host + ' -k ' + item_key + ' -o ' + item_value)
	print(send[1])
	if send[0] == 0:
		print('\n', item_key, zabbix_host, 'send successfully\n')
	else:
		print('\n', item_key, zabbix_host, 'failed to send\n')


def process_mongodb(ip, port, zabbix_server, user, pwd):
	'''Get the status data from mongodb and send them to zabbix server.

	And you can refer to MongoDB manual for more details about the returns of serverStatus command.

	Args:
		ip            string   the ip of mongo server
		port          int      the port of mongo server
		zabbix_server string   the ip of zabbix server
		user          string   the user of mongodb
		pwd           string   the password of mongodb
	'''
	status_result =  getServerStatus(ip, port, user, pwd)
	if status_result[0]  == 0:
		send_value('mongo.alive', zabbix_server, str(1))
		send_value('mongo.conn.current', zabbix_server, str(status_result[1]['connections']['current']))
		send_value('mongo.conn.available', zabbix_server, str(status_result[1]['connections']['available']))
		send_value('mongo.mem.resident', zabbix_server, str(status_result[1]['mem']['resident']))
		send_value('mongo.network.in', zabbix_server, str(status_result[1]['network']['bytesIn']))
		send_value('mongo.network.out', zabbix_server, str(status_result[1]['network']['bytesOut']))
		send_value('mongo.op.delete', zabbix_server, str(status_result[1]['opcounters']['delete']))
		send_value('mongo.op.getmore', zabbix_server, str(status_result[1]['opcounters']['getmore']))
		send_value('mongo.op.insert', zabbix_server, str(status_result[1]['opcounters']['insert']))
		send_value('mongo.op.query', zabbix_server, str(status_result[1]['opcounters']['query']))
		send_value('mongo.op.update', zabbix_server, str(status_result[1]['opcounters']['update']))
		send_value('mongo.page_faults', zabbix_server, str(status_result[1]['extra_info']['page_faults']))
		send_value('mongo.uptime', zabbix_server, str(status_result[1]['uptime']))
		send_value('mongo.version', zabbix_server, str(status_result[1]['version']))
	elif status_result[0]  == 1:
		send_value('mongos.alive', zabbix_server, str(0))
		print('Cound not connect to the server', ip, str(port))
	else:
		print('\nCound not get the server status, please check your authentication', ip, str(port))


# the main method 
def main(argv):
	zabbix_server, mongo_ip, mongo_port, user, pwd = parseArg(argv)
	if zabbix_server == '' or mongo_ip == '' or mongo_port == '' or user == '' or pwd == '':
		print('invalid input!\nplease check and use python mongodb_standalone_noauth.py --help for more information\n')
		sys.exit(2)
	process_mongodb(mongo_ip, mongo_port, zabbix_server, user, pwd)


if __name__ == "__main__":
   main(sys.argv[1:])
