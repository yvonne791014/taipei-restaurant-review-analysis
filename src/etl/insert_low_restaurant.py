
#docker run --name mysql-container -p 3307:3306 -e MYSQL_ROOT_PASSWORD=1234567890 -d mysql:latest

import pymysql

# 設定資料庫連線資訊
host = 'localhost'
port = 3306
user = 'root'
passwd = 'password'
db = 'REVIEW'
charset = 'utf8mb4'

# 建立連線
conn = pymysql.connect(host=host, port=port, user=user, passwd=passwd, db=db, charset=charset)
print('Successfully connected!')

cursor = conn.cursor()

sql = '''

	INSERT IGNORE INTO low_rating_restaurant
        (restaurant_id, restaurant_name, avg_score, reviews_count, state, category_name, google_map_url, created_at, updated_at) 
    SELECT 
        restaurant_id, restaurant_name, avg_score, reviews_count, state, category_name, google_map_url, NOW(), NOW()
    FROM 
        restaurant
    WHERE 
        avg_score <= 3.5
        AND reviews_count >= 100

'''

cursor.execute(sql)

conn.commit()

cursor.close()

conn.close()




#將restaurant過濾後放到low_rating_reastaurant