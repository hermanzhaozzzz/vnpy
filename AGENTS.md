# Repository Guidelines

在本项目中，Codex 与贡献者默认使用中文交流，请在沟通和提交文档时保持中文。如需引用命令或日志，请配合简要中文说明，避免仅贴 raw log。

## 项目结构与模块组织
VeighNa 的核心源码位于 `vnpy/`。`trader/` 提供事件引擎、用户界面 (`ui/`) 以及本地化资源 (`locale/`)；`alpha/` 专注机器学习研究；`event/`、`rpc/` 与 `chart/` 分别负责消息分发、远程调用和可视化工具。说明性资料位于 `docs/`，可运行教学例程与冒烟用例集中在 `examples/`。

非原始vn.py仓库代码,本用户定制的信息：
- `mytest/`: 用户临时测试用的脚本文件夹，可承载临时联调脚本（如 `run_qmt.py`）。
- `pyproject.toml`: 定制了poetry配置信息，依赖和构建元信息。

## 构建、测试与开发命令
- `poetry install --all-extras --all-groups`：一次性安装运行时、Alpha 拓展及开发工具，第一次 clone 后执行。

## 代码风格与命名约定
目标 Python 3.10+，统一使用 4 空格缩进。模块与可调用对象采用 `snake_case`，类名使用 `CamelCase`，配置常量保持 `UPPER_CASE`。项目启用严格类型检查：`mypy` 配置了 `disallow_untyped_defs`、`no_implicit_optional` 与 `strict_optional`。Ruff 会应用 bugbear 以及 `E`、`F`、`UP`、`W` 规则，因忽略了 `E501` 可适度放宽行宽。日志沿用 `vnpy.trader.utility` 中的 `loguru` 模式，新增 UI 字符串需同步进 `locale` 目录的 `.po` 文件并更新 `vnpy/trader/locale/...`。

## 测试指南
优先使用 `pytest` 扩充覆盖率，可在目标包旁新建轻量测试（例如 `vnpy/trader/test_*.py`）以便自动发现。测试命名聚焦行为，如 `test_engine_register_event`。涉及回测或经纪商联机的用例需使用固件化数据或夹具，必要时通过 `pytest.mark.slow`、`pytest.mark.broker` 等标签区分运行环境，并在 CI 说明如何跳过（例如 `pytest -m "not slow"`）。为复杂场景撰写 docstring，记录前置条件与期望输出。

## 提交与合并请求规范
提交主题保持简洁、祈使语，建议不超过 72 个字符；视情况延续历史中的作用域标签（如 `[Mod] update CHANGELOG`、`[Fix] guard null gateway`）。提交正文记录关键改动、风险与回滚策略。合并请求需说明动机、列出验证命令或界面截图，并关联相关 Issue 或论坛主题。若更改公共 API 或数据结构，请在 PR、`CHANGELOG.md` 与文档同步标注影响范围；必要时提供升级脚本或迁移步骤。

## 协作与沟通
建议在团队看板中维护 backlog 与 in progress 列，避免重复工作。每日 standup 模板为 `Done / Doing / Blocked`，请按顺序汇报。跨时区协作时，使用 issue comment 记录决策，并在摘要中加入 `TL;DR` short note。提交审查建议时，优先使用 GitHub review suggestion 功能并附带中文概述。跨团队即时讨论请在 shared Slack channel `#vnpy-dev` 中进行，并将结论同步至 meeting notes 文档。

## 安全与配置提示
勿在仓库中提交任何凭据、经纪商端点或 API Token，可借助本地 `.env` 或操作系统密钥管理，并通过 `vnpy.trader.setting` 读取。对新增配置项，请同步在相关模块或文档中说明所需环境变量与权限，必要时示例 `config/sample.env`。部署生产环境前，确认日志级别、加密存储和网络白名单均符合机构合规要求。
