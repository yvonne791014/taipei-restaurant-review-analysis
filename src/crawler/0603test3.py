import json
from pathlib import Path
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline


def json_to_csv(json_path: Path, csv_path: Path):
    """將 JSON 檔案轉換為 CSV 檔案"""
    print(f" 正在將 {json_path.name} 轉換為 {csv_path.name}...")
    if not json_path.exists():
        print(f" 找不到來源 JSON 檔案：{json_path}")
        return False
    try:
        df = pd.read_json(json_path, encoding="utf-8")
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f" 轉換成功！已生成 CSV 檔案：{csv_path}")
        return True
    except Exception as e:
        print(f" 轉換失敗，錯誤訊息：{e}")
        return False


def main():
    current_dir = Path(__file__).resolve().parent

    # ==========================================
    # 功能一：JSON 轉 CSV
    # ==========================================
    input_json = current_dir / "Zhongshan.json"  
    raw_csv = current_dir / "Zhongshan_comments.csv"  

    json_to_csv(input_json, raw_csv)
    print("=" * 30)

    # ==========================================
    # 功能二：差評多分類機器學習管線
    # ==========================================
    if not raw_csv.exists():
        print(f"⚠️ 找不到 {raw_csv.name}，無法進行後續的模型預測。")
        return

    df = pd.read_csv(raw_csv)

    # 基礎防錯：補空值並剃除絕對空白留言
    df["comment_text"] = df["comment_text"].fillna("").astype(str).str.strip()
    df = df[df["comment_text"].str.len() > 1].copy()

    # 🎯 核心修改：建立多分類的「差評教材」
    # 這裡的每一句範例，都要精準對應到右邊的差評類別
    X_train = [
        # --- 店員態度 ---
        "店員態度很差，臉臭得像欠他錢一樣",
        "服務生不理人，叫好幾次都假裝沒聽到",
        "櫃檯人員口氣非常不客氣，體驗極差",
        
        # --- 衛生 ---
        "桌子沒擦乾淨，摸起來黏黏的，環境很髒",
        "看到小強在地上爬，衛生堪憂",
        "餐具上面還有殘留的油漬，很不衛生",
        
        # --- 排隊 ---
        "排隊等太久了，在外面站了一個小時氣死",
        "動線規劃很爛，排隊點餐一團混亂",
        "等位置等很久，明明有空桌卻不放人進去",
        
        # --- 送餐速度 ---
        "送餐速度太慢，等了半小時點的漢堡才來",
        "上菜超慢，飲料都喝完了主餐還沒上",
        "出餐速度有夠久，趕時間的人絕對不要來",
        
        # --- 停車 ---
        "附近非常難停車，找車位找了半天",
        "沒有附設停車場，開車過來超不方便",
        "週邊車位一位難求，停車很不方便",
        
        # --- 價格 ---
        "價格太貴了，CP值極低，不值這個價",
        "份量很少卻賣這麼貴，搶錢嗎",
        "價錢偏高，吃完覺得空虛",
        
        # --- 其他（不屬於以上差評的，例如好評或廣告） ---
        "東西很好吃，大力推薦！",
        "超級好吃，下次還會再來",
        "餐點很美味"
    ]
    
    # 標籤直接改成你想分類的類別名稱（必須與上面 X_train 的句子嚴格一一對應）
    y_train = [
        "店員態度", "店員態度", "店員態度",
        "衛生", "衛生", "衛生",
        "排隊", "排隊", "排隊",
        "送餐速度", "送餐速度", "送餐速度",
        "停車", "停車", "停車",
        "價格", "價格", "價格",
        "其他", "其他", "其他"
    ]

    # 建立多分類機器學習管線
    classifier_pipeline = Pipeline([
        ("tfidf", TfidfVectorizer()), 
        ("clf", LogisticRegression(class_weight="balanced")) # 自動平衡各類別的權重
    ])

    # 訓練多分類模型
    classifier_pipeline.fit(X_train, y_train)

    if "comment_text" in df.columns:
        # 讓 AI 幫每條評論打上分類標籤（店員態度、衛生、排隊... 或 其他）
        df["bad_comment_type"] = classifier_pipeline.predict(df["comment_text"])

        # 篩選：我們只需要 6 大差評，所以要把判定為「其他」的正常評論刪除
        df_bad_only = df[df["bad_comment_type"] != "其他"].copy()

        # 匯出結果
        cleaned_csv = current_dir / "classified_bad_comments.csv"
        df_bad_only.to_csv(cleaned_csv, index=False, encoding="utf-8")
        
        print(f"📊 原始資料總數: {len(df)} 筆")
        print(f"🎉 成功偵測並分類的差評總數: {len(df_bad_only)} 筆")
        print("\n各類別差評統計數量：")
        print(df_bad_only["bad_comment_type"].value_counts())
        print(f"\n💾 已生成分類完成的差評檔案：{cleaned_csv.name}")
    else:
        print("❌ 錯誤：CSV 檔案中找不到 'comment_text' 欄位！")

    print("=" * 30)


if __name__ == "__main__":
    main()