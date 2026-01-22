# LifeLens 项目部署指南

本指南将帮助您使用 Docker 快速将 LifeLens 部署到服务器。

## 1. 准备工作

### 服务器要求
- 操作系统：Ubuntu 20.04/22.04 (推荐) 或 CentOS 7+
- 内存：至少 2GB
- 已安装 Git (可选)

### 必须安装的软件
在您的服务器上运行以下命令安装 Docker：

```bash
# Ubuntu 安装 Docker
curl -fsSL https://get.docker.com | bash
# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

## 2. 部署步骤

### 第一步：上传代码
将整个项目文件夹上传到服务器（例如 `/root/lifelens`）。您可以使用 SCP、FTP 或 Git。

### 第二步：配置环境变量
在项目根目录（即 `docker-compose.yml` 所在的目录）创建一个 `.env` 文件，填入您的阿里云 DashScope API Key：

```bash
# 在服务器项目根目录执行
echo "DASHSCOPE_API_KEY=您的实际API密钥" > .env
```

### 第三步：启动服务
在项目根目录下运行：

```bash
# 构建并启动容器（后台运行）
docker compose up -d --build
```

> 注意：如果您使用的是旧版 Docker，可能需要使用 `docker-compose` 而不是 `docker compose`。

### 第四步：验证部署
- **前端访问**：打开浏览器访问 `http://您的服务器IP`
- **后端 API**：`http://您的服务器IP/api/`

## 3. 常见问题排查

**Q: 容器启动失败？**
查看日志：
```bash
docker compose logs -f
```

**Q: 只有后端，想单独测试？**
```bash
docker compose logs backend
```

**Q: 修改了代码如何更新？**
```bash
# 重新构建并重启
docker compose down
docker compose up -d --build
```

**Q: 微信小程序无法访问？**
微信小程序强制要求 HTTPS。您需要：
1. 购买或申请免费 SSL 证书（如 Let's Encrypt）。
2. 修改 `nginx.conf` 配置 SSL 证书（监听 443 端口）。
3. 重新启动 Nginx 容器。
