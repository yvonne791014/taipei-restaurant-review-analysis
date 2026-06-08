

from numpy import select
import pymysql

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

#print(restaurant_list)

# 確保不論程式成功或失敗，都會關閉資源
cursor.close()
conn.close()

 