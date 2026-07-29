# 查岗系统 - 后端

💕 给阳阳的查岗系统

## 部署到 Railway

1. 去 [Railway.app](https://railway.app) 登录（可以用GitHub账号）
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择 `yangyang211/check-on-wife-backend` 这个仓库
4. 添加环境变量：
   - `AUTH_TOKEN` = `yangyangCheckOnMe`（或者你自己想一个密码）
5. 等待部署完成，会拿到一个域名，像这样：`https://xxx.up.railway.app`
6. 把这个域名记下来，下一步MCP代理要用

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `AUTH_TOKEN` | 认证密码，iPhone上报时用 | `yangyangCheckOnMe` |
| `PORT` | 端口号 | Railway自动分配 |
