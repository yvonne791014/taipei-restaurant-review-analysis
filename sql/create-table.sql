create database REVIEW;

use REVIEW;

create table restaurant(
	restaurant_id varchar(30) NOT NULL comment '餐廳編號(from apify)',
    restaurant_name VARCHAR(100) not null comment '餐廳名稱',
    total_score DECIMAL(2,1) comment '平均分數',
    reviews_count int comment '評論數',
    state char(3) not null comment '行政區',
    category_name varchar(10) comment '分類',
    google_map_url VARCHAR(512) not null comment '餐廳網址連結',
    created_at datetime default now() comment '資料建立時間',
	updated_at datetime default now() comment '資料更新時間',
	PRIMARY KEY(restaurant_id)
);

create table low_rating_restaurant(
	restaurant_id varchar(30) NOT NULL comment '餐廳編號(from apify)',
    restaurant_name VARCHAR(100) not null comment '餐廳名稱',
    total_score DECIMAL(2,1) comment '平均分數',
    reviews_count int comment '評論數',
    state char(3) not null comment '行政區',
    category_name varchar(10) comment '分類',
    google_map_url VARCHAR(512) not null comment '餐廳網址連結',
    created_at datetime default now() comment '資料建立時間',
    updated_at datetime default now() comment '資料更新時間',
	PRIMARY KEY(restaurant_id)
);

create table reviews(
	review_id varchar(128) NOT NULL comment '評論編號(from apify)',
	restaurant_id varchar(30) NOT NULL comment '餐廳編號',
    rating tinyint unsigned comment '評分1~5',
    review_content TEXT comment '評論內容',
    published_at datetime not null comment '評論發布的時間',
    price_per_person_from int unsigned default 0 comment '價位from',
    price_per_person_to int unsigned default 0 comment '價位to',
    food int unsigned default 0 comment '評分-食物, 0分代表沒給分數',
    service int unsigned default 0 comment '評分-服務, 0分代表沒給分數',
    atmosphere int unsigned default 0 comment '評分-環境氣氛, 0分代表沒給分數',
    PRIMARY KEY(review_id)    
);

