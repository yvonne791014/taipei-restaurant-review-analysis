

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

cursor = conn.cursor()

sql =""" 
    select google_map_url 
    from low_rating_restaurant
    order by state;
"""
# 將指令放進 cursor 物件，並執行
cursor.execute(sql)

data = cursor.fetchall()

data_urls = [url[0] for url in data]

print(data_urls)




 