from fastapi import FastAPI, Request
import ollama
from ddgs import DDGS
from datetime import datetime
import requests
import re
import ast
import operator

app = FastAPI()

def search_net(query: str):
    results = []
    urls = []
    try:
        with DDGS() as ddgs:
            # timelimit='m' (1ヶ月以内) で2023年の情報を物理遮断
            for r in ddgs.text(query, region="jp-jp", max_results=5, timelimit='m'):
                results.append(f"事実: {r.get('title','')} - {r.get('body','')}")
                urls.append(r.get("href",""))
    except: pass
    return "\n".join(results), urls

def detect_tool(query: str):

    q = query.lower()

    # 天気
    if "天気" in q:
        return "weather"

    # 日時
    if "何時" in q or "時間" in q or "日付" in q or "曜日" in q:
        return "datetime"

    # 計算
    if re.fullmatch(r"[0-9\+\-\*\/\(\)\.\s]+", q):
        return "calc"

    # 最新情報
    latest_words = [
        "最新",
        "ニュース",
        "配信",
        "発売",
        "switch",
        "switch2"
    ]

    if any(word in q for word in latest_words):
        return "search"

    return "chat"

def get_datetime_answer(query: str):

    now = datetime.now()

    if "何時" in query or "時間" in query:
        return f"現在時刻は {now.strftime('%H:%M')} です。"

    if "曜日" in query:
        weekdays = [
            "月曜日",
            "火曜日",
            "水曜日",
            "木曜日",
            "金曜日",
            "土曜日",
            "日曜日"
        ]
        return f"今日は{weekdays[now.weekday()]}です。"

    if "日付" in query or "今日" in query:
        return f"今日は{now.strftime('%Y年%m月%d日')}です。"

    return None

def calculate_expression(expression: str):

    try:
        # 利用できる演算子
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_node(node):
            if isinstance(node, ast.Constant):
                return node.value

            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](
                    eval_node(node.left),
                    eval_node(node.right)
                )

            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](
                    eval_node(node.operand)
                )

            else:
                raise ValueError("対応していない式です。")

        tree = ast.parse(expression, mode="eval")
        result = eval_node(tree.body)

        return f"計算結果：{result}"

    except Exception:
        return "計算できませんでした。"
    
def get_weather():

    # 札幌駅
    latitude = 43.0687
    longitude = 141.3508

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m,weather_code"
    )

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        temp = data["current"]["temperature_2m"]
        code = data["current"]["weather_code"]

        weather_dict = {
            0: "快晴",
            1: "晴れ",
            2: "晴れ時々曇り",
            3: "曇り",
            45: "霧",
            48: "霧",
            51: "小雨",
            61: "雨",
            71: "雪",
            95: "雷雨"
        }

        weather = weather_dict.get(code, "不明")

        return f"札幌の現在の天気は『{weather}』、気温は{temp}℃です。"

    except:
        return "天気情報を取得できませんでした。"

@app.post("/chat")
async def chat(request: Request):
    # 体内時計を今日に固定
    today = datetime.now().strftime("%Y年%m月%d日")
    history = await request.json()
    user_input = history[-1]["Text"]
        
    tool = detect_tool(user_input)
    print(tool)

    if tool == "datetime":
        return get_datetime_answer(user_input)
    
    if tool == "calc":
        return calculate_expression(user_input)
    
    if tool == "weather":
        return get_weather()

    # 必要な時だけ検索する
    search_data = ""
    urls = []

    if tool == "search":
        search_data, urls = search_net(user_input)

    system_instruction = f"""
    あなたはAIアシスタント『S.O.R.A.』です。

    現在の日付は【{today}】です。

    ルール
    ・ユーザーの質問にだけ答えてください。
    ・不要な情報は付け加えないでください。
    ・会話履歴を参考に回答してください。
    ・検索結果がある場合は優先してください。
    ・検索結果がない場合は自分の知識で回答してください。
    ・自然な日本語で簡潔に回答してください。
    ・回答は引用符（「」や""）で囲まないでください。
    ・回答本文だけを出力してください。

    検索結果
    {search_data if search_data else "なし"}
    """
    messages = [
        {
            "role": "system",
            "content": system_instruction
        }
    ]

    for item in history[-10:]:

        role = "assistant"

        if item["Sender"] == "あなた：":
            role = "user"

        messages.append({
            "role": role,
            "content": item["Text"]
        })

    # 3. 生成（「回答：」から先を書かせる）
    res = ollama.chat(
        model="qwen3:8b",
        messages=messages
    )
    
    # AIの出力を取得
    raw_answer = res["message"]["content"].strip()

    # --- 物理フィルタ：ここが一番大事 ---
    # 万が一AIが「[確定事実]～」などと喋り始めても、
    # 最後の「回答：」というキーワードより後ろだけをユーザーに返す
    if "回答：" in raw_answer:
        answer = raw_answer.split("回答：")[-1].strip()
    else:
        answer = raw_answer

      # 出典はURL1つだけに絞る（ごちゃつき防止）
    source = f"\n\n【出典】\n{urls[0]}" if urls else ""
    
    return answer + source