import json
import os
import glob

# 1. 自動偵測並取得 data/raw 資料夾下所有 12 個 JSON 檔案的路徑
data_folder = os.path.join('data', 'raw')
json_files = glob.glob(os.path.join(data_folder, '*.json'))

# 用來存放所有檔案整合後的總資料 List
insert_data_list = []

# 💡 新增：用一個集合（Set）來記錄已經抓過的 restaurant_id，利用 Set 查詢速度極快的特性防重
restaurant_set = set()

print(f"🔍 找到 {len(json_files)} 個行政區的 JSON 檔案，開始解析...")

# 2. 用迴圈依序讀取與清洗這 12 個檔案
for file_path in json_files:
    file_name = os.path.basename(file_path)  # 取得檔名
    print(f" ➔ 正在讀取並清洗: {file_name}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ 警告：檔案 {file_name} 格式毀損，已跳過。")
            continue

    # 解析該行政區檔案內的每筆餐廳資料
    for item in data:
        # 擷取對應欄位
        restaurant_id = item.get('placeId')
        restaurant_name = item.get('title')
        total_score = item.get('totalScore')
        reviews_count = item.get('reviewsCount')
        
        # 處理行政區欄位
        state_raw = item.get('state')
        if state_raw is None:
            state_raw = ''
        state_raw = str(state_raw).strip()
        state = state_raw[-3:] if len(state_raw) >= 3 else state_raw
        
        category_name = item.get('categoryName')
        google_map_url = item.get('url')
        
        # 💡 嚴格過濾：除了原本的必填檢查，還要確保 restaurant_id 「沒有重複出現過」
        if (restaurant_id and str(restaurant_id).strip() and 
            restaurant_name and str(restaurant_name).strip() and 
            state and state.strip() and 
            google_map_url and str(google_map_url).strip()):
            
            clean_id = str(restaurant_id).strip()
            
            # 判斷這個 ID 是不是已經在 seen_ids 裡面了？
            if clean_id in restaurant_set:
                continue # 如果重複了，直接跳過這筆，不要了！
                
            # 如果是第一次看到，就加進 seen_ids 記錄起來
            restaurant_set.add(clean_id)
            
            # 建立一個符合 SQL 欄位順序的元組 (Tuple)
            record = (
                clean_id,
                str(restaurant_name).strip(),
                float(total_score) if total_score is not None else None,
                int(reviews_count) if reviews_count is not None else None,
                str(state).strip(),
                str(category_name)[:10].strip() if category_name else None,
                str(google_map_url).strip()
            )
            
            insert_data_list.append(record)

# 3. 檢查轉換後的 List 結果
print("\n" + "="*50)
print(f"📊 全部 12 個檔案解析完畢！")
print(f"成功轉換了 {len(insert_data_list)} 筆餐廳資料！（已自動剔除缺失與重複的資料）")
print(f"共過濾掉了 {13595 - len(insert_data_list)} 筆重複的餐廳。")
print("="*50)


# import json
# import pymysql

# # 1. 讀取你的 JSON 檔案 (修正後的路徑)
# with open('data/raw/Shilin.json', 'r', encoding='utf-8') as f:
#     data = json.load(f)

# # 用來存放準備匯入 MySQL 的資料 List (每一筆資料都是一個 tuple)
# insert_data_list = []

# # 2. 解析並清洗資料
# for item in data:
#     # 擷取對應欄位
#     restaurant_id = item.get('placeId')
#     restaurant_name = item.get('title')
#     total_score = item.get('totalScore')
#     reviews_count = item.get('reviewsCount')
    
#     # 處理行政區欄位
#     state_raw = item.get('state', '')
#     state = state_raw[-3:] if len(state_raw) >= 3 else state_raw
    
#     category_name = item.get('categoryName')
#     google_map_url = item.get('url')
    
#     # 將解析好的欄位打包成一個 tuple，順序要跟後面的 SQL 語法一致
#     record = (restaurant_id, restaurant_name, total_score, reviews_count, state, category_name, google_map_url)
#     insert_data_list.append(record)

# # 3. 連線至 MySQL 並寫入資料
# # 💡 請根據你的 MySQL 設定修改主機、帳號、密碼與資料庫名稱
# connection = pymysql.connect(
#     host='localhost',
#     user='root',         # 你的 MySQL 帳號
#     password='password', # 你的 MySQL 密碼
#     database='REVIEW', # 你的資料庫名稱
#     charset='utf8mb4',
#     cursorclass=pymysql.cursors.DictCursor
# )

# try:
#     with connection.cursor() as cursor:
#         # 建立 SQL 插入語法 (假設你的資料表叫 restaurants，欄位名請對照你的資料庫)
#         # 使用 %s 作為預留位置，PyMySQL 會自動幫你處理特殊字元，避免 SQL Injection
#         sql = """
#         INSERT INTO restaurant
#         (restaurant_id, restaurant_name, total_score, reviews_count, state, category_name, google_map_url) 
#         VALUES (%s, %s, %s, %s, %s, %s, %s)
#         """
        
#         # 使用 executemany 一次性高速批量寫入所有資料
#         print(f"正在匯入 {len(insert_data_list)} 筆資料至 MySQL...")
#         cursor.executemany(sql, insert_data_list)
        
#         # 必須 commit，資料才會真正寫入資料庫
#         connection.commit()
#         print("資料匯入成功！")

# except Exception as e:
#     # 發生錯誤時回滾
#     connection.rollback()
#     print(f"發生錯誤，資料已回滾。錯誤訊息: {e}")

# finally:
#     # 無論成功或失敗，最後都要關閉資料庫連線
#     connection.close()


import pymysql

# --- 安全檢查：如果完全沒有清洗出合格資料，就不用連線資料庫了 ---
if not insert_data_list:
    print("⚠️ 提示：沒有任何合格的餐廳資料可供匯入，程式結束。")
    exit()

# 3. 連線至 MySQL 並一次性寫入所有資料
# 💡 請根據你的 MySQL 設定修改主機、帳號、密碼與資料庫名稱
connection = pymysql.connect(
    host='localhost',
    user='root',         # 你的 MySQL 帳號
    password='password', # 你的 MySQL 密碼
    database='REVIEW',   # 你的資料庫名稱
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

try:
    with connection.cursor() as cursor:
        # 建立 SQL 插入語法
        # 使用 %s 作為預留位置，PyMySQL 會自動幫你處理特殊字元，避免 SQL Injection
        sql = """
        INSERT INTO restaurant
        (restaurant_id, restaurant_name, total_score, reviews_count, state, category_name, google_map_url) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        # 使用 executemany 一次性高速批量寫入「所有行政區加總」的乾淨資料
        print(f"🚀 正在將整合後的 {len(insert_data_list)} 筆資料匯入 MySQL...")
        cursor.executemany(sql, insert_data_list)
        
        # 必須 commit，資料才會真正寫入資料庫
        connection.commit()
        print("🎉 恭喜！12 個行政區的合格資料已成功全數匯入！")

except Exception as e:
    # 發生錯誤時回滾（如果 12 個檔案裡有任何一筆造成寫入失敗，整批都會退回，保證資料庫乾淨）
    connection.rollback()
    print(f"❌ 發生錯誤，資料已回滾。錯誤訊息: {e}")

finally:
    # 無論成功或失敗，最後都要關閉資料庫連線
    connection.close()