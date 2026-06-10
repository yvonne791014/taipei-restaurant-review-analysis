import asyncio
import re
import os
import pandas as pd
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

## 1. 尚未修改成自動讀取list[餐廳url]
## 2. 儲存檔名感覺要根據餐廳ID取(或其他方式)
## 3. 目前不知道async是幹嘛用的，再研究如果拿掉async能不能用
## 4. 這個程式跑過一次之後會儲存類似cookie，下次跑的時候就不會被google認為是機器人了
#     只會出現"你"，不用登入，上次試跑好幾次沒有被擋，應該沒問題(但如果標籤變了就不能保證)

async def scrape_latest_google_reviews(url, max_reviews=None, output_filename="google_reviews_latest"):
    async with async_playwright() as p:
        # 1. 啟動瀏覽器並偽裝（強制設定繁體中文與台灣時區）
        user_data_dir = os.path.join(os.getcwd(), "playwright_user_data")

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 800}
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        stealth_obj = Stealth()
        await stealth_obj.apply_stealth_async(browser)
        
        print("正在導向目標 Google 地圖網址...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=5000)
        except Exception:
            print("首次載入稍微超時，準備執行強制重新整理...")

        # 依照需求：打開後先重新整理
        print("2. 執行網頁強制重新整理 (Reload)...")
        try:
            await page.reload(wait_until="domcontentloaded", timeout=5000)
            print("重新整理指令已送出，等待3秒確保畫面渲染完成...")
            await page.wait_for_timeout(3000)  # 使用硬性時間等待，最穩固
        except Exception as e:
            print(f"重新整理超時或失敗：{e}，嘗試強制繼續...")
        
        # 3. 自動尋找並切換到「評論」頁籤
        print("3. 正在尋找『評論』頁籤...")
        # 尋找包含「評論」文字的按鈕或標籤
        reviews_tab = page.locator('button:has-text("評論")').first
        if await reviews_tab.count() > 0:
            await reviews_tab.click()
            print("已點擊『評論』頁籤")
            await page.wait_for_timeout(2000)
        else:
            print("未找到明確的評論頁籤，可能已在評論頁或此商家介面不同，嘗試繼續執行...")

        # 4. 點擊「排序」並選擇「最新」
        print("4. 正在設定排序為『最新』...")
        try:
            # 尋找排序按鈕（通常文字包含 "排序"）
            sort_button = page.locator('button:has-text("排序")').first
            await sort_button.wait_for(timeout=3000)
            await sort_button.click()
            await page.wait_for_timeout(3000)
            
            # 在彈出的選單中點擊「最新」
            latest_option = page.locator('div[role="menuitem"]:has-text("最新"), button:has-text("最新"), .fxNQSd:has-text("最新")').first
            await latest_option.click()
            print("成功切換排序為：最新")
            await page.wait_for_timeout(2000)

        except Exception as e:
            print(f"切換排序失敗（可能選單結構有變）：{e}。將以預設排序繼續抓取。")

        # 5. 定位評論滾動容器
        try:
            scroll_pane = page.locator('.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde')
            await scroll_pane.wait_for(timeout=3000)
        except Exception:
            print("錯誤：找不到評論的滾動容器，請檢查商家網頁結構。")
            await browser.close()
            return

        # 6. 開始「邊滾動、邊點擊更多、邊解析」的增量處理流程
        all_parsed_ids = set()
        current_batch_reviews = []
        total_saved_count = 0
        batch_size = 500
        batch_num = 1
        no_new_rounds = 0
        last_height = 0

        while True:
            # 取得當前畫面上所有的評論區塊
            cards = await page.locator('div.jftiEf.fontBodyMedium').all()
            new_found_in_round = False

            for card in cards:
                if max_reviews is not None and total_saved_count + len(current_batch_reviews) >= max_reviews:
                    break

                # 擷取評論 ID 做為唯一識別
                review_id = ""
                for attr in ["data-review-id", "data-review_ID", "data-reviewid"]:
                    val = await card.get_attribute(attr)
                    if val:
                        review_id = val
                        break
                
                # 如果這則評論解析過，就跳過
                if review_id in all_parsed_ids:
                    continue
                
                new_found_in_round = True
                all_parsed_ids.add(review_id)

                try:
                    # 滾動到該評論位置以確保「更多」按鈕可見
                    await card.scroll_into_view_if_needed()
                    
                    # 點開「更多」按鈕
                    more_button = card.locator('button:has-text("更多")')
                    if await more_button.count() > 0 and await more_button.is_visible():
                        await more_button.click()
                        await page.wait_for_timeout(500) 

                    # 1. 總星等
                    stars_el = card.locator('.kvMYJc')
                    star_text = ""
                    if await stars_el.count() > 0:
                        star_text = await stars_el.get_attribute('aria-label') or ""
                    
                    cleaned = re.sub(r'[\u4e00-\u9fff]+', '', star_text.strip())
                    cleaned = re.sub(r'[^\d.]', '', cleaned).strip()
                    m = re.search(r'(\d+(?:\.\d+)?)', cleaned)
                    total_stars = float(m.group(1)) if m else None
                    
                    # 2. 評論本文
                    review_text = ""
                    text_el = card.locator('.wiI7pd').first
                    if await text_el.count() > 0:
                        review_text = (await text_el.text_content() or "").strip()
                    
                    # 3. 細項評分
                    food_rating = None
                    service_rating = None
                    atmosphere_rating = None
                    aspect_elements = await card.locator('.RfDO5c').all()
                    for aspect in aspect_elements:
                        aspect_text = await aspect.text_content()
                        if aspect_text:
                            match = re.search(r'(餐點|服務|氣氛)\s*[:：]\s*(\d+)', aspect_text)
                            if match:
                                category = match.group(1)
                                score = int(match.group(2))
                                if category == "餐點": food_rating = score
                                elif category == "服務": service_rating = score
                                elif category == "氣氛": atmosphere_rating = score

                    # 儲存到當前批次
                    review_data = {
                        "review-ID": review_id,
                        "total_stars": total_stars,
                        "text": review_text,
                        "food_rating": food_rating,
                        "service_rating": service_rating,
                        "atmosphere_rating": atmosphere_rating
                    }
                    current_batch_reviews.append(review_data)

                    # 檢查是否達到 500 則，若是則存檔
                    if len(current_batch_reviews) >= batch_size:
                        filename = f"{output_filename}_part{batch_num}.csv"
                        pd.DataFrame(current_batch_reviews).to_csv(filename, index=False, encoding="utf-8-sig")
                        print(f"==> 已達 {batch_size} 則，儲存至 {filename}")
                        total_saved_count += len(current_batch_reviews)
                        current_batch_reviews = []
                        batch_num += 1

                    if len(all_parsed_ids) % 50 == 0:
                        print(f"目前累計解析進度: {len(all_parsed_ids)} 則...")
                    
                except Exception as e:
                    print(f"   [跳過] 解析評論時發生異常: {e}")
                    continue

            if max_reviews is not None and len(all_parsed_ids) >= max_reviews:
                print(f"已達到最大需求量 {max_reviews}，停止抓取。")
                break

            # 執行滾動以載入更多內容
            await scroll_pane.evaluate("el => el.scrollBy(0, el.clientHeight * 2)")
            await page.wait_for_timeout(2000)

            new_height = await scroll_pane.evaluate("el => el.scrollHeight")
            if not new_found_in_round and new_height == last_height:
                no_new_rounds += 1
                if no_new_rounds >= 3:
                    print("連續 3 輪未發現新評論且滾動高度未變，判定已到底部。")
                    break
            else:
                no_new_rounds = 0
            last_height = new_height

        # 7. 儲存最後剩餘的評論（不足 500 則的部分）
        if current_batch_reviews:
            filename = f"{output_filename}_part{batch_num}.csv"
            pd.DataFrame(current_batch_reviews).to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"==> 儲存剩餘的 {len(current_batch_reviews)} 則至 {filename}")
            total_saved_count += len(current_batch_reviews)

        print(f"\n全部任務完成！總共抓取並儲存了 {total_saved_count} 則評論。")
        
        await browser.close()

# --- 執行入口 ---
if __name__ == "__main__":
    # 在此處替換為你想要爬取的 Google Maps 商家網址

    """要用迴圈，把餐廳url放在list裡面，然後一個一個爬取"""
    target_urls = [
        "https://www.google.com/maps/place/%E7%89%9B%E8%A7%92%E6%97%A5%E6%9C%AC%E7%87%92%E8%82%89%E5%B0%88%E9%96%80%E5%BA%97+%E5%BE%A9%E8%88%88%E5%BA%97/@25.0586821,121.5443849,17z/data=!4m8!3m7!1s0x3442abe43ec8be7b:0x234965f40e72a4ab!8m2!3d25.0586821!4d121.5443849!9m1!1b1!16s%2Fg%2F1vhkh78_?entry=ttu&g_ep=EgoyMDI2MDYwMS4wIKXMDSoASAFQAw%3D%3D",
        # 在這裡添加更多餐廳URL
    ]

    # 執行腳本
    asyncio.run(scrape_latest_google_reviews(target_urls, max_reviews=None))
