# 🧩 TG-WebDevelop

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.x-green?logo=flask)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

> **用最简单的方式，从 0 部署一套『AI 芯片逻辑生成 ✕ 可视化』Web 应用**
>
> 只需跟着下面的 **5 分钟指北**，你的朋友就能把项目跑起来；如果需要上线到正式服务器，也有一键 `Docker`& `systemd` 示例可以直接复用。

---

## 📖 项目简介

TG‑WebDevelop 是一个基于 **Flask** 的全栈小应用：

* 通过 **OpenAI / SiliconFlow** 大模型，把自然语言描述转成芯片逻辑 JSON
* 内置 **SVG 渲染器**，实时预览逻辑图
* 带用户系统（注册 / 登录 / 记忆 API‑Key）
* 管理员后台可查看生成记录 & 访问统计

<details>
  <summary>主要技术栈</summary>

| Layer    | Tech                               |
| -------- | ---------------------------------- |
| Backend  | Flask · Flask‑Login · SQLAlchemy   |
| AI       | OpenAI SDK / SiliconFlow REST      |
| DB       | SQLite (自动放在 `instance/`)          |
| Frontend | Jinja2 · Vanilla JS · Tailwind CSS |
| Misc     | Graphviz (生成 SVG)                  |

</details>

---

## 🚀 快速开始（本地开发）

> 下文假设你已安装 **Python ≥3.10** & **Git**。

```bash
# 1. 克隆仓库
$ git clone https://github.com/xunxiing/tg-webdevelop.git
$ cd tg-webdevelop

# 2. 创建虚拟环境（可选但推荐）
$ python -m venv .venv && \
  source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
$ pip install -r requirements.txt  # requirements 文件在根目录

# 4. 设置环境变量（首次运行就两行）
$ export ADMIN_USER=admin  # 管理后台账户
$ export ADMIN_PASS=ChangeMe123  # 强烈建议修改！

# 若需要指定 OpenAI Key，可额外：
$ export OPENAI_API_KEY=sk-xxx

# 5. 运行
$ python app.py  # 默认 http://127.0.0.1:5000
```

第一次启动时，脚本会自动：

1. 在 `instance/` 目录创建 SQLite 数据库、`users.json`、`api_keys.json` 等文件。
2. 自动建表（`models.py` 中的 `db.create_all()`）
3. 初始化访问计数器。

打开浏览器访问 **`/`** 就能看到首页啦！

---

## 🐳 Docker 一键部署

如果朋友懒得装 Python，可以直接用 Docker：

```dockerfile
# Dockerfile (贴到项目根目录)
FROM python:3.10-slim AS base
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    ADMIN_USER=admin \
    ADMIN_PASS=ChangeMe123
EXPOSE 5000
CMD ["python", "app.py"]
```

构建并运行：

```bash
$ docker build -t tg-webdevelop .
$ docker run -d -p 80:5000 --name tg_app \
  -e ADMIN_USER=admin -e ADMIN_PASS=SuperSecret \
  -e OPENAI_API_KEY=sk-xxx tg-webdevelop
```

> **Tips**
> *若需要持久化数据库，把 `instance/` 挂到宿主机卷即可：*
> `-v $(pwd)/instance:/app/instance`

---

## ☁️ 生产环境部署（Gunicorn + Nginx + systemd）

### 1. Gunicorn Service

```ini
# /etc/systemd/system/tg_web.service
[Unit]
Description=TG-WebDevelop Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/tg-webdevelop
Environment="ADMIN_USER=admin" "ADMIN_PASS=ChangeMe123" "OPENAI_API_KEY=sk-xxx"
ExecStart=/srv/tg-webdevelop/.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tg_web
```

### 2. Nginx (反向代理 + HTTPS)

```nginx
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass       http://127.0.0.1:5000;
        proxy_set_header Host            $host;
        proxy_set_header X-Real-IP       $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

用 Certbot 一键签发 HTTPS：`sudo certbot --nginx -d example.com`。

---

## 🔧 配置文件 & 路径

| 文件/目录              | 作用                            |
| ------------------ | ----------------------------- |
| `requirements.txt` | Python 依赖列表 citeturn7view0 |
| `instance/*`       | 运行时产生的 DB / JSON / 访问计数等      |
| `templates/`       | Jinja2 前端模板                   |
| `static/`          | CSS / JS / 图片                 |
| `app.py`           | Flask 入口，全部路由定义               |
| `models.py`        | SQLAlchemy ORM 模型             |
| `ai_service.py`    | 与 OpenAI / SiliconFlow 通信逻辑   |

---

## 📝 常见问题 FAQ

<details>
  <summary><strong>Q1: 如何更换大模型或代理？</strong></summary>
在 `ai_service.py` 修改 `SILICONFLOW_BASE_URL` 或自行实现 `generate_chip_json_stream`。
</details>

<details>
  <summary><strong>Q2: 数据库放哪？</strong></summary>
默认在 `instance/app_data.db`。生产环境建议迁移到 MySQL/PostgreSQL，并更新 `SQLALCHEMY_DATABASE_URI`。
</details>

<details>
  <summary><strong>Q3: 登录后 401？</strong></summary>
确认浏览器允许 Cookie，并检查服务端 `SECRET_KEY` 是否持久化（生产时建议写死或用环境变量）。
</details>

---

## 🙌 贡献

欢迎 Issue / PR！如果 README 帮到你，记得点个 ⭐ Star。

## 📄 License

[MIT](LICENSE)
