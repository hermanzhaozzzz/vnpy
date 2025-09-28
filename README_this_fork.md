# Fork 仓库协作速览

本文记录在本地维护 upstream（官方仓库）与自己 fork（origin）时的常规 Git 操作流程。分为三部分：首次初始化、日常开发、跟进上游更新。

## 一、首次初始化远程设置

1. **将官方仓库改名为 `upstream`**
   ```bash
   git remote rename origin upstream
   ```
   这样可以避免后续 push 到官方仓库，且便于区分上下游。

2. **把你的 fork 配置为新的 `origin`**
   ```bash
   git remote add origin git@github.com:hermanzhaozzzz/vnpy.git
   ```

3. **验证远程地址是否正确**
   ```bash
   git remote -v
   ```
   确认 `upstream` 指向官方仓库，`origin` 指向个人 fork。

## 二、日常开发流程

1. **保持 `master` 与上游一致**
   ```bash
   git checkout master
   git fetch upstream
   git pull --rebase upstream master  # 或：git rebase upstream/master
   ```
   使用 `--rebase` 可以保持提交历史整洁。

2. **基于最新 `master` 开新分支**
   ```bash
   git checkout -b feat/xxx
   ```
   在新分支上完成开发、提交。

3. **将分支推送到个人 fork**
   ```bash
   git push -u origin feat/xxx
   ```
   `-u` 会在本地分支和远端分支之间建立跟踪关系，之后可直接使用 `git push`。

## 三、上游更新时的同步

1. **获取最新上游提交并在当前功能分支上 rebase**
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```
   如果出现冲突，按需解决后继续 `git rebase --continue`。

2. **强制推送更新后的分支到 fork**
   ```bash
   git push --force-with-lease
   ```
   `--force-with-lease` 会在推送前确认远端分支没有他人更新，相比 `--force` 更安全。

完成以上步骤后，即可在 GitHub 上向官方仓库发起 Pull Request，保持 fork 与上游仓库同步、高效协作。
