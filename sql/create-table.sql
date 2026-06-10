create database REVIEW;

use REVIEW;

create table restaurant(
	restaurant_id varchar(30) NOT NULL comment '餐廳編號(from apify)',
    restaurant_name VARCHAR(500) not null comment '餐廳名稱',
    total_score DECIMAL(2,1) comment '平均分數',
    reviews_count int comment '評論數',
    state char(3) not null comment '行政區',
    category_name varchar(255) comment '分類',
    google_map_url TEXT not null comment '餐廳網址連結',
    created_at datetime default now() comment '資料建立時間',
	updated_at datetime default now() comment '資料更新時間',
	PRIMARY KEY(restaurant_id)
);

create table low_rating_restaurant(
	restaurant_id varchar(30) NOT NULL comment '餐廳編號(from apify)',
    restaurant_name VARCHAR(500) not null comment '餐廳名稱',
    total_score DECIMAL(2,1) comment '平均分數',
    reviews_count int comment '評論數',
    state char(3) not null comment '行政區',
    category_name varchar(255) comment '分類',
    google_map_url TEXT not null comment '餐廳網址連結',
    created_at datetime default now() comment '資料建立時間',
    updated_at datetime default now() comment '資料更新時間',
	PRIMARY KEY(restaurant_id)
);

create table reviews(
	review_id varchar(128) NOT NULL comment '評論編號(from apify)',
	restaurant_id varchar(30) NOT NULL comment '餐廳編號',
    total_stars tinyint unsigned NOT NULL comment '總評分1~5',
    review_content TEXT comment '評論內容',
    food_rating tinyint unsigned default null comment '評分-食物',
    service_rating tinyint unsigned default null comment '評分-服務',
    atmosphere_rating tinyint unsigned default null comment '評分-環境氣氛',
    created_at datetime default now() comment '資料建立時間',
	updated_at datetime default now() comment '資料更新時間',
    PRIMARY KEY(review_id),
    constraint FK_REVIEWS_LOWRATING foreign key (restaurant_id)
    references low_rating_restaurant(restaurant_id)
);

/*
1   = 正面
0   = 未提及
-1  = 負面
*/
create table reviews_analyze(
	review_id varchar(128) NOT NULL comment '評論編號(from apify)',
    food_issue         tinyint DEFAULT 0 comment '餐點味道或品質問題',
	price_issue        tinyint DEFAULT 0 comment '價格問題',
	service_issue      tinyint DEFAULT 0 comment '服務態度問題',
	hygiene_issue      tinyint DEFAULT 0 comment '食物衛生問題',
	queue_issue        tinyint DEFAULT 0 comment '等待問題(排隊/上菜速度)',
	environment_issue  tinyint DEFAULT 0 comment '環境問題(空間大小/整潔)',
    parking_issue  tinyint DEFAULT 0 comment '停車問題',
    created_at datetime default now() comment '資料建立時間',
	updated_at datetime default now() comment '資料更新時間',
    PRIMARY KEY(review_id),
    constraint FK_MEANING_REVIEWS foreign key (review_id)
    references reviews(review_id)
);