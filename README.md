# MCP OpenProject Server

基于 FastMCP 框架的 OpenProject MCP 服务器，为 AI 助手提供完整的项目管理功能。

## 🚀 快速部署

### Smithery.ai (推荐)
```bash
# 推送代码到 GitHub
git add .
git commit -m "Initial OpenProject MCP server"
git push origin main

# 部署到 Smithery.ai
npm install -g @smithery/cli
smithery deploy
```

### 本地测试
```bash
# 环境配置
export OPENPROJECT_BASE_URL=http://localhost:8090
export OPENPROJECT_API_KEY=your-api-key

# 安装依赖并运行
pip install -r requirements.txt
python -m openproject.server
```

## 📋 项目结构

```
mcp-openproject/
├── spec.yml              # OpenProject OpenAPI 规范
├── smithery.yaml         # Smithery.ai 部署配置
├── Dockerfile            # Docker 容器配置
├── requirements.txt       # Python 依赖
├── openproject/          # MCP 服务器代码
│   ├── __init__.py
│   ├── server.py          # 主服务器
│   └── config.py          # 配置管理
└── docs/                  # 项目文档
```

## 📚 文档

- [业务需求](docs/brd.md) - 项目需求和目标
- [技术设计](docs/technical-design.md) - 详细技术实现
- [部署指南](docs/deployment-guide.md) - Smithery.ai 部署说明
- [项目结构](docs/project-structure.md) - 项目目录说明

## 🎯 功能特性

- ✅ 完整 OpenProject API 覆盖
- ✅ 自动 OpenAPI → MCP 转换
- ✅ HTTP 远程访问支持
- ✅ 配置验证和错误处理

## 📄 许可证

MIT License