# QuantTalk - 量化交易策略服务 API

基于 FastAPI 的量化交易策略服务，提供市场数据接口与策略执行服务。

## 技术栈

- Python 3
- FastAPI
- Uvicorn

## 快速部署

```bash
cd /home/ubuntu
python3 -m venv quanttalk-venv
source quanttalk-venv/bin/activate
git clone https://github.com/joohebin/QuantTalk.git
cd QuantTalk
pip install -r requirements.txt
nohup python main.py > /home/ubuntu/quanttalk.log 2>&1 &
```

服务默认运行在 `http://0.0.0.0:8080`

## API 文档

启动后访问：
- Swagger UI: `http://<IP>:8080/docs`
- ReDoc: `http://<IP>:8080/redoc`
