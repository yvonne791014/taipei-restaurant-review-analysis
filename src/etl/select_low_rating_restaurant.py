

from numpy import select
import pymysql
import json

# 設定資料庫連線資訊
host = 'localhost'
port = 3306
user = 'root'
passwd = 'password'
db = 'REVIEW'
charset = 'utf8mb4'

conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db, charset=charset)
print('Successfully connected!')


# #這一段是抓取全部區域的網址
# cursor = conn.cursor(pymysql.cursors.DictCursor)


# sql =""" 
#     select restaurant_id,google_map_url 
#     from low_rating_restaurant
#     order by state;
# """
# # 將指令放進 cursor 物件，並執行
# cursor.execute(sql)

# #這時候得到的 data 直接就是 [{'restaurant_id': ..., 'google_map_url': ...}, ...]
# data = cursor.fetchall() 
# print(data)
# #先建立外面最大的空 list
# restaurant_list = []

# # 用迴圈一筆一筆處理資料
# for row in data:
#     # 建立該筆資料的小字典 {'restaurant_id': 'google_map_url'}
#     item_dict = {row['restaurant_id']: row['google_map_url']}
    
#     # 把小字典丟進大 list 裡面
#     restaurant_list.append(item_dict)

# print(restaurant_list)




# 更改這一行：指定 cursor 類型為 DictCursor
cursor = conn.cursor(pymysql.cursors.DictCursor)

sql = """
select restaurant_id, google_map_url
from low_rating_restaurant
where state = '北投區';
"""
cursor.execute(sql)

# 這時候得到的 data 直接就是 [{'restaurant_id': ..., 'google_map_url': ...}, ...]
data = cursor.fetchall() 
#print(data)
# 先建立外面最大的空 list
restaurant_list = []

# 用迴圈一筆一筆處理資料
for row in data:
    # 建立該筆資料的小字典 {'restaurant_id': 'google_map_url'}
    item_dict = {row['restaurant_id']: row['google_map_url']}
    
    # 把小字典丟進大 list 裡面
    restaurant_list.append(item_dict)

print(restaurant_list)
# ==================== 🛠️ 改成存成 JSON 檔 ====================
if restaurant_list:
    json_filename = "beitou_low_rating_restaurants.json"

    # 使用 utf-8 開啟檔案，並用 json.dump 一鍵寫入
    with open(json_filename, mode="w", encoding="utf-8") as file:
        # indent=4 可以讓輸出的 JSON 檔自動排版縮排，變得像程式碼一樣好讀
        # ensure_ascii=False 可以確保裡面的中文不會被轉成 \u4e2d\u6587 這種編碼
        json.dump(restaurant_list, file, indent=4, ensure_ascii=False)

    print(f"✅ 檔案已成功儲存為 JSON 至: {json_filename}")
else:
    print("⚠️ 找不到符合條件的北投區餐廳資料，未產生 JSON 檔。")



# 確保不論程式成功或失敗，都會關閉資源
cursor.close()
conn.close()

 