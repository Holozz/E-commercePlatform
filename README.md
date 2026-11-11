# 纸迹工作台

淘宝纸质笔记本试卖的 T02–T04 首版：保存真实货源证据、整理商品规格和报价、确定性核价、记录验样，并只把验样通过的商品放入履约白名单。

## 本地启动

1. 复制 `.env.example` 为 `.env`。如需真实搜索，在本地填写 `BRAVE_SEARCH_API_KEY`，不要提交密钥。
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

## 当前边界

- Brave Search 未配置时明确显示“未连接”，不会填入虚构结果。
- 搜索结果只形成候选和证据摘要；详细规格、真实报价和代发能力仍需页面读取或人工核验。
- AI 规格提取、登录页面读取、淘宝/1688 接入尚未实现。
- 付款、采购、上架、客服发送均不在这一版范围内。

