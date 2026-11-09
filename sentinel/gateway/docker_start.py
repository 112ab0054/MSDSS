"""Docker 啟動入口：確認真正載入模型後，才開放 gateway 接收請求。"""
from contextlib import asynccontextmanager

import uvicorn
from app import app

# 重用原本 lifespan 的套件 SHA 核對、模型載入、自測及 HTTP 連線池。
original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def require_model(application):
    """容器模式必須有模型；失敗便讓 uvicorn 以啟動失敗結束。"""
    async with original_lifespan(application):
        if application.state.predictor is None:
            raise RuntimeError('XGBoost 載入失敗；拒絕啟動 Docker gateway')
        yield


app.router.lifespan_context = require_model

if __name__ == '__main__':
    # 單程序重用模型；不使用多 worker 放大記憶體及分析工作數。
    uvicorn.run(app, host='0.0.0.0', port=8080, workers=1)
