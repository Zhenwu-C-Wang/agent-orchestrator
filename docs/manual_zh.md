# 中文使用手册

这份文档面向希望用中文快速了解和上手 `agent-orchestrator` 的读者。内容以当前仓库的真实能力为准，重点覆盖推荐使用路径、常见工作流、运行结果怎么看，以及现在的边界在哪里。

## 1. 项目是什么

`agent-orchestrator` 是一个本地优先的多代理编排项目。

当前版本的核心思路是：

- 用一个 `Supervisor` 串起多个边界清晰的 worker
- 用 `TaskPlanner` 在有限的工作流模板里做路由，而不是开放式自主规划
- 用结构化 schema、trace、tool invocation、audit artifact 保持可观察性
- 先把本地可运行、可调试、可测试做好，再逐步扩展能力

它现在已经支持五条有边界的工作流：

- `research_then_write`
- `analysis_then_write`
- `research_then_analysis_then_write`
- `comparison_then_write`
- `research_then_comparison_then_write`

## 2. 适合什么场景

当前比较适合：

- 本地做研究型问答
- 对 CSV 或 JSON 数据做受限分析
- 比较两份显式上下文并输出总结
- 在研究和分析之间做组合式建议输出
- 观察 workflow route、tool 使用、trace 和持久化产物

当前还不适合：

- 开放式 autonomous agent
- 并行 DAG 调度
- 大规模外部工具生态
- 面向完全零配置终端用户的正式安装包发布

如果你是第一次接触这个仓库，建议先把它理解成“可观察、可测试、边界清晰的本地编排基线”，而不是一个已经产品化完成的平台。

## 3. 环境要求

基础环境：

- Python `3.11+`
- macOS 或 Linux 更顺手
- 如果只做第一轮体验，用 `fake` runner 即可
- 如果要体验本地模型路径，再额外准备 `Ollama`

推荐先创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

如果你主要使用 CLI：

```bash
pip install -e '.[dev]'
```

如果你主要使用 Streamlit UI：

```bash
pip install -e '.[ui]'
```

如果你要尝试 macOS 打包预览：

```bash
pip install -e '.[ui,packaging]'
```

## 4. 推荐起步方式

### 4.1 最推荐的第一条路径：Streamlit UI

启动 UI：

```bash
streamlit run app.py
```

或者在安装了 UI 依赖后使用包装友好的入口：

```bash
agent-orchestrator-ui
```

第一次使用时建议：

- 保持 `Guided mode` 开启
- `Runner` 先选 `fake`
- 先从内置 `Starter Task` 开始
- 第一次不要改 `Advanced settings`

这样做的好处是：

- 能直接看到 planner 选中了哪条 workflow
- 不需要自己先准备样例文件
- 能直接看到 tool invocation 和 trace
- 出问题时更容易定位

### 4.2 CLI 起步方式

如果你更习惯命令行，先跑一条研究型任务：

```bash
python main.py "How should I bootstrap a supervisor-worker agent system?" \
  --runner fake \
  --output pretty
```

如果想看完整结构化结果：

```bash
python main.py "How should I bootstrap a supervisor-worker agent system?" \
  --runner fake \
  --output json
```

## 5. 内置工作流怎么理解

### 5.1 研究型

适合纯问题型输入，没有明确文件或 URL 上下文时最常见：

```bash
python main.py "How should I bootstrap a supervisor-worker agent system?" \
  --runner fake
```

预期路由：

- `research_then_write`

### 5.2 分析型

当你提供单个数据文件或网页上下文时，通常会走分析路径：

```bash
python main.py "Summarize the most important changes in this data." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output markdown
```

预期路由：

- `analysis_then_write`

你应该重点看：

- `tool_invocations` 里是否出现 `local_file_context`
- CSV 时是否出现 `csv_analysis`
- JSON 时是否出现 `json_analysis`
- 数值变化计算时是否出现 `data_computation`

### 5.3 研究 + 分析混合型

如果你不仅要总结数据，还要给建议，planner 会扩大到混合路径：

```bash
python main.py "Analyze this dataset and recommend what we should prioritize next." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --output json
```

预期路由：

- `research_then_analysis_then_write`

### 5.4 对比型

如果你提供两份上下文并明确要求比较：

```bash
python main.py "Compare these datasets and summarize the most important differences." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --context-file docs/sample_data/quarterly_metrics_baseline.csv \
  --output json
```

预期路由：

- `comparison_then_write`

如果你再加上“该优先哪个”的建议语气，通常会扩大到：

- `research_then_comparison_then_write`

## 6. 上下文怎么提供

当前最推荐的是显式上下文，而不是把路径或 URL 写进问题里。

### 6.1 本地文件

```bash
python main.py "Summarize the most important changes in this JSON snapshot." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.json \
  --output markdown
```

可以重复多个 `--context-file`。

### 6.2 URL

```bash
python main.py "Summarize the most important findings from this webpage." \
  --runner fake \
  --context-url https://example.com/report \
  --output markdown
```

可以重复多个 `--context-url`。

### 6.3 内联发现

默认情况下，问题文本里的文件路径和 URL 不会自动触发工具。

如果你明确想启用，再加：

```bash
--allow-inline-context-files
```

或：

```bash
--allow-inline-context-urls
```

## 7. UI 里该看什么

当一次运行完成后，最值得看的几个区域是：

- `Workflow Plan`
  用来确认 planner 到底选了哪条路径，为什么这样选
- `Overview`
  看整体结果摘要和 highlights
- `Intermediates`
  看 research / analysis / comparison 的中间结果
- `Tools`
  看是否真的调用了预期工具
- `Traces`
  看 worker 顺序、耗时、输出 schema 和 metadata
- `Raw JSON`
  看完整结构化产物

如果你打开了持久化目录，还可以看：

- 最近 runs
- acceptance reports
- cache 健康状态

## 8. Ollama 怎么用

当你确认 `fake` runner 跑通后，再尝试 Ollama：

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model llama3.1
```

默认：

- Ollama 地址是 `http://localhost:11434`
- model-layer retry 是 `--max-retries 1`
- backoff 是 `--retry-backoff-seconds 0.25`

如果你想提高稳健性：

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model qwen2.5:14b \
  --max-retries 2 \
  --retry-backoff-seconds 0.5
```

要注意：

- retry 只作用在模型调用层
- 不会自动重放整个 workflow
- Ollama 路径仍然比 `fake` runner 更容易受到模型差异影响

## 9. 持久化与检查

### 9.1 保存单次运行

```bash
python main.py "Analyze this dataset and summarize the most important changes." \
  --runner fake \
  --context-file docs/sample_data/quarterly_metrics.csv \
  --audit-dir artifacts/runs \
  --output json
```

### 9.2 查看历史运行

```bash
python -m orchestrator.runs --audit-dir artifacts/runs list
python -m orchestrator.runs --audit-dir artifacts/runs latest
python -m orchestrator.runs --audit-dir artifacts/runs show <run_id>
```

### 9.3 运行 acceptance

```bash
python -m orchestrator.acceptance --runner fake
```

如果你想保存 acceptance 报告：

```bash
python -m orchestrator.acceptance --runner fake --report-dir artifacts/acceptance
python -m orchestrator.acceptance_runs --report-dir artifacts/acceptance compare
```

### 9.4 使用缓存

```bash
python main.py "How should I bootstrap a supervisor-worker system?" \
  --runner ollama \
  --model qwen2.5:14b \
  --cache-dir artifacts/cache
```

查看缓存：

```bash
python -m orchestrator.cache --cache-dir artifacts/cache list
python -m orchestrator.cache --cache-dir artifacts/cache stats
```

## 10. 输出格式和退出码

常用输出格式：

- `--output pretty`
- `--output json`
- `--output markdown`

常见退出码：

- `3` 配置错误
- `4` 模型调用错误
- `5` 模型响应格式错误
- `6` workflow 执行错误
- `7` audit 查询错误
- `8` acceptance 运行中有 case 失败
- `9` cache 查询或管理错误
- `10` acceptance report 查询错误

## 11. macOS 打包预览

当前仓库已经能在本机产出第一版 `macOS .app` 和 `.dmg` 预览，但它还不是最终给小白用户双击安装的正式版本。

如果你要构建：

```bash
bash scripts/build_macos_app.sh
```

如果你想生成更接近分发包形态的 DMG：

```bash
bash scripts/build_macos_dmg.sh
```

如果你只想验证产物结构：

```bash
bash scripts/validate_macos_app.sh
```

或验证 DMG：

```bash
bash scripts/validate_macos_dmg.sh
```

当前状态可以概括成：

- 已能本地 build `.app`
- 已能本地 build `.dmg`
- 已能自动做 `.app` 和 `.dmg` 结构验证
- 已能通过 `agent-orchestrator-ui --workflow-smoke-test` 跑通内置 fake 首跑路径，验证打包资源、样例数据和审计落盘
- 还没有做第二台机器验证
- 还没有完成签名、公证、DMG 或最终分发体验

更详细的打包说明见 [macos_packaging.md](./macos_packaging.md)。

## 12. 推荐阅读顺序

如果你是第一次看这个仓库，推荐顺序：

1. 先看 [quickstart.md](./quickstart.md)
2. 如果你是外部测试者，再看 [beta_quickstart.md](./beta_quickstart.md)
3. 想了解支持边界，看 [beta_support_matrix.md](./beta_support_matrix.md)
4. 想了解标准测试任务，看 [beta_task_pack.md](./beta_task_pack.md)
5. 想了解架构边界，看 [architecture.md](./architecture.md)
6. 想了解未来规划，看 [../ROADMAP.md](../ROADMAP.md)

## 13. 维护约定

这份中文手册建议和下面这些文件一起维护，避免信息漂移：

- [README.md](../README.md)
- [quickstart.md](./quickstart.md)
- [beta_quickstart.md](./beta_quickstart.md)
- [beta_support_matrix.md](./beta_support_matrix.md)
- [macos_packaging.md](./macos_packaging.md)
- [../ROADMAP.md](../ROADMAP.md)

如果这些文件中的 CLI 参数、默认入口、支持范围、打包状态发生变化，这份中文手册也应该同步更新。
