# Ollama AI Chat

ASP.NET Core MVC と FastAPI を組み合わせて開発した
ローカルAIチャットWebアプリです。

Ollamaを利用し、ローカルLLMとのチャット、
Web検索、天気取得、日時取得、計算機能などを実装しています。

---

## 使用技術

- ASP.NET Core MVC
- C#
- Python
- FastAPI
- Ollama
- JavaScript
- HTML
- CSS

---

## 主な機能

- ローカルLLMとの対話
- Web検索
- 天気取得
- 日時取得
- 四則演算
- 質問内容の自動判定

---

## 開発環境

- Windows 11
- Visual Studio 2022
- Python 3.x

---

## 起動方法

### Pythonライブラリ

```bash
pip install -r requirements.txt
```

### FastAPI起動

```bash
uvicorn main:app --reload
```

### ASP.NET Core起動

```bash
dotnet run
```

ブラウザで

```
https://localhost:xxxx
```

へアクセスしてください。