## Monitoring For Sharded Cluster  

对于 MongoDB 而言，有三种部署方式：  
+ Standalone（单节点）  
+ Replica Set（副本集）
+ Sharded Cluster（分片集）

Sharded Cluster 是其中最为复杂的部署方式，既包含提供分布式数据存储的分片 Shard，同时包含保证数据安全的副本 Replica Set；除常见的 mongod 实例外，还包含 mongos 实例  

我们致力于实现简单快速地使用 Zabbix 4.0 来监控 MongoDB 的 Sharded Cluster

### 设计思想  
+ 用户通过编写一个 JSON 文件来描述其 Sharded Cluster 的复杂结构（JSON 文件作为输入）  
+ 程序读取 JSON 文件，解析集群结构，并调用 zabbix web 提供的 API ，自动创建主机组、导入模板、创建主机、链接模板等  
+ 定时使用脚本，收集集群信息，通过 zabbix-sender 发送给 zabbix server 上对应的主机及监控项  

### 使用说明  

#### 适用对象  
适用于使用 Zabbix 4.0 监控**无安全认证**的 Sharded Cluster  

#### 环境要求  
+ Linux  
+ Python 3.6+
+ Python Module: requests 2.19.1, pymongo 3.7.2  
+ zabbix server 4.0
+ zabbix-sender 4.0  

#### 使用步骤  
1. 将 monitoring for Sharded Cluster 目录下的全部内容下载到本地路径，如/root/liyunting/
2. 修改 cluster_structure.json 文件，描述需要监控的 Sharded Cluster 的信息  
3. 修改 create_host.py 中的 zabbix server ip 并执行  

   该脚本会自动解析 JSON 文件中的集群结构，在 zabbix web 上 创建名为 “Mongodb Sharded Cluster”的 hostgroup，导入 mongos.xml、config.xml、shard0.xml、shard1.xml、shard2.xml、shard3.xml六个模板，并根据集群结构创建相应数量的主机并链接上对应的模板  

4. 修改 mongodb_zabbix_noauth.py 中的 zabbix_server 和 zabbix_host 变量   
5. 使用 Linux 的 crontab 将 mongodb_zabbix_noauth.py 设置为定时执行，即可完成监控  
6. zabbix 的邮件报警需在 web 上自行配置  

注：mongodb_zabbix_noauth.py 中也需读取 cluster_structure.json，建议将文件路径修改为绝对路径，防止设置定时后出现问题  






