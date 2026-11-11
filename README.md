# 纸迹工作台

淘宝纸质笔记本试卖的 T02–T04 首版：保存真实货源证据、整理商品规格和报价、确定性核价、记录验样，并只把验样通过的商品放入履约白名单。

## 本地启动

1. 复制 `.env.example` 为 `.env`。真实搜索填写 `TAVILY_API_KEY`；AI 规格提取填写 `OPENAI_API_KEY`。密钥只保存在本地，不要提交。
2. 启动 PostgreSQL：`docker compose up -d db`
3. 建立虚拟环境并安装依赖：

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install -e ".[dev]"
   ```

4. 把 `.env` 中配置载入当前终端后启动：

   ```powershell
   $env:DATABASE_URL = "postgresql+psycopg://ecommerce:ecommerce@localhost:5432/ecommerce"
   .\.venv\Scripts\python -m uvicorn app.main:app --reload --env-file .env
   ```

访问 <http://127.0.0.1:8000>。应用启动时会创建当前版本的数据表。

## 真实服务验收前的配置

- [Tavily](https://app.tavily.com/)：注册 Researcher 免费账户并创建 API Key，填入 `.env` 的 `TAVILY_API_KEY`。免费档目前不要求信用卡；共享无密钥模式只适合临时试用，可能因公共日限额耗尽而失败。
- [OpenAI API Platform](https://platform.openai.com/)：单独启用 API 额度并创建项目 Key，填入 `.env` 的 `OPENAI_API_KEY`。默认使用 `gpt-6-luna` 做低成本结构化提取。
- PostgreSQL：启动 Docker Desktop 后运行 `docker compose up -d db`。

所有密钥只在用户本机配置，不要粘贴到聊天、提交到 Git 或放进浏览器代码。

## 当前边界

- Tavily Search 未配置密钥时使用限流的共享试用，仍只保存真实返回结果；正式运行可配置专用密钥。选择 Tavily 是因为当前条款允许长期保存搜索链接、摘要和衍生事实，符合本项目的证据留存要求。
- 搜索结果只形成候选和证据摘要；详细规格、真实报价和代发能力仍需页面读取或人工核验。
- 可读取无需登录的公开商品页面；登录限制、验证码和动态渲染页面会生成待处理事项。
- AI 规格提取使用结构化输出，提取结果附原文证据并标记人工复核；没有 API Key 时明确拒绝调用。
- 淘宝/1688 接入尚未实现。
- 付款、采购、上架、客服发送均不在这一版范围内。

