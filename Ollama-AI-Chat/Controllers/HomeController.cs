using System.Diagnostics;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Primitives;
using S.O.R.A._System_Operational_Remote_Assistant_.Models;
using System.Net.Http;
using System.IO;
using System.Text.Json;

namespace S.O.R.A._System_Operational_Remote_Assistant_.Controllers
{
    public class HomeController : Controller
    {
        public IActionResult Index()
        {
            if (System.IO.File.Exists(_filePath))
            {
                try
                {
                    string json = System.IO.File.ReadAllText(_filePath);
                    // 中身が空でないかチェック
                    if (!string.IsNullOrWhiteSpace(json))
                    {
                        _messageLog = JsonSerializer.Deserialize<List<ChatMessage>>(json) ?? new List<ChatMessage>();
                    }
                }
                catch (JsonException)
                {
                    // もし読み込みに失敗したら、履歴を空にして新しく始める
                    _messageLog = new List<ChatMessage>();
                }
            }

            // 以前作った「起動時の挨拶」
            if (_messageLog.Count == 0)
            {
                _messageLog.Add(new ChatMessage { Sender = "S.O.R.A.：", Text = "システム復旧完了。お帰りなさい。" });
            }

            // 読み込んだ（あるいは空の）履歴を画面に渡す
            ViewData["ChatLog"] = _messageLog;
            return View();
        }

        public IActionResult Privacy()
        {
            return View();
        }

        [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
        public IActionResult Error()
        {
            return View(new ErrorViewModel { RequestId = Activity.Current?.Id ?? HttpContext.TraceIdentifier });
        }
        public class ChatMessage { public string Sender  { get; set; }  public string Text { get; set; } }
        // クラスの直下に配置（staticにすることで、ページを移動しても消えないようにする）
        private static List<ChatMessage> _messageLog = new List<ChatMessage>();
        // 保存先の住所を指定（@を付けるのがコツ）
        private static string _filePath =
               Path.Combine(AppContext.BaseDirectory, "chat_history.json");
        [HttpPost]
        public async Task<IActionResult> SendMessage(string UserMessage)
        {
            if (string.IsNullOrWhiteSpace(UserMessage)) return RedirectToAction("Index");

            // 1. ユーザーの発言を履歴に追加
            _messageLog.Add(new ChatMessage { Sender = "あなた：", Text = UserMessage });

            using var client = new HttpClient();
            try
            {
                // 2. 直近の履歴（最大10件）をJSONにまとめて送信準備
                var historyData = _messageLog.TakeLast(10).ToList();
                var jsonOptions = new JsonSerializerOptions { PropertyNamingPolicy = null };
                string jsonPayload = JsonSerializer.Serialize(historyData, jsonOptions);
                var content = new StringContent(jsonPayload, System.Text.Encoding.UTF8, "application/json");

                // 3. Pythonの /chat 窓口へ送信
                var response = await client.PostAsync("http://127.0.0.1:8000/chat", content);
                var result = await response.Content.ReadAsStringAsync();

                // 4. AIの返答を履歴に追加
                _messageLog.Add(new ChatMessage { Sender = "S.O.R.A.：", Text = result });
            }
            catch (Exception ex)
            {
                _messageLog.Add(new ChatMessage { Sender = "System：", Text = "通信エラーが発生しました。" + ex.Message });
            }

            // 履歴の保存
            System.IO.File.WriteAllText(
                _filePath,
                JsonSerializer.Serialize(_messageLog)
            );

            ViewData["ChatLog"] = _messageLog;
            return View("Index");
        }
    }
}
