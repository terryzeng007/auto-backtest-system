# TODOS

## [CONFIG] 统一配置管理 — 本次实现
- **What:** 创建 `.env` 文件管理 Tushare token、火山引擎 API key、模型名等敏感配置
- **Why:** 当前 config.json 硬编码，敏感信息不能提交到 Git
- **Pros:** 安全、环境可切换
- **Cons:** 多一个配置文件
- **Context:** Tushare token 和 LLM API key 必须可配置，不能硬编码。.env 已加入 .gitignore
- **Depends on:** 无

## [FRONTEND] Streamlit 多页面架构
- **What:** 支持"回测"和"数据管理"（同步/缓存状态）两个页面
- **Why:** MVP 只有回测页，但数据同步状态用户需要看到
- **Pros:** 清晰的页面分工
- **Cons:** 多页面增加复杂度
- **Context:** 数据同步可能耗时，用户需看到进度和状态
- **Depends on:** 数据层完成
