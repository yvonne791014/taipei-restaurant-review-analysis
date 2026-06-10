create database REVIEW;

use REVIEW;

create table restaurant(
	restaurant_id varchar(30) not null comment '餐廳編號(from apify)',
    restaurant_name VARCHAR(500) not null comment '餐廳名稱',
    total_score DECIMAL(2,1) comment '平均分數',
    reviews_count int comment '評論數',
    state char(3) not null comment '行政區',
    category_name varchar(255) comment '分類',
    google_map_url TEXT not null comment '餐廳網址連結',
    created_at datetime not null default now() comment '資料建立時間',
	updated_at datetime not null default now() comment '資料更新時間',
	PRIMARY KEY(restaurant_id)
);

create table low_rating_restaurant(
	restaurant_id varchar(30) not null comment '餐廳編號(from apify)',
    restaurant_name VARCHAR(500) not null comment '餐廳名稱',
    total_score DECIMAL(2,1) comment '平均分數',
    reviews_count int comment '評論數',
    state char(3) not null comment '行政區',
    category_name varchar(255) comment '分類',
    google_map_url TEXT not null comment '餐廳網址連結',
    created_at datetime not null default now() comment '資料建立時間',
    updated_at datetime not null default now() comment '資料更新時間',
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
    is_deleted bool not null default 0 comment '是否刪除，0=否, 1=是，代表不進行分析',
    created_at datetime not null default now() comment '資料建立時間',
	updated_at datetime not null default now() comment '資料更新時間',
    PRIMARY KEY(review_id),
    constraint FK_REVIEWS_LOWRATING foreign key (restaurant_id)
    references low_rating_restaurant(restaurant_id)
);

create table issue_type(
  issue_type_id tinyint unsigned not null auto_increment comment 'ID',
  issue_code char(1) not null comment '問題類型代碼',
  issue_ename varchar(20) not null comment '問題類型英文名稱',
  issue_cname varchar(10) not null comment '問題類型中文名稱',
  key_words varchar(200) comment 'AI用來分析的關鍵字',
  PRIMARY KEY(issue_type_id)
);

insert into issue_type(issue_code, issue_ename, issue_cname, key_words)
values
('F', 'food', '食物', '餐點、味道、份量、食材、菜色'),
('P', 'price', '價格', '價格、CP值、划算、偏貴'),
('S', 'service', '服務', '服務、態度、店員、出餐、漏單'),
('H', 'hygiene', '衛生', '衛生、乾淨、髒、蟑螂、廁所'),
('Q', 'queue', '排隊', '排隊、等候、候位、等很久'),
('E', 'environment', '環境', '裝潢、座位、空間、吵、冷氣、氣氛'),
('P', 'parking', '停車', '停車、交通、車位')
;

create table reviews_analyze(
	analyze_id int unsigned not null auto_increment comment 'ID',
	review_id varchar(128) NOT NULL comment '評論編號',
    issue_type_id tinyint UNSIGNED NOT NULL comment 'ID',
    sentiment tinyint not null comment '情緒 1=正向, -1=負向',
    created_at datetime not null default now() comment '資料建立時間',
	updated_at datetime not null default now() comment '資料更新時間',
    PRIMARY KEY(analyze_id),
    constraint FK_ANALYZE_REVIEWS foreign key (review_id)
    references reviews(review_id),
    constraint FK_ANALYZE_TYPE foreign key (issue_type_id)
    references issue_type(issue_type_id)
);