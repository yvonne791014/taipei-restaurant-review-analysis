"""
insert ignore into 
	low_rating_restaurant
select *
from 
	restaurant
where 
	total_score < 4
    and reviews_count > 100

"""

#將restaurant過濾後放到low_rating_reastaurant