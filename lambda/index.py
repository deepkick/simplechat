# lambda/index.py
import json
import os
import urllib.request, urllib.error

FASTAPI_URL = (
    os.environ.get("FASTAPI_URL", "https://e484-104-197-89-231.ngrok-free.app").rstrip(
        "/"
    )
    + "/generate"
)  # Swagger UI で確認したエンドポイント


# ──────────────────────────────────────────────
def lambda_handler(event, context):
    try:
        # ① フロントエンドから届くリクエストを取得
        body = json.loads(event["body"])
        message = body["message"]  # 必須
        history = body.get("conversationHistory", [])  # list[dict]

        # ② Colab 側 API へ渡す JSON 生成
        payload = {
            "prompt": message,  # まずは単一プロンプトだけ渡す
            "max_new_tokens": 512,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        req = urllib.request.Request(
            FASTAPI_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        # ③ API コール
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_json = json.loads(resp.read())

        # ④ Colab から返るキー名を取得（例: generated_text）
        assistant_reply = (
            resp_json.get("generated_text")
            or resp_json.get("text")
            or resp_json.get("reply")
        )
        if not assistant_reply:
            raise ValueError(f"Unexpected response shape: {resp_json}")

        # 会話履歴を更新してフロントへ返却
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": assistant_reply})

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "response": assistant_reply,
                    "conversationHistory": history,
                }
            ),
        }

    # ─ エラーハンドリング ─
    except (urllib.error.URLError, ValueError, KeyError) as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"success": False, "error": str(e)}),
        }
