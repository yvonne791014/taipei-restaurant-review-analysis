import json
import os
import time
from dotenv import load_dotenv  # 引入載入環境變數的套件 (Import dotenv)
from google import genai
from google.genai import types

# 自動尋找並載入 .env 檔案中的環境變數
load_dotenv()

def init_gemini_client():
    """
    函式 1：初始化並回傳 Gemini 客戶端
    """
    # 從系統或 .env 中抓取變數值
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("❌ 錯誤：在環境變數或 .env 檔案中找不到 'GEMINI_API_KEY'！")
        
    # 初始化 Client 並回傳
    return genai.Client(api_key=api_key)


def analyze_review_with_gemini(client, text_content):
    """
    函式 2：負責將單筆評論丟給 Gemini 進行多面向情感分析
    """
    prompt = f"""
你是一個精準的餐廳評論多面向情感分析器 (Aspect-Based Sentiment Analysis Analyzer)。
請分析下方提供的餐廳評論，並嚴格按照指定的 JSON 格式輸出。

【分析面向與定義】
- food (食物): 包含口味、食材、好不好吃、多汁、柴等。
- price (價格): 包含劃算、貴、便宜、CP值高低等。
- service (服務): 包含服務態度、速度、店員表現等。
- hygiene (衛生): 包含乾淨、髒亂、餐具衛生等。
- queue (排隊): 包含等很久、排隊人潮、排很久等。
- environment (環境): 包含裝潢、氣氛、噪音、擁擠程度等。
- parking (停車): 包含好不好停車、停車場等。

【情感分類標籤】
每個面向的情感 (sentiment) 只能從以下三個標籤中選擇一個：
- "positive" (正面的評價)
- "negative" (負面的評價)
- "not_mentioned" (完全沒有提到該面向)

【關鍵字規則】
在 keywords 陣列中，只填入評論中與該面向直接相關的「原始中文字詞或短句」。如果該面向為 "not_mentioned"，則 keywords 必須為空陣列 []。

【原始評論】
"{text_content}"

【輸出的 JSON 格式樣本】
{{
  "food": {{ "sentiment": "not_mentioned", "keywords": [] }},
  "price": {{ "sentiment": "not_mentioned", "keywords": [] }},
  "service": {{ "sentiment": "not_mentioned", "keywords": [] }},
  "hygiene": {{ "sentiment": "not_mentioned", "keywords": [] }},
  "queue": {{ "sentiment": "not_mentioned", "keywords": [] }},
  "environment": {{ "sentiment": "not_mentioned", "keywords": [] }},
  "parking": {{ "sentiment": "not_mentioned", "keywords": [] }}
}}
"""

    # 呼叫 Gemini API
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            temperature=0.0                      
        ),
    )
    
    return json.loads(response.text)


def main():
    """
    函式 3：主程式控制流程
    """
    # 1. 初始化 Gemini Client
    try:
        client = init_gemini_client()
    except Exception as e:
        print(e)
        return

    # 2. 讀取 JSON 檔案
    file_path = "data/測試用評論.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reviews_data = json.load(f)
        print(f"✅ 成功讀取檔案！總共有 {len(reviews_data)} 筆資料。")
    except FileNotFoundError:
        print(f"❌ 錯誤：找不到檔案 '{file_path}'，請確認執行路徑是否正確。")
        return

    # 3. 過濾有效評論（加上 1~3 顆星的篩選）
    valid_reviews = [
        r for r in reviews_data 
        if r.get("text") is not None 
        and r["text"].strip() != ""
        and r.get("rating") in [1, 2, 3]  # 👈 這裡加入了星星過濾！只挑 1、2、3 顆星
    ]
    print(f"📊 含有評論文字且評分為 1~3 星的資料共有 {len(valid_reviews)} 筆。\n")

    # 4. 開始迴圈測試
    max_tests = 10
    print(f"=== 🚀 開始使用香香的 Gemini 測試前 {max_tests} 筆有效低星評論 (不寫入檔案) ===\n")

    for idx, review in enumerate(valid_reviews[:max_tests], start=1):
        author_name = review.get("author", {}).get("name", "匿名")
        review_text = review["text"]
        review_rating = review.get("rating", "無")
        
        print(f"【測試第 {idx} 筆】 評論者：{author_name} ({review_rating} 星)")
        print(f"📝 原始評論：\n\"{review_text}\"")
        
        # 執行分析
        try:
            analysis_result = analyze_review_with_gemini(client, review_text)
            print("✨ Gemini 結構化分析結果：")
            print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"💥 處理時發生錯誤：{e}")
            
        print("-" * 60 + "\n")
        
        # 根據要求修改：每次呼叫完強迫休息 5 秒 (Sleep 5s)
        if idx < max_tests:
            print("⏳ 休息 5 秒後繼續下一筆...")
            time.sleep(5)

    print("=== 🏁 Gemini 測試結束 ===")


if __name__ == "__main__":
    main()