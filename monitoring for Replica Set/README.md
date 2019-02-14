## 监控 MongoDB Replica Set  

### 概述  
MongoDB 副本集是 MongoDB 中主要的一种部署方式，采用一组 mongod 进程来维护同一数据集，以实现数据备份及高可用性。副本集一般包含若干数据存储节点，以及不存储数据的仲裁点。其中，数据存储节点中有且仅有一个主节点，其余均为备节点。仲裁点非必需，可无。当主节点故障，副本集将通过投票在备节点中选举出新的主节点，从而保证数据的高可用性。  

对于 MongoDB 副本集的监控，我们基于 Zabbix 提出一套简单、快速、有效的监控部署方案  

适用范围：
+ MongoDB 4.0   
+ Zabbix 4.0 

配置内容： 
+ 监控端： Zabbix Server 
+ 被监控端：Zabbix Sender（使用 Zabbix Sender 主动向 Zabbix Server 定时发送批量数据，而不使用 Zabbix Agent）  

**注：Zabbix Server 和 Zabbix Sender 请自行配置，具体配置过程此处不再赘述，下文均默认 Zabbix Server 和 Zabbix Sender已完成配置**  

### 机制  
**监控端**（Zabbix Server）：读取 repl.json 文件，根据得到的副本集信息导入模板、创建主机组、创建相应数量的主机并分别为其链接上合适的模板  
**被监控端**（Zabbix Sender）：读取 repl.json 文件，根据得到的副本集中每个成员节点的 ip 和 port，分别连接到相应的 mongod 进程(若 MongoDB 需认证，则还需 user 和 password)，从主、备节点获取 serverStatus 信息，而仲裁点只需判断是否存活，然后选取模板中各监控项所需数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机及其监控项  

**注：Zabbix Sender 可安装在任意节点，不一定要安装在 MongoDB 副本集部署节点，只要能通过 ip 和 port 连接上 MongoDB 副本集所有成员即可**

### 文件说明  

##### repl.json  

+ 通过严格的 JSON 格式描述副本集相关信息，包括副本集名称和各成员信息  
+ name 值即为副本集名称，members 值即为副本集中所有成员信息  
+ 成员信息包含 ip、port 和 role，其中 role 用于描述该成员是否是仲裁点(arbiter)，仅有 not arbiter / arbiter两个取值  
```
示例：  
{
	"name" : "myrepl",
	"members" : [
		{"ip" : "10.0.87.31", "port" : 27017, "role" : "not arbiter"},
		{"ip" : "10.0.87.32", "port" : 27017, "role" : "not arbiter"},
		{"ip" : "10.0.87.33", "port" : 27017, "role" : "not arbiter"},
		{"ip" : "10.0.87.34", "port" : 27017, "role" : "not arbiter"},
		{"ip" : "10.0.87.35", "port" : 27017, "role" : "arbiter"}
	]
}
```

##### mongodb_repl_notarbiter.xml  

+ 适用于 MongoDB 副本集中主节点或备节点（非仲裁点）的 Zabbix 模板  

##### mongodb_repl_arbiter.xml  

+ 适用于 MongoDB 副本集中仲裁点的 Zabbix 模板  

##### create_host_repl.py  

+ 通过执行该 Python 文件可自动在 Zabbix Server 上完成模板导入、主机创建等系列过程  
+ 调用 Zabbix API，对于 API 的详细说明可参考 Zabbix 4.0 的官方文档 https://www.zabbix.com/documentation/4.0/manual/api  
+ 输入：Zabbix Server ip，Zabbix username，Zabbix password  
+ 完成内容：  
   [1] 将同一目录下 mongodb_repl_arbiter.xml 和 mongodb_repl_notarbiter.xml 中的两个模板导入 Zabbix Server  
   [2] 读取同一目录下 repl.json 文件，获取副本集名称及所有成员信息  
   [3] 在 Zabbix Server 中创建主机组，主机组名为前缀 Mongodb Repl 加上副本集名称，如 'Mongodb Repl myrepl'  
   [4] 在该主机组中为每一个成员创建一个主机，主机名为前缀 repl_ 加上成员 ip，如 'repl_10.0.87.31'  
   [5] 创建主机时根据成员是否为仲裁点，为主机链接上相应的模板  

##### mongodb_repl_noauth.py  

+ 通过执行该 Python 文件可分别获取 MongoDB 副本集中各成员的相关数据信息，并由 Zabbix Sender 发送至 Zabbix Server 中对应主机  
+ 对于主节点和备节点（非仲裁点）获取 serverStatus 信息，对于仲裁点仅判断是否存活  
+ 输入：Zabbix Server ip  
+ 完成内容：  
   [1] 读取 repl.json 文件，获取副本集所有成员信息  
   [2] 通过每个成员的 ip 和 port 连接到其 mongod 进程，通过 role 判断是否为仲裁点  
   [3] 若不是仲裁点，则获取 serverStatus 信息，从中取出模板中各监控项对应的数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  
   [4] 若是仲裁点，则仅判断该节点是否存活，将存活信息通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  

##### mongodb_repl_auth.py  

+ 通过执行该 Python 文件可分别获取 MongoDB 副本集中各成员的相关数据信息，并由 Zabbix Sender 发送至 Zabbix Server 中对应主机  
+ 对于主节点和备节点（非仲裁点）获取 serverStatus 信息，对于仲裁点仅判断是否存活  
+ 输入：Zabbix Server ip, MongoDB user, MongoDB password  
+ 完成内容：  
   [1] 读取 repl.json 文件，获取副本集所有成员信息  
   [2] 通过每个成员的 ip 和 port 连接到其 mongod 进程，通过 role 判断是否为仲裁点  
   [3] 若不是仲裁点，则通过 MongoDB user 和 password 完成认证，再获取 serverStatus 信息，从中取出模板中各监控项对应的数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  
   [4] 若是仲裁点，则无需认证，仅判断该节点是否存活，将存活信息通过 Zabbix Sender 发送至 Zabbix Server 中对应主机  

### 模板  

#### 模板1  Template MongoDB Repl Notarbiter  
模板名：Template MongoDB Repl Notarbiter  
模板所属主机组：Templates/Databases  
内容：Applications 1，Items 14，Triggers 1，Graphs 2  
模板设计参考了 Zabbix 官方提供的 MySQL 数据库模板（Template DB MySQL）  

##### Applications（应用）  
应用名：Mongo  
包含监控项：14  

##### Items (监控项)  
|监控项名称|监控项键|类型|所属应用|  
|:-----:|:---:|:---:|:---:|
|**Mongo status**|mongo.alive|Zabbix trapper| Mongo| 
|**Mongo available connections**|mongo.conn.available|Zabbix trapper| Mongo| 
|**Mongo current connections**|mongo.conn.current|Zabbix trapper| Mongo| 
|**Mongo memory currently used (MB)**|mongo.mem.resident|Zabbix trapper| Mongo| 
|**Mongo bytes received per second**|mongo.network.in|Zabbix trapper| Mongo| 
|**Mongo bytes sent per second**|mongo.network.out|Zabbix trapper| Mongo| 
|**Mongo delete operations per second**|mongo.op.delete|Zabbix trapper| Mongo| 
|**Mongo getmore operations per second**|mongo.op.getmore|Zabbix trapper| Mongo| 
|**Mongo insert operations per second**|mongo.op.insert|Zabbix trapper| Mongo| 
|**Mongo query operations per second**|mongo.op.query|Zabbix trapper| Mongo| 
|**Mongo update operations per second**|mongo.op.update|Zabbix trapper| Mongo| 
|**Mongo page faults**|mongo.page_faults|Zabbix trapper| Mongo| 
|**Mongo uptime (s)**|mongo.uptime|Zabbix trapper| Mongo| 
|**Mongo version**|mongo.version|Zabbix trapper| Mongo| 

##### Triggers（触发器）
名称： Mongo is down  
表达式：{Template MongoDB Repl Notarbiter:mongo.alive.last()}=0   

##### Graphs（自定义图形）
|图形名称|说明|显示监控项|
|:-----:|:---:|:---:|
|Mongo bandwidth|表现 MongoDB 带宽信息| mongo.network.in，mongo.network.out|
|Mongo operations|表现 MongoDB 操作信息| mongo.op.delete，mongo.op.getmore，mongo.op.insert，mongo.op.query，mongo.op.update|  


#### 模板2  Template MongoDB Repl Arbiter  
模板名：Template MongoDB Repl Arbiter  
模板所属主机组：Templates/Databases  
内容：Applications 1，Items 1，Triggers 1  

##### Applications（应用）  
应用名：Mongo  
包含监控项：1  

##### Items (监控项)  
监控项名称：Mongo status  
监控项键：mongo.alive  
类型：Zabbix trapper  
所属应用：Mongo  

##### Triggers（触发器）
名称： Mongo is down  
表达式：{Template MongoDB Repl Arbiter:mongo.alive.last()}=0   

### 配置使用  
##### 环境要求  
+ Linux CentOS7
+ Python 3.6+
+ Python 模块：requests 2.19.1,  pymongo 3.7.2  
+ zabbix-server 4.0
+ zabbix-sender 4.0  

*默认 Zabbix Server 和 Zabbix Sender 已自行配置完毕* 

##### 配置步骤  
1.将 create_host_repl.py 、repl.json、mongodb_repl_notarbiter.xml、mongodb_repl_arbiter.xml 置于同一目录下  

2.根据副本集的实际部署情况修改 repl.json  
如下例中，副本集名为 myrepl，副本集中共有5个成员，其中4个数据节点(含主节点和备节点)以及1个仲裁点  
```
示例：  
{
   "name" : "myrepl",
   "members" : [
      {"ip" : "10.0.87.31", "port" : 27017, "role" : "not arbiter"},
      {"ip" : "10.0.87.32", "port" : 27017, "role" : "not arbiter"},
      {"ip" : "10.0.87.33", "port" : 27017, "role" : "not arbiter"},
      {"ip" : "10.0.87.34", "port" : 27017, "role" : "not arbiter"},
      {"ip" : "10.0.87.35", "port" : 27017, "role" : "arbiter"}
   ]
}
```
**格式说明**  

|key|value type|
|:-----:|:---:|
|name|string|
|members|array|
|ip|string|
|port|int|
|role|"arbiter"/"not arbiter"|

3.执行 create_host_repl.py  
```
python create_host_repl.py -z <zabbix_server_ip> -u <zabbix_user> -p <zabbix_password>

zabbix_server_ip, zabbix_user, zabbix_password 请替换为实际值
注：若不输入 Zabbix Server 的用户名密码，则使用 Zabbix 默认的 Admin/zabbix
```
也可选择不执行 create_host_repl.py ，自行在 zabbix server web 界面上完成模板导入、创建主机组、创建主机、链接模板等  

4.将 mongodb_repl_noauth.py 和 mongodb_repl_auth.py 中 main 方法中 repl.json 文件路径替换为实际的绝对路径  
不要使用相对路径，否则使用 crontab 定时运行时将会产生错误  

5.根据该副本集是否需要安全认证分为两种情况：  
若不需认证，则通过 Linux 的 crontab 将 mongodb_repl_noauth.py 设置为定时执行（建议每2分钟执行一次）  
```
vim /etc/crontab 
在文件末尾添加：
*/2 * * * * root /usr/bin/python36 /yourpath/mongodb_repl_noauth.py -z <zabbix_server_ip>

zabbix_server_ip 请替换为实际值
另：python 路径和 mongodb_repl_noauth.py 路径请根据实际修改
```

若需要认证，则通过 Linux 的 crontab 将 mongodb_repl_auth.py 设置为定时执行（建议每2分钟执行一次）  
```
vim /etc/crontab 
在文件末尾添加：
*/2 * * * * root /usr/bin/python36 /yourpath/mongodb_repl_auth.py -z <zabbix_server_ip> -u <mongodb_user> -d <mongodb_password>

zabbix_server_ip, mongodb_user, mongodb_password 请替换为实际值
注：需确保输入的 MongoDB 用户有权限执行 serverStatus 命令，建议使用 admin 或 root 用户
另：python 路径和 mongodb_repl_auth.py 路径请根据实际修改
```

至此，配置完成，可在 Zabbix server web 界面查看监控数据  

