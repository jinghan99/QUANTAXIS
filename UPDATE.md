# 从主仓库更新

当前远程关系：

```text
origin    git@github.com:jinghan99/QUANTAXIS.git
upstream  https://github.com/yutiansut/QUANTAXIS.git
```

在项目根目录的 PowerShell 执行：

```powershell
# 只检查本地分支和未提交文件
.\update-upstream.ps1 -Check

# 提交或自行 stash 当前工作后，将 upstream/master 合并到当前分支
.\update-upstream.ps1

# 同时把主仓库 master 快进同步到你的 Fork master
.\update-upstream.ps1 -PushFork
```

默认使用普通 merge，保留当前分支已提交的改动。需要严格只允许快进时使用 `-Mode ff-only`。工作区有未提交 / 未跟踪文件会停止；发生合并冲突会自动中止本次合并，恢复到更新前的干净工作区。脚本不强推，不自动 stash 或 reset，不发布生产环境。

`-PushFork` 同步的是 Fork 的 `master`，当前功能分支仍保留在本地。若 Fork master 有独立提交而不能快进，脚本会拒绝覆盖。执行日志保存在 `.git/upstream-update-logs`。

目前本地开发改动尚未提交，所以正式更新会先提示处理工作区。需要向主仓库贡献时，先同步主仓库更新，再完成自测与更新记录（当前项目文档入口为 `doc/appendix/changelog.md`），将功能分支推送到自己的 Fork 后创建 PR。不要把数据库密码文件加入提交。

prod 是独立固定快照；更新 dev 仓库不会自动修改正在运行的 prod。
