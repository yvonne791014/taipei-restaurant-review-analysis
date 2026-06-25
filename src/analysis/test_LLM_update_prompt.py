import json
import os
import time
from dotenv import load_dotenv  # 引入載入環境變數的套件 (Import dotenv)
from google import genai
from google.genai import types
import pymysql  # 引入 MySQL 連線套件 (Import pymysql)

# 自動尋找並載入 .env 檔案中的環境變數
load_dotenv()

def init_gemini_client():
    """
    函式 1：初始化並回傳 Gemini 客戶端
    """
    # 從環境變數抓取變數值，避免密鑰外洩 (Secure API key)
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError("❌ 錯誤：在環境變數或 .env 檔案中找不到 'GEMINI_API_KEY'！")
        
    return genai.Client(api_key=api_key)


def get_reviews_from_db():
    """
    函式 2：從 MySQL 資料庫撈取評論資料（純讀取測試）
    """
    # 從環境變數讀取資料庫設定，完全不寫死連線資訊 (Database settings)
    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        passwd=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME", "REVIEW"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor  # 讓撈出來的資料自動變成 dict 格式
    )
    
    try:
        with connection.cursor() as cursor:
            # 使用你截圖中的精準 SQL 語法 (Targeted SQL query)
            sql = """
            SELECT review_id, restaurant_id, review_score, review_content
            FROM REVIEW.reviews
            where review_score <= 3 and review_content is not null
            order by review_score desc, review_id desc;
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        connection.close()  # 關閉資料庫連線 (Close database connection)


def analyze_review_with_gemini(client, text_content, review_id):
    """
    函式 3：負責將單筆評論丟給 Gemini 進行多面向情感分析
    """
    prompt = f"""
你是一個精準的餐廳評論多面向情感分析器 (Aspect-Based Sentiment Analysis Analyzer)。
請分析下方提供的餐廳評論，並嚴格按照指定的 JSON 格式輸出。

【分析面向與定義】
- food (食物): 包含口味、食材、好不好吃、多汁、柴等。
- price (價格): 包含划算、貴、便宜、CP值高低等。
- service (服務): 包含服務態度、速度、店員表現等。
- hygiene (衛生): 包含乾淨、髒亂、餐具衛生等。
- queue (排隊): 包含等很久、排隊人潮、排很久等。
- environment (環境): 包含裝潢、氣氛、噪音、擁擠程度等.
- parking (停車): 包含好不好停車、停車場等。

【情感分類標籤與輸出規則】
每個面向的情感 (sentiment) 只能從以下三個標籤中選擇一個，並請嚴格遵守數字轉換與隱藏規則：
- 正面評價：請輸出數字 1
- 負面評價：請輸出數字 -1
- 完全沒有提到該面向："not_mentioned"，且**該面向必須完全從輸出的 JSON 中移除（不需回傳）**。

【關鍵字規則】
在 keywords 陣列中，只填入評論中與該面向直接相關的「原始中文字詞或短句」。

【輸入資料】
- 評論 ID: "{review_id}"
- 原始評論內容: "{text_content}"

【輸出的 JSON 格式樣本】
{{
  "review_id": "{review_id}",
  "food": {{ "sentiment": -1, "keywords": ["東西不怎麼樣"] }},
  "price": {{ "sentiment": -1, "keywords": ["價格貴"] }},
  "service": {{ "sentiment": 1, "keywords": ["服務好"] }},
  "queue": {{ "sentiment": 1, "keywords": ["上菜速度快"] }}
}}

【重要注意事項】
1. 請務必將 JSON 中的 "review_id" 欄位值，替換為上方【輸入資料】中實際傳入的 "{review_id}" 變數內容，不可沿用樣本中的字串。
2. 輸出時請只回傳標準 JSON 格式字串，不要包含任何 markdown 標籤（如 ```json）或額外的解釋文字。
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
    函式 4：主程式控制流程
    """
    # 1. 初始化 Gemini Client
    try:
        client = init_gemini_client()
    except Exception as e:
        print(e)
        return

    # 2. 從 MySQL 讀取資料
    try:
        reviews_data = get_reviews_from_db()
        print(f"✅ 成功從資料庫 [REVIEW.reviews] 讀取資料！總共有 {len(reviews_data)} 筆符合條件。")
    except Exception as e:
        print(f"❌ 錯誤：資料庫連線或查詢失敗：{e}")
        return

    # 3. 過濾有效評論
    valid_reviews = [
        r for r in reviews_data 
        if r.get("review_content").strip() != ""
    ]
    print(f"📊 排除空字串後，有效低星評論共有 {len(valid_reviews)} 筆。\n")

    # 4. 開始迴圈測試
    max_tests = 3
    print(f"=== 🚀 開始使用香香的 Gemini 測試前 {max_tests} 筆有效低星評論 (純印出，不寫入) ===\n")

    for idx, review in enumerate(valid_reviews[:max_tests], start=1):
        review_id = review.get("review_id", "未知ID")
        restaurant_id = review.get("restaurant_id", "未知餐廳")
        review_text = review["review_content"]
        review_rating = review.get("review_score", "無")
        
        # 配合資料庫欄位，改印出 review_id 與 restaurant_id
        print(f"【測試第 {idx} 筆】 評論ID：{review_id} | 餐廳ID：{restaurant_id} ({review_rating} 星)")
        print(f"📝 原始評論：\n\"{review_text}\"")
        
        # 執行分析
        try:
            analysis_result = analyze_review_with_gemini(client, review_text, review_id)
            print("✨ Gemini 結構化分析結果：")
            print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"💥 處理時發生錯誤：{e}")
            
        print("-" * 60 + "\n")
        
        # 每次呼叫完強迫休息 2 秒 (Sleep 2s)
        if idx < max_tests:
            print("⏳ 休息 2 秒後繼續下一筆...")
            time.sleep(2)

    print("=== 🏁 Gemini 測試結束 ===")


if __name__ == "__main__":
    main()