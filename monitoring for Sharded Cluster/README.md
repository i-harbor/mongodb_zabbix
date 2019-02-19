## 监控 MongoDB Sharded Cluster  

### 概述  
MongoDB Sharded Cluster 是 MongoDB 中最为复杂的一种集群部署方式。Sharded Cluster 不仅通过分片技术使得数据分布式地存储于多台机器上，并且通过副本技术为每台机器上的数据进行备份。可以说，Sharded Cluster 是一个综合了 sharding 和 replication 的复杂集群，可满足 MongoDB 数据量大量增长的需求，支持大规模数据集存储和高吞吐量操作。  

Sharded Cluster 的组成：  
+ **mongos**: mongos 区别于 mongod，仅作为一个的查询路由以接入客户端，为客户端应用访问集群提供一个接口，让整个集群看上去像单一数据库  
+ **config servers**: mongod，存储整个集群元数据和配置信息( MongoDB 4.0 要求 config servers 必须部署为副本集，且副本集成员中不得有仲裁点和历史快照点)  
+ **shard**: mongod，存储实际数据，每个 shard 存储一部分数据，shard 一般也部署为副本集以防止单点故障  

MongoDB Sharded Cluster 由于其本身结构和部署的复杂性，因而较之单节点和副本集，对其进行监控部署也更为复杂。对于 Sharded Cluster 的监控，我们基于 Zabbix 提出一套简单、快速、有效的监控部署方案  

适用范围：
+ MongoDB 4.0   
+ Zabbix 4.0  

配置内容： 
+ 监控端： Zabbix Server 
+ 被监控端：Zabbix Sender（使用 Zabbix Sender 主动向 Zabbix Server 定时发送批量数据，而不使用 Zabbix Agent）  

**注：Zabbix Server 和 Zabbix Sender 请自行配置，具体配置过程此处不再赘述，下文均默认 Zabbix Server 和 Zabbix Sender已完成配置**  

### 机制  
**监控端**（Zabbix Server）：读取 cluster.json 文件，分析集群结构，而后导入模板、创建主机组、创建各主机并根据集群结构信息分别为其链接一个或多个合适的模板  
**被监控端**（Zabbix Sender）：读取 cluster.json 文件，得到集群的各组成部分(mongos, config, shard)，根据每个组成部分中各个节点的 ip 和 port，分别连接到相应的 mongod 或 mongos 进程(若 MongoDB 需认证，则连接还需 user 和 password)，从 mongod 的非仲裁点或 mongos 获取 serverStatus 信息，而 mongod 的仲裁点只需判断是否存活，然后选取模板中各监控项所需数据，通过 Zabbix Sender 统一发送至 Zabbix Server 中对应主机及其监控项  

**注：Zabbix Sender 可安装在任意节点，不一定要安装在 MongoDB Sharded Cluster 的任何部署节点，只要能通过 ip 和 port 连接上集群的所有成员即可**

### 文件说明  

##### cluster.json  

+ 通过严格的 JSON 格式描述 Sharded Cluster 的结构信息，包括 mongos，config，shard 三个组成成分的相关信息  
+ mongos 需给出各 mongos 的 ip 和 port  
+ config 除 ip 和 port 外，还需给出 role(仅有 not arbiter / arbiter 两个取值)，role 用于描述该节点在副本集中是数据节点(not arbiter)还是仲裁点(arbiter)，由于 MongoDB 4.0 中 config servers 需部署为不含仲裁点的副本集，故 config 的所有节点的 role 一律取 not arbiter 值  
+ shard 包含多个分片信息，name 为分片名，members 为该分片的成员，分片一般也会部署为副本集，但若该分片部署为单节点，则 members 中只有一个成员，且该成员 role 也需取 not arbiter 值  

在示例一中，仅使用三个节点来部署一个 Sharded Cluster，集群有3个 mongos，config 为含3个数据点的副本集，有3个分片(shard1, shard2, shard3)，每个分片均为含2个数据点、1个仲裁点的副本集  
```
示例一：
{
	"mongos" : [
		{"ip" : "10.0.86.206", "port" : 20000},
		{"ip" : "10.0.86.204", "port" : 20000},
		{"ip" : "10.0.86.195", "port" : 20000}
	],
	"config" : [
		{"ip" : "10.0.86.206", "port" : 21000, "role" : "not arbiter"},
		{"ip" : "10.0.86.204", "port" : 21000, "role" : "not arbiter"},
		{"ip" : "10.0.86.195", "port" : 21000, "role" : "not arbiter"}
	],
	"shard" : [
		{
			"name" : "shard1",
			"members" : [
				{"ip" : "10.0.86.206", "port" : 27001, "role" : "not arbiter"},
				{"ip" : "10.0.86.204", "port" : 27001, "role" : "not arbiter"},
				{"ip" : "10.0.86.195", "port" : 27001, "role" : "arbiter"}
			]
		},		
		{
			"name" : "shard2",
			"members" : [
				{"ip" : "10.0.86.206", "port" : 27002, "role" : "not arbiter"},
				{"ip" : "10.0.86.204", "port" : 27002, "role" : "arbiter"},
				{"ip" : "10.0.86.195", "port" : 27002, "role" : "not arbiter"}
			]
		},
		{
			"name" : "shard3",
			"members" : [
				{"ip" : "10.0.86.195", "port" : 27003, "role" : "not arbiter"},
				{"ip" : "10.0.86.204", "port" : 27003, "role" : "not arbiter"},
				{"ip" : "10.0.86.206", "port" : 27003, "role" : "arbiter"}
			]
		}
	]
}
```

在示例二中，共使用11个节点部署 Sharded Cluster，集群有3个 mongos，config 为含3个数据点的副本集，有2个分片(myshard0, myshard1)，myshard0 是含3个数据点、1个仲裁点的副本集，myshard1 是一个单节点  
```
示例二：
{
	"mongos" : [
		{"ip" : "10.0.87.200", "port" : 20000},
		{"ip" : "10.0.87.201", "port" : 20000},
		{"ip" : "10.0.87.202", "port" : 20000}
	],
	"config" : [
		{"ip" : "10.0.87.203", "port" : 21000, "role" : "not arbiter"},
		{"ip" : "10.0.87.204", "port" : 21000, "role" : "not arbiter"},
		{"ip" : "10.0.87.205", "port" : 21000, "role" : "not arbiter"}
	],
	"shard" : [
		{
			"name" : "myshard0",
			"members" : [
				{"ip" : "10.0.87.206", "port" : 27017, "role" : "not arbiter"},
				{"ip" : "10.0.87.207", "port" : 27017, "role" : "not arbiter"},
				{"ip" : "10.0.87.208", "port" : 27017, "role" : "arbiter"},
				{"ip" : "10.0.87.209", "port" : 27017, "role" : "not arbiter"}
			]
		},		
		{
			"name" : "myshard1",
			"members" : [
				{"ip" : "10.0.87.210", "port" : 27017, "role" : "not arbiter"}
			]
		}
	]
}
```
##### sh_mongos.xml  

+ 适用于 MongoDB Sharded Cluster 中 mongos 的 Zabbix 模板  

##### sh_config.xml  

+ 适用于 MongoDB Sharded Cluster 中 config servers 的 Zabbix 模板  

##### sh_shard_na.xml  

+ 适用于 MongoDB Sharded Cluster 的分片中非仲裁点（单节点、副本集的主或备节点）的 Zabbix 模板  

##### sh_shard_a.xml  

+ 适用于 MongoDB Sharded Cluster 的分片中仲裁点的 Zabbix 模板  

##### create_host_sh.py  

+ 通过执行该 Python 文件可自动在 Zabbix Server 上完成模板导入、主机创建等系列过程  
+ 调用 Zabbix API，对于 API 的详细说明可参考 Zabbix 4.0 的官方文档 https://www.zabbix.com/documentation/4.0/manual/api  
+ 输入：Zabbix Server ip，Zabbix username，Zabbix password  
+ 完成内容：  
   [1] 读取同一目录下 cluster.json 文件，获取集群结构信息  
   [2] 在 Zabbix Server 中创建名为 'Mongodb Sh Cluster' 主机组  
   [3] 将同一目录下 sh_mongos.xml 和 sh_config.xml 中两个模板导入 Zabbix Server  
   [4] 根据集群中分片个数和分片名，修改 sh_shard_na.xml 和 sh_shard_a.xml 内容，导入相应数量的定制模板到 Zabbix Server  
   [5] 在该主机组中为每一个节点创建一个主机，主机名为前缀 sh_ 加上 ip，如 'sh_10.0.86.206'  
   [6] 创建主机时根据该节点上部署的集群成分，为主机链接上相应的各模板  

##### mongodb_sh_noauth.py  

+ 通过执行该 Python 文件可分别获取 MongoDB Sharded Cluster中各成分、成员的相关数据信息，并由 Zabbix Sender 发送至 Zabbix Server 中对应主机  
+ 输入：Zabbix Server ip  
+ 完成内容：  
   [1] 读取 cluster.json 文件，获取集群所有成分以及成员信息  
   [2] 通过 ip 和 port 连接到 mongos 或 mongod 进程，对于 mongod 通过 role 判断是否为仲裁点  
   [3] 若为 mongos，则获取 serverStatus 信息，从中取出模板中各监控项对应的数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  
   [4] 若为 mongod 且不是仲裁点，则获取 serverStatus 信息，从中取出模板中各监控项对应的数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  
   [5] 若为 mongod 且是仲裁点，则仅判断是否存活，将存活信息通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  

##### mongodb_sh_auth.py  

+ 通过执行该 Python 文件可分别获取 MongoDB Sharded Cluster中各成分、成员的相关数据信息，并由 Zabbix Sender 发送至 Zabbix Server 中对应主机  
+ 输入：Zabbix Server ip, MongoDB user, MongoDB password  
+ 完成内容：  
   [1] 读取 cluster.json 文件，获取集群所有成分以及成员信息  
   [2] 通过 ip 和 port 连接到 mongos 或 mongod 进程，对于 mongod 通过 role 判断是否为仲裁点  
   [3] 若为 mongos，则通过 MongoDB user 和 password 完成认证，再获取 serverStatus 信息，从中取出模板中各监控项对应的数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  
   [4] 若为 mongod 且不是仲裁点，则通过 MongoDB user 和 password 完成认证，再获取 serverStatus 信息，从中取出模板中各监控项对应的数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  
   [5] 若为 mongod 且是仲裁点，则无需认证，仅判断是否存活，将存活信息通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  

### 模板  

#### 模板1  Template MongoDB Sh Mongos  
模板名：Template MongoDB Sh Mongos  
模板所属主机组：Templates/Databases  
内容：Applications 1，Items 11，Triggers 1，Graphs 2  
模板设计参考了 Zabbix 官方提供的 MySQL 数据库模板（Template DB MySQL）  

##### Applications（应用）  
应用名：Mongos  
包含监控项：11  

##### Items (监控项)  
|监控项名称|监控项键|类型|所属应用|  
|:-----:|:---:|:---:|:---:|
|**Mongo status**|mongos.alive|Zabbix trapper| Mongos| 
|**Mongo current connections**|mongos.conn.current|Zabbix trapper| Mongos| 
|**Mongo bytes received per second**|mongos.network.in|Zabbix trapper| Mongos| 
|**Mongo bytes sent per second**|mongos.network.out|Zabbix trapper| Mongos| 
|**Mongo delete operations per second**|mongos.op.delete|Zabbix trapper| Mongos| 
|**Mongo getmore operations per second**|mongos.op.getmore|Zabbix trapper| Mongos| 
|**Mongo insert operations per second**|mongos.op.insert|Zabbix trapper| Mongos| 
|**Mongo query operations per second**|mongos.op.query|Zabbix trapper| Mongos| 
|**Mongo update operations per second**|mongos.op.update|Zabbix trapper| Mongos| 
|**Mongo uptime (s)**|mongos.uptime|Zabbix trapper| Mongos| 
|**Mongo version**|mongos.version|Zabbix trapper| Mongos| 

##### Triggers（触发器）
名称： Mongos is down  
表达式：{Template MongoDB Sh Mongos:mongos.alive.last()}=0   

##### Graphs（自定义图形）
|图形名称|说明|显示监控项|
|:-----:|:---:|:---:|
|Mongos bandwidth|表现 MongoDB 带宽信息| mongos.network.in，mongos.network.out|
|Mongos operations|表现 MongoDB 操作信息| mongos.op.delete，mongos.op.getmore，mongos.op.insert，mongos.op.query，mongos.op.update|  

#### 模板2  Template MongoDB Sh Config  
模板名：Template MongoDB Sh Config  
模板所属主机组：Templates/Databases  
内容：Applications 1，Items 11，Triggers 1，Graphs 2  
模板设计参考了 Zabbix 官方提供的 MySQL 数据库模板（Template DB MySQL）  

##### Applications（应用）  
应用名：Config  
包含监控项：11  

##### Items (监控项)  
|监控项名称|监控项键|类型|所属应用|  
|:-----:|:---:|:---:|:---:|
|**Mongo status**|config.alive|Zabbix trapper| Config| 
|**Mongo current connections**|config.conn.current|Zabbix trapper| Config| 
|**Mongo bytes received per second**|config.network.in|Zabbix trapper| Config| 
|**Mongo bytes sent per second**|config.network.out|Zabbix trapper| Config| 
|**Mongo delete operations per second**|config.op.delete|Zabbix trapper| Config| 
|**Mongo getmore operations per second**|config.op.getmore|Zabbix trapper| Config| 
|**Mongo insert operations per second**|config.op.insert|Zabbix trapper| Config| 
|**Mongo query operations per second**|config.op.query|Zabbix trapper| Config| 
|**Mongo update operations per second**|config.op.update|Zabbix trapper| Config| 
|**Mongo uptime (s)**|config.uptime|Zabbix trapper| Config| 
|**Mongo version**|config.version|Zabbix trapper| Config| 

##### Triggers（触发器）
名称： Config is down  
表达式：{Template MongoDB Sh Config:config.alive.last()}=0   

##### Graphs（自定义图形）
|图形名称|说明|显示监控项|
|:-----:|:---:|:---:|
|Config bandwidth|表现 MongoDB 带宽信息| config.network.in，config.network.out|
|Config operations|表现 MongoDB 操作信息| config.op.delete，config.op.getmore，config.op.insert，config.op.query，config.op.update|  

#### 模板3  Template MongoDB Sh Shard Notarbiter  
模板名：Template MongoDB Sh Shard Notarbiter  
模板所属主机组：Templates/Databases  
内容：Applications 1，Items 11，Triggers 1，Graphs 2  
模板设计参考了 Zabbix 官方提供的 MySQL 数据库模板（Template DB MySQL）  

##### Applications（应用）  
应用名：Shard  
包含监控项：11  

##### Items (监控项)  
|监控项名称|监控项键|类型|所属应用|  
|:-----:|:---:|:---:|:---:|
|**Mongo status**|shard.alive|Zabbix trapper| Shard| 
|**Mongo current connections**|shard.conn.current|Zabbix trapper| Shard| 
|**Mongo bytes received per second**|shard.network.in|Zabbix trapper| Shard| 
|**Mongo bytes sent per second**|shard.network.out|Zabbix trapper| Shard| 
|**Mongo delete operations per second**|shard.op.delete|Zabbix trapper| Shard| 
|**Mongo getmore operations per second**|shard.op.getmore|Zabbix trapper| Shard| 
|**Mongo insert operations per second**|shard.op.insert|Zabbix trapper| Shard| 
|**Mongo query operations per second**|shard.op.query|Zabbix trapper| Shard| 
|**Mongo update operations per second**|shard.op.update|Zabbix trapper| Shard| 
|**Mongo uptime (s)**|shard.uptime|Zabbix trapper| Shard| 
|**Mongo version**|shard.version|Zabbix trapper| Shard| 

##### Triggers（触发器）
名称： Shard is down  
表达式：{Template MongoDB Sh Shard Notarbiter:shard.alive.last()}=0   

##### Graphs（自定义图形）
|图形名称|说明|显示监控项|
|:-----:|:---:|:---:|
|Shard bandwidth|表现 MongoDB 带宽信息| shard.network.in，shard.network.out|
|Shard operations|表现 MongoDB 操作信息| shard.op.delete，shard.op.getmore，shard.op.insert，shard.op.query，shard.op.update|  

#### 模板4  Template MongoDB Sh Shard Arbiter  
模板名：Template MongoDB Sh Shard Arbiter  
模板所属主机组：Templates/Databases  
内容：Applications 1，Items 1，Triggers 1  

##### Applications（应用）  
应用名：Shard  
包含监控项：1  

##### Items (监控项)  
监控项名称：Mongo status  
监控项键：shard.alive  
类型：Zabbix trapper  
所属应用：Shard  

##### Triggers（触发器）
名称： Shard is down  
表达式：{Template MongoDB Sh Shard Arbiter:shard.alive.last()}=0   

### 配置使用  
##### 环境要求  
+ Linux CentOS7
+ Python 3.6+
+ Python 模块：requests 2.19.1,  pymongo 3.7.2  
+ zabbix-server 4.0
+ zabbix-sender 4.0  

*默认 Zabbix Server 和 Zabbix Sender 已自行配置完毕* 

##### 配置步骤  
1.将 create_host_sh.py 、cluster.json、sh_mongos.xml、sh_config.xml、sh_shard_na.xml、sh_shard_a.xml 置于同一目录下  

2.根据 Sharded Cluster 的实际部署情况修改 cluster.json  
```
示例：
{
	"mongos" : [
		{"ip" : "10.0.86.206", "port" : 20000},
		{"ip" : "10.0.86.204", "port" : 20000},
		{"ip" : "10.0.86.195", "port" : 20000}
	],
	"config" : [
		{"ip" : "10.0.86.206", "port" : 21000, "role" : "not arbiter"},
		{"ip" : "10.0.86.204", "port" : 21000, "role" : "not arbiter"},
		{"ip" : "10.0.86.195", "port" : 21000, "role" : "not arbiter"}
	],
	"shard" : [
		{
			"name" : "shard1",
			"members" : [
				{"ip" : "10.0.86.206", "port" : 27001, "role" : "not arbiter"},
				{"ip" : "10.0.86.204", "port" : 27001, "role" : "not arbiter"},
				{"ip" : "10.0.86.195", "port" : 27001, "role" : "arbiter"}
			]
		},		
		{
			"name" : "shard2",
			"members" : [
				{"ip" : "10.0.86.206", "port" : 27002, "role" : "not arbiter"},
				{"ip" : "10.0.86.204", "port" : 27002, "role" : "not arbiter"},
				{"ip" : "10.0.86.195", "port" : 27002, "role" : "arbiter"}
			]
		},
		{
			"name" : "shard3",
			"members" : [
				{"ip" : "10.0.86.195", "port" : 27003, "role" : "not arbiter"},
				{"ip" : "10.0.86.204", "port" : 27003, "role" : "not arbiter"},
				{"ip" : "10.0.86.206", "port" : 27003, "role" : "arbiter"}
			]
		}
	]
}
```

**格式说明**  

|key|value type|
|:-----:|:---:|
|mongos|array|
|config|array|
|shard|array|
|name|string|
|members|array|
|ip|string|
|port|int|
|role|"arbiter"/"not arbiter"|

3.执行 create_host_sh.py  
```
python create_host_sh.py -z <zabbix_server_ip> -u <zabbix_user> -p <zabbix_password>

zabbix_server_ip, zabbix_user, zabbix_password 请替换为实际值
注：若不输入 Zabbix Server 的用户名密码，则使用 Zabbix 默认的 Admin/zabbix
```

4.将 mongodb_sh_noauth.py 和 mongodb_sh_auth.py 中 main 方法中 cluster.json 文件路径替换为实际的绝对路径  
不要使用相对路径，否则使用 crontab 定时运行时将会产生错误  

5.根据 Sharded Cluster 是否需要安全认证分为两种情况：  
若不需认证，则通过 Linux 的 crontab 将 mongodb_sh_noauth.py 设置为定时执行（建议每2分钟执行一次）  
```
vim /etc/crontab 
在文件末尾添加：
*/2 * * * * root /usr/bin/python36 /yourpath/mongodb_sh_noauth.py -z <zabbix_server_ip>

zabbix_server_ip 请替换为实际值
另：python 路径和 mongodb_sh_noauth.py 路径请根据实际修改
```

若需要认证，则通过 Linux 的 crontab 将 mongodb_sh_auth.py 设置为定时执行（建议每2分钟执行一次）  

说明：MongoDB Sharded Cluster 的认证机制较为复杂，在 mongos 上创建的用户(即使是 root 用户)，只能在 mongos 和 config servers 的成员上进行认证，在各个 shard 上无法进行认证。原因在于每个 shard 有其单独的用户，在 shard 上创建，称为 shard local users，这些用户只能在本 shard 上认证，和 mongos 上创建的用户是完全独立的。具体参见 https://github.com/evharbor/mongodb-setup/blob/master/MongoDB%20shard集群安全认证.md  

因此，为方便进行监控，建议在集群 mongos 和 每个 shard 的主节点上分别创建用户名相同的用户，密码也设置为相同，且用户能有获取 serverStatus 的权限  

```
vim /etc/crontab 
在文件末尾添加：
*/2 * * * * root /usr/bin/python36 /yourpath/mongodb_sh_auth.py -z <zabbix_server_ip> -u <mongodb_user> -d <mongodb_password>

zabbix_server_ip, mongodb_user, mongodb_password 请替换为实际值
注：需确保输入的 MongoDB 用户有权限执行 serverStatus 命令，建议使用 admin 或 root 用户
另：python 路径和 mongodb_sh_auth.py 路径请根据实际修改
```

至此，配置完成，可在 Zabbix server web 界面找到名为 Mongodb Sh Cluster 的主机组查看监控数据  
