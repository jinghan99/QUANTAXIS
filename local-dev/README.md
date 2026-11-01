# QUANTAXIS 本地开发与服务部署

## 已部署结构

| 环境 | 后端源码 | Python | 前端 | 后端 API |
|---|---|---|---|---|
| dev（配置目标） | `E:\PycharmProjects\QUANTAXIS` | Windows Conda `quantaxis` / Python 3.11 | http://localhost:8080 | http://localhost:18089 |
| prod（后续部署目标） | 固定源码版本，后续部署到 35 | 35 上的独立运行环境 | 尚待部署设计 | http://192.168.1.35:18089 |

以上为用户确认的目标配置。本轮只修改文件，没有重启现有历史 WSL 服务或部署 prod；历史验证回执中的 8010/8011 是当时的运行端口，不是新端口验收结果。

前端发布文件分别在 `E:\PycharmProjects\qamazing_community` 和 `E:\PycharmProjects\qamazing_community-prod`。公开前端只有编译产物，没有 Vue 源码工程和 npm 热更新。服务会将它依赖的 CDN 文件缓存到本机，并把已支持的回测 API 代理到对应后端。

后端版本为 `2.1.0.alpha2`，上游提交 `232aa7ac9869966108f02a8fff85f1f7b09a9ce2`。dev 启用调试与自动重载；prod 关闭二者。生产源码快照带 `deployment-manifest.json`，没有使用 dev 源码作为运行目录。后续新改动需单独发布到 prod。

数据库共用 `192.168.1.35:27017` 的同一个 `quantaxis` 库。两套环境并不是数据隔离环境；dev 的业务写入也会影响 prod。调度控制使用同一 `qascheduler` 库中的 `jobs_dev` / `jobs_prod`，防止两套进程读取同一任务集合。

## Windows / PyCharm 开发

专用 Miniconda 环境名为 `quantaxis`，Python 3.11；没有向 `stock` 环境安装或调整依赖。

1. 在 PyCharm 打开 `E:\PycharmProjects\QUANTAXIS`。
2. 设置项目解释器为 `C:\Users\jinghan\miniconda3\envs\quantaxis\python.exe`。
3. 运行配置下拉框中选择 `QUANTAXIS Dev` 同时运行前后端；也可分别选择 `QUANTAXIS Backend`、`QUANTAXIS Frontend`。配置在 `.run` 目录。
4. 如果 WSL dev 还在运行，先在 PowerShell 执行：

```powershell
cd E:\PycharmProjects\QUANTAXIS
.\local-dev\manage.ps1 -Action stop -Environment dev
```

这只停止 dev，不停止 WSL prod 和 35 上的数据库。Windows 和 WSL 不应同时占用同一组 dev 端口。

若 PyCharm 没显示共享运行配置，手动添加 Python 配置：

| 字段 | 后端 | 前端 |
|---|---|---|
| Script path | `E:\PycharmProjects\QUANTAXIS\local-dev\run_backend.py` | `E:\PycharmProjects\QUANTAXIS\local-dev\run_frontend.py` |
| Parameters | `--address=127.0.0.1 --port=18089` | 留空 |
| Working directory | `E:\PycharmProjects\QUANTAXIS` | 同左 |
| Interpreter | `miniconda3\envs\quantaxis\python.exe` | 同左 |

依赖重新安装与本机连接初始化：

```powershell
& C:\Users\jinghan\miniconda3\envs\quantaxis\python.exe -m pip install -r requirements.txt
& C:\Users\jinghan\miniconda3\envs\quantaxis\python.exe local-dev\configure_windows.py
```

配置脚本从现有 SSH 别名 `thousand-stock-server` 获取应用连接文件，保存在 `%LOCALAPPDATA%\quantaxis-local\database.json`；不把密码放入运行配置或源码。专用环境的 `.pth` 只加载该项目的 MongoDB 配置。`MONGODB_URI` 优先于旧的全局 `~/.quantaxis/setting/config.ini`。

## WSL 服务管理

```powershell
.\local-dev\manage.ps1 -Action status -Environment all
.\local-dev\manage.ps1 -Action start -Environment dev
.\local-dev\manage.ps1 -Action restart -Environment prod
.\local-dev\manage.ps1 -Action logs -Environment dev
.\local-dev\manage.ps1 -Action jupyter
```

WSL 运行依赖位于 `/home/jinghan/.local/share/quantaxis-local/venv` 和 `prod/venv`。日志在该目录下 `dev/logs`、`prod/logs`。JupyterLab 是 dev 研究入口，端口 8888，使用本机保存的访问令牌。

这些用户服务已配置为随 WSL 用户 systemd 启动；本次没有执行 Windows/WSL 整机重启测试。

## 35 上的 MongoDB

服务目录：`/vol2/1000/docker/mongodb`

```text
docker-compose.yml
.env                 # 管理员和应用密码；权限 600
client.json          # QUANTAXIS 连接 URI；权限 600
init-user.js
data/                # /data/db
configdb/            # /data/configdb
migration-receipt.json
```

容器名 `common-mongodb`，固定镜像 `mongo:7.0.45`，地址 `192.168.1.35:27017`，启用密码认证、健康检查、日志轮转和 `unless-stopped` 自动重启。管理员账号 `mongo_admin`；应用账号 `quantaxis` 具有 `quantaxis`、`qascheduler`、`QAREALTIME` 的读写权限。

```bash
cd /vol2/1000/docker/mongodb
sudo docker compose ps
sudo docker compose logs --tail 100
sudo docker compose up -d
```

迁移前的停止容器及 `common-mongodb-data` 数据卷均保留；原本机 WSL MongoDB 已停止，旧数据目录保留。`deploy_mongo.py` 与 `migrate_mongo_compose.py` 记录了本次初始部署和迁移过程，不是日常启动命令。

## 验证与功能边界

访问 `/api/readiness`（前端代理）或后端 `/readiness`，可查看实际环境、MongoDB 地址、数据行数与调试配置。`verify.py` 还会写入并读回 `quantaxis.deployment_checks` 的审计记录，保留验证证据。

本次已验证 dev / prod 的后端启动、认证 MongoDB 连接、持久化写入与读回、账户列表及独立调度查询。行情、指数、账户历史目前为空；没有运行行情初始化或交易。

行情、财务和实盘独立服务尚未部署，对应前端配置指向本机 `503 unsupported` 入口；不会自动接到上游网页里的旧服务器地址。当前核心服务可用于开发启动，不代表所有社区菜单已经具备完整业务能力。Rust 可选组件未安装。

- [行情初始化](DATA_INIT.md)
- [策略开发](STRATEGY_GUIDE.md)
- [QFQ 与腾讯实测比较](QFQ_COMPARISON.md)
- [官方安装指南](https://yutiansut.github.io/QUANTAXIS/getting-started/installation.html)
