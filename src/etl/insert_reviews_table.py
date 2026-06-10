import os
import pandas as pd
import pymysql

# 1. 資料庫連線設定 (請根據你的團隊環境修改)
host = 'localhost'
port = 3306
user = 'root'
passwd = 'password'
db = 'REVIEW'
charset = 'utf8mb4'

# 2. ETL 流程主程式
def etl_csv_to_reviews_pymysql(csv_path):
    print("🚀 開始執行 reviews 主表資料清洗與轉換...")
    
    # 相對路徑防呆機制
    if not os.path.exists(csv_path):
        print(f"❌ 錯誤：找不到 CSV 檔案，請確認專案目錄結構！")
        print(f"🔍 系統目前查找的動態路徑為: {csv_path}")
        return

    # 讀取原始爬蟲 CSV
    df = pd.read_csv(csv_path)
    
    # 過濾掉主鍵 review-ID 為空的髒資料
    df = df.dropna(subset=['review-ID'])
    
    # 建立一個新的 DataFrame 來對應你的【最新版】DB 欄位
    cleaned_df = pd.DataFrame()
    
    # 欄位對應與清洗 (完全對應最新 SQL 欄位名稱)
    cleaned_df['review_id'] = df['review-ID'].str.strip()
    cleaned_df['restaurant_id'] = df['restaurant_id'].str.strip()
    
    # total_stars 處理：轉成數字，若有空值先填 0（因 SQL 設定 NOT NULL），型態轉整數 (tinyint)
    cleaned_df['total_stars'] = pd.to_numeric(df['total_stars'], errors='coerce').fillna(0).astype(int)
    
    # review_content 處理：將 NaN 轉為 None (在 MySQL 中會呈現為 NULL)
    cleaned_df['review_content'] = df['text'].astype(object).where(df['text'].notna(), None)
    
    # 食物、服務、環境評分處理：依據最新 Schema 規範 (default null)
    # 轉為數字，將無法轉換的髒資料或空值(NaN)換成 Python 的 None，寫入 MySQL 時就會是完美的 NULL
    cleaned_df['food_rating'] = pd.to_numeric(df['food_rating'], errors='coerce').astype(object).where(pd.to_numeric(df['food_rating'], errors='coerce').notna(), None)
    cleaned_df['service_rating'] = pd.to_numeric(df['service_rating'], errors='coerce').astype(object).where(pd.to_numeric(df['service_rating'], errors='coerce').notna(), None)
    cleaned_df['atmosphere_rating'] = pd.to_numeric(df['atmosphere_rating'], errors='coerce').astype(object).where(pd.to_numeric(df['atmosphere_rating'], errors='coerce').notna(), None)
    
    print("📊 本地端資料清洗完成！準備連線至 MySQL 檢查外鍵約束...")

    # 3. 使用純 PyMySQL 連線並寫入資料庫
    try:
        # 連線參數更新為最新版 (database & password)，消滅 DeprecationWarning
        conn = pymysql.connect(
            host=host, 
            port=port, 
            user=user, 
            password=passwd, 
            database=db, 
            charset=charset
        )
        cursor = conn.cursor()
        
        # 🛠️ 【外鍵防呆機制】先撈出 low_rating_restaurant 裡面目前有哪些餐廳 ID
        cursor.execute("SELECT restaurant_id FROM low_rating_restaurant")
        valid_restaurant_ids = {row[0] for row in cursor.fetchall()}  # 轉成 set 加快比對速度
        
        # 🛠️ 【自動過濾】利用 Pandas 比對，只保留存在於主表的餐廳評論
        initial_count = len(cleaned_df)
        cleaned_df = cleaned_df[cleaned_df['restaurant_id'].isin(valid_restaurant_ids)]
        filtered_count = len(cleaned_df)
        
        if filtered_count == 0:
            print("⚠️ 警告：這批 CSV 裡面的餐廳 ID，在 [low_rating_restaurant] 表中通通找不到！")
            print("💡 請組員先跑「餐廳主表」的爬蟲寫入腳本，否則評論無法寫入。")
            return
            
        if initial_count != filtered_count:
            print(f"🧹 外鍵保護發動：已自動過濾掉 {initial_count - filtered_count} 筆不存在於主表的餐廳評論（避免 1452 錯誤）")
        
        # 將過濾後安全的資料轉換為 Python 的 Tuple 列表
        data_tuples = list(cleaned_df.itertuples(index=False, name=None))
        print(f"📦 準備批量寫入/更新 {len(data_tuples)} 筆合法評論...")

        # 準備 SQL 語法 (欄位名稱已更新為最新版，並改用 ON DUPLICATE KEY UPDATE 避免重複執行時卡住)
        sql = """
        INSERT INTO reviews 
        (review_id, restaurant_id, total_stars, review_content, food_rating, service_rating, atmosphere_rating) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            total_stars = VALUES(total_stars),
            review_content = VALUES(review_content),
            food_rating = VALUES(food_rating),
            service_rating = VALUES(service_rating),
            atmosphere_rating = VALUES(atmosphere_rating),
            updated_at = NOW();


        """
        
        # 批量寫入 (Bulk Insert)
        cursor.executemany(sql, data_tuples)
        conn.commit()
        print(f"✅ 成功透過 PyMySQL 處理完成！資料庫實際影響筆數: {cursor.rowcount}")
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()  # 發生錯誤時回滾
        print(f"❌ 寫入資料庫失敗！錯誤訊息：{e}")
        
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# 執行 Pipeline
if __name__ == "__main__":
    
    # 📂 團隊共用：動態相對路徑計算
    # 1. 取得目前這支 Python 檔所在的資料夾絕對路徑 (即 ...\reviews\src\etl)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. 透過 '..' 往上跳兩層回到 \reviews，然後再進入 \data\ 尋找對應的 CSV
    # 這裡我特別將檔名換成你剛才畫面上顯示的 'ChIJceaYPzmpQjQRlc1-wYpELkw_part1.csv'
    csv_target_path = os.path.abspath(os.path.join(current_dir, '..', '..', 'data', 'ChIJ5RyKyfOuQjQRSg2b2u0bt3s_part1.csv'))
    
    print(f"CSV 路徑為:\n {csv_target_path}\n")
    
    # 執行 ETL
    etl_csv_to_reviews_pymysql(csv_target_path)