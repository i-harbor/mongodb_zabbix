## 监控 MongoDB Standalone  

### 概述 
MongoDB 单节点是 MongoDB 中最为简单的部署方式，对于 MongoDB 性能的监控，我们基于 Zabbix 提出一套简单、快速、有效的监控部署方案  

适用范围：
+ MongoDB 4.0  且无需使用用户名、密码进行安全认证 
+ Zabbix 4.0 

配置内容： 
+ 监控端： Zabbix Server 
+ 被监控端：Zabbix Sender（使用 Zabbix Sender 主动向 Zabbix Server 定时发送批量数据，而不使用 Zabbix Agent）  

**注：Zabbix Server 请自行配置，具体配置过程此处不再赘述，下文均默认 Zabbix Server 已完成配置**  

### 机制 
**监控端**（Zabbix Server）：需导入模板，创建主机组，在该主机组中为待监控的 MongoDB 单节点创建主机，并为主机链接导入的模板  
**被监控端**（Zabbix Sender）：通过 MongoDB 的 ip 和 port 来连接 MongoDB，并获取 serverStatus 信息，从信息中选取模板中各监控项所需数据，通过 Zabbix Sender 发送至 Zabbix Server 中对应主机及其监控项  

**注：Zabbix Sender 可安装在任意节点，不一定要安装在 MongoDB 所在节点，只要能通过 ip 和 port 连接上 MongoDB 即可** 

### 文件说明 
 
##### mongo_standalone.xml  

+ 适用于 MongoDB 单节点的 Zabbix 模板  


##### create_host_standalone.py 

+ 通过执行该 Python 文件可自动在 Zabbix Server 上完成模板导入、主机创建等系列过程  
+ 调用 Zabbix API，对于 API 的详细说明可参考 Zabbix 4.0 的官方文档 https://www.zabbix.com/documentation/current/manual/api  
+ 输入：Zabbix Server ip，Zabbix username，Zabbix password，MongoDB ip   
+ 完成内容：  
   [1] 将同一目录下 mongo_standalone.xml 中的模板导入 Zabbix Server   
   [2] 在 Zabbix Server 中创建名为 Mongodb Standalone 的主机组  
   [3] 在 Mongodb Standalone 主机组中创建名为 mongo_server 的主机  
   [4] 为 mongo_server 链接导入的模板  

##### mongodb_standalone_noauth.py  

+ 通过执行该 Python 文件可以获取 MongoDB 的 serverStatus信息，并由 Zabbix Sender 发送至 Zabbix Server 的对应主机  
+ 输入： Zabbix Server ip，MongoDB ip，MongoDB port
+ 完成内容：  
   [1] 通过 MongoDB ip 和 port 连接 MongoDB   
   [2] 获取 serverStatus 信息  
   [3] 从中取出模板中各监控项对应的数据  
   [4] 通过 Zabbix Sender 全部发送至 Zabbix Server 的对应主机  

### 模板 
模板名：Template DB MongoDB  
内容：Applications 6，Items 14，Triggers 1，Graphs 2  
模板设计参考了 Zabbix 官方提供的 MySQL 数据库模板（Template DB MySQL）  

##### Applications（应用） 
|应用名|说明|包含监控项数|  
|:-----:|:---:|:---:|
|**Basic_info**|数据库基础信息|3|   
|**Connections**|数据库连接数|2|   
|**Extra_info**|数据库其它信息|1|   
|**Memory**|数据库内存使用信息|1|   
|**Network**|数据库网络信息|2|   
|**Operation**|数据库基本操作信息|5| 

##### Items (监控项)  
|监控项名称|监控项键|类型|所属应用|  
|:-----:|:---:|:---:|:---:|
|**Mongo status**|mongo.alive|Zabbix trapper| Basic_info| 
|**Mongo available connections**|mongo.conn.available|Zabbix trapper| Connections| 
|**Mongo current connections**|mongo.conn.current|Zabbix trapper| Connections| 
|**Mongo memory currently used (MB)**|mongo.mem.resident|Zabbix trapper| Memory| 
|**Mongo bytes received per second**|mongo.network.in|Zabbix trapper| Network| 
|**Mongo bytes sent per second**|mongo.network.out|Zabbix trapper| Network| 
|**Mongo delete operations per second**|mongo.op.delete|Zabbix trapper| Operation| 
|**Mongo getmore operations per second**|mongo.op.getmore|Zabbix trapper| Operation| 
|**Mongo insert operations per second**|mongo.op.insert|Zabbix trapper| Operation| 
|**Mongo query operations per second**|mongo.op.query|Zabbix trapper| Operation| 
|**Mongo update operations per second**|mongo.op.update|Zabbix trapper| Operation| 
|**Mongo page faults**|mongo.page_faults|Zabbix trapper| Extra_info| 
|**Mongo uptime (s)**|mongo.uptime|Zabbix trapper| Basic_info| 
|**Mongo version**|mongo.version|Zabbix trapper| Basic_info| 

##### Triggers（触发器）
名称： Mongo is down 
表达式：{Template DB MongoDB:mongo.alive.last()}=0   

##### Graphs（自定义图形）
|图形名称|说明|显示监控项|
|:-----:|:---:|:---:|
|Mongo bandwidth|表现 MongoDB 带宽信息| mongo.network.in，mongo.network.out|
|Mongo operations|表现 MongoDB 操作信息| mongo.op.delete，mongo.op.getmore，mongo.op.insert，mongo.op.query，mongo.op.update|  

### 配置使用
##### 环境要求
+ Linux CentOS7
+ Python 3.6+
+ Python 模块：requests 2.19.1,  pymongo 3.7.2
+ zabbix-sender 4.0  

*默认 Zabbix Server 已自行配置完毕*

##### 配置步骤  

1.将 create_host_standalone.py 文件与 mongo_standalone.xml 置于同一目录下  

2.执行 create_host_standalone.py  
```
python create_host_standalone.py -z <zabbix_server_ip> -u <zabbix_user> -p <zabbix_password> -m <mongodb_ip>

zabbix_server_ip，zabbix_user，zabbix_password，mongodb_ip 请替换为实际值
注：若不输入 Zabbix Server 的用户名密码，则使用 Zabbix 默认的 Admin/zabbix
```

3.通过 Linux 的 crontab 将 mongodb_standalone_noauth.py 设置为定时执行（建议2分钟执行一次）
```
vim /etc/crontab 
在文件末尾添加：
*/2 * * * * root /usr/bin/python36 /yourpath/mongodb_standalone_noauth.py -z <zabbix_server_ip> -m <mongodb_ip> -p <mongodb_port>

zabbix_server_ip，mongodb_ip，mongodb_port 请替换为实际值
另：python路径和mongodb_standalone_noauth.py路径根据实际修改
```

至此，配置完成，即可在 Zabbix Server 中找到名为 Mongodb Standalone 的主机组，在该主机组中找到名为 mongo_server 的主机，查看监控数据  



