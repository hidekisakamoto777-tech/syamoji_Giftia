# function_app.py — Azure Functions から FastAPI を呼ぶ入口（本番用）
#
# 本番（Azure Functions）では、この app が起点になる。FastAPI のアプリ（main.py）を、
# そのまま Functions の HTTP の入口につなぐだけで、main.py は変えない。
# ローカルは、これまでどおり「uvicorn main:app --reload」で動く（この file は使わない）。

import azure.functions as func

from main import app as fastapi_app

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
