## EveryClass Web 服务模块
Web server part of EveryClass

![status](https://img.shields.io/badge/status-stable-green.svg)
![python version](https://img.shields.io/badge/python-3.6-blue.svg)
![license](https://img.shields.io/badge/license-MPL_2.0-orange.svg)
[![Build Status](https://travis-ci.org/fr0der1c/EveryClass-server.svg?branch=master)](https://travis-ci.org/fr0der1c/EveryClass-server)
[![codecov](https://codecov.io/gh/fr0der1c/EveryClass-server/branch/master/graph/badge.svg)](https://codecov.io/gh/fr0der1c/EveryClass-server)

这是 EveryClass 的 Web 服务模块。为了结构的清晰性，我们把本项目的不同模块分成了单独的仓库。查看 [项目主页](https://github.com/fr0der1c/EveryClass) 了解详情。

This is the server-part repo of EveryClass. We decided to separate its different module to standalone repositories for clearer structure. See [project page](https://github.com/fr0der1c/EveryClass) for more information. Since this repo is specially for college students in China, we do not offer English version of this README document.

### 最新进度
参见 [CHANGELOG.txt](https://github.com/fr0der1c/EveryClass-server/blob/master/CHANGELOG.txt)

### 未来计划
- 每次刷新数据后自动生成ics文件，使得手机端可以自动获取新课表，而无需再次来到本网站
- 增加一些趣味性的统计数据

更多请参见 issues 页面。

### 源码使用
1. 在 Python 3.6.0 下安装所需要的 package （在 requirements.txt 里）
2. 在 src/everyclass/config 目录下建立 development.py 用于开发配置
3. 导入数据库（[在这里](https://github.com/fr0der1c/EveryClass-collector/tree/master/sql)）
4. 配置环境变量`MODE`为`DEVELOPMENT`，然后运行 ec_server.py

### 参与改进
fork 本项目，然后 pull request。