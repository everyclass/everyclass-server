## EveryClass Web 服务模块
Web server part of EveryClass

这是 EveryClass 的 Web 服务模块。为了结构的清晰性，我们把本项目的不同模块分成了单独的仓库。查看 [项目主页](https://github.com/fr0der1c/EveryClass) 了解详情。

This is the server-part repo of EveryClass. We decided to separate its different module to standalone repositories for clearer structure. See [project page](https://github.com/fr0der1c/EveryClass) for more information. Since this repo is specially for college students in China, we do not offer English version of this README document.

### 最新进度
#### August 27, 2017
- Sentry 支持
- 多域名/CDN 支持
- 修复 ics 导出路径链接错误的 bug
- HTML 压缩
- 前端自动化支持

在 CHANGELOG.txt 中可以找到更多信息。

### 未来计划
- 继续收集学号前缀和专业对应关系信息
- 增加一些趣味性的统计数据

### 源码使用
1. 在 Python 3.6.0 下安装所需要的 package （在 requirements.txt 里）
2. 在 src/everyclass/config 目录下建立 development.py 用于开发配置
3. 导入数据库（[在这里](https://github.com/fr0der1c/EveryClass-collector/tree/master/sql)）
4. 配置环境变量`MODE`为`DEVELOPMENT`，然后运行 ec_server.py

### 参与改进
fork 本项目，然后 pull request。