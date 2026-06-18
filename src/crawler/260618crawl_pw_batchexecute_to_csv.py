import asyncio
import csv
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.async_api import Page, Response, async_playwright
from playwright_stealth import Stealth

# 該版爬蟲改為監聽batchexecute回傳的評論資料，目前穩定約2000則
# 尚未改成跑list抓餐廳_di跟url


SERVICE_NAME = "MapsUgcPostService.ListUgcPosts"

# VS Code direct-run settings. Change these values, then click "Run Python File".
DEFAULT_RESTAURANT_ID = "ChIJuylXlmysQjQR9Ki2eWi7IfA" # 來來豆漿店內湖店，評論6000多則
DEFAULT_URL = "https://www.google.com/maps/search/?api=1&query=%E4%BE%86%E4%BE%86%E8%B1%86%E6%BC%BF%EF%BC%8824%E5%B0%8F%E6%99%82%EF%BC%89&query_place_id=ChIJuylXlmysQjQR9Ki2eWi7IfA"
DEFAULT_OUTPUT = f"reviews_{DEFAULT_RESTAURANT_ID}.csv"
DEFAULT_MAX_REVIEWS = None
DEFAULT_HEADLESS = False


def walk_json(node: Any):
    yield node
    if isinstance(node, list):
        for item in node:
            yield from walk_json(item)
    elif isinstance(node, dict):
        for item in node.values():
            yield from walk_json(item)


def google_maps_url_with_language(url: str, language: str = "zh-TW") -> str:
    parsed = urlparse(url)
    query_pairs = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "hl"]
    query_pairs.append(("hl", language))
    return urlunparse(parsed._replace(query=urlencode(query_pairs)))


def is_review_text_candidate(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if text.startswith(("http://", "https://", "//")):
        return False
    if text.startswith(("CIABI", "GUIDED_", "E:", "M:/")):
        return False
    if re.fullmatch(r"[a-z]{2}(?:-[A-Za-z]+)?", text):
        return False
    if text in {
        "餐點",
        "服務",
        "氣氛",
        "餐點類型",
        "訂單類型",
        "平均每人消費金額",
        "建議的餐點",
        "用餐人數",
        "由 Google 翻譯",
        "查看原文",
        "顯示原文",
    }:
        return False
    return True


def looks_like_chinese_text(text: str) -> bool:
    if not re.search(r"[\u4e00-\u9fff]", text):
        return False
    # Avoid treating Japanese/Korean originals as Chinese translations.
    if re.search(r"[\u3040-\u30ff\uac00-\ud7af]", text):
        return False
    return True


def looks_like_non_language_text(text: str) -> bool:
    # Preserve emoji-only or symbol-only comments, but do not keep foreign prose.
    return not re.search(r"[A-Za-z\u3040-\u30ff\uac00-\ud7af]", text)


def extract_text_tuple(node: Any) -> str:
    if not (
        isinstance(node, list)
        and len(node) >= 3
        and isinstance(node[0], str)
        and node[1] is None
        and isinstance(node[2], list)
        and len(node[2]) >= 2
        and all(isinstance(x, int) for x in node[2][:2])
    ):
        return ""

    text = node[0].strip()
    return text if is_review_text_candidate(text) else ""


def collect_review_text_candidates(node: Any) -> list[str]:
    candidates: list[str] = []

    for item in walk_json(node):
        text = extract_text_tuple(item)
        if text and text not in candidates:
            candidates.append(text)

    return candidates


def first_text(node: Any) -> str:
    if not isinstance(node, list):
        return ""

    language_block_candidates: list[str] = []
    for idx, item in enumerate(node):
        if not (
            isinstance(item, list)
            and len(item) == 1
            and isinstance(item[0], str)
            and re.fullmatch(r"[a-z]{2}(?:-[A-Za-z]+)?", item[0])
        ):
            continue

        maybe_texts = node[idx + 1] if idx + 1 < len(node) else None
        if not isinstance(maybe_texts, list):
            continue
        for maybe_text in maybe_texts:
            text = extract_text_tuple(maybe_text)
            if text:
                language_block_candidates.append(text)

    all_candidates = language_block_candidates + [
        text for text in collect_review_text_candidates(node) if text not in language_block_candidates
    ]

    for text in all_candidates:
        if looks_like_chinese_text(text):
            return text

    for text in all_candidates:
        if looks_like_non_language_text(text):
            return text

    return ""


def aspect_rating(content: Any, aspect_key: str):
    for item in walk_json(content):
        if not isinstance(item, list) or len(item) <= 11:
            continue
        marker = item[0]
        if (
            isinstance(marker, list)
            and marker
            and marker[0] == aspect_key
            and isinstance(item[11], list)
            and item[11]
        ):
            return item[11][0]
    return None


def selected_option(content: Any, guided_key: str) -> str | None:
    for item in walk_json(content):
        if not isinstance(item, list) or not item:
            continue
        marker = item[0]
        if not (isinstance(marker, list) and marker and marker[0] == guided_key):
            continue
        choices = item[2] if len(item) > 2 else None
        try:
            return choices[0][0][1]
        except (TypeError, IndexError):
            return None
    return None


def selected_options(content: Any, guided_key: str) -> list[str]:
    values: list[str] = []
    for item in walk_json(content):
        if not isinstance(item, list) or not item:
            continue
        marker = item[0]
        if not (isinstance(marker, list) and marker and marker[0] == guided_key):
            continue

        choices = item[3] if len(item) > 3 else None
        if not isinstance(choices, list) or not choices:
            return values

        try:
            for choice in choices[0]:
                if isinstance(choice, list) and len(choice) > 1 and isinstance(choice[1], str):
                    values.append(choice[1])
        except TypeError:
            return values
    return values


def parse_review_wrapper(wrapper: Any, restaurant_id: str | None = None) -> dict[str, Any] | None:
    if not isinstance(wrapper, list) or not wrapper or not isinstance(wrapper[0], list):
        return None

    review = wrapper[0]
    if len(review) < 3:
        return None

    review_id = review[0]
    meta = review[1] if isinstance(review[1], list) else []
    content = review[2] if isinstance(review[2], list) else []
    created_timestamp_raw = meta[2] if len(meta) > 2 else None
    updated_timestamp_raw = meta[3] if len(meta) > 3 else None

    return {
        "review_id": review_id,
        "restaurant_id": restaurant_id,
        "_sort_timestamp": max(
            timestamp for timestamp in [created_timestamp_raw, updated_timestamp_raw] if isinstance(timestamp, int)
        )
        if isinstance(created_timestamp_raw, int) or isinstance(updated_timestamp_raw, int)
        else 0,
        "review_score": content[0][0] if content and isinstance(content[0], list) and content[0] else None,
        "review_content": first_text(content),
        "food_score": aspect_rating(content, "GUIDED_DINING_FOOD_ASPECT"),
        "service_score": aspect_rating(content, "GUIDED_DINING_SERVICE_ASPECT"),
        "atmosphere_score": aspect_rating(content, "GUIDED_DINING_ATMOSPHERE_ASPECT"),
    }


def iter_listugc_payloads(raw_text: str):
    text = raw_text.strip()
    if text.startswith(")]}'"):
        text = text[4:].strip()

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("[["):
            continue
        try:
            outer = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(outer, list):
            continue

        for call in outer:
            if not (
                isinstance(call, list)
                and len(call) >= 3
                and isinstance(call[1], str)
                and SERVICE_NAME in call[1]
                and isinstance(call[2], str)
            ):
                continue
            try:
                yield json.loads(call[2])
            except json.JSONDecodeError:
                continue


def parse_batchexecute_text(raw_text: str, restaurant_id: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in iter_listugc_payloads(raw_text):
        review_wrappers = payload[2] if isinstance(payload, list) and len(payload) > 2 else []
        if not isinstance(review_wrappers, list):
            continue

        for wrapper in review_wrappers:
            row = parse_review_wrapper(wrapper, restaurant_id=restaurant_id)
            if row:
                rows.append(row)
    return rows


def review_sort_timestamp(row: dict[str, Any]) -> int:
    sort_timestamp = row.get("_sort_timestamp")
    if isinstance(sort_timestamp, int):
        return sort_timestamp

    updated = row.get("updated_timestamp_raw")
    created = row.get("created_timestamp_raw")
    if isinstance(updated, int) and isinstance(created, int):
        return max(updated, created)
    if isinstance(updated, int):
        return updated
    if isinstance(created, int):
        return created
    return 0


def review_sort_score(row: dict[str, Any]) -> float:
    score = row.get("review_score")
    if isinstance(score, (int, float)):
        return float(score)
    return float("inf")


def looks_like_lowest_rating_batch(rows: list[dict[str, Any]]) -> bool:
    scores = [review_sort_score(row) for row in rows if review_sort_score(row) != float("inf")]
    if len(scores) < 3:
        return bool(scores)

    first_score = scores[0]
    inversions = sum(1 for left, right in zip(scores, scores[1:]) if left > right)
    allowed_inversions = max(1, len(scores) // 5)

    return first_score == min(scores) and inversions <= allowed_inversions


class BatchReviewCollector:
    def __init__(self, restaurant_id: str):
        self.restaurant_id = restaurant_id
        self.by_id: dict[str, dict[str, Any]] = {}
        self.raw_response_count = 0
        self.parsed_response_count = 0
        self.next_progress_report = 100

    def add_raw(self, raw: str):
        if SERVICE_NAME not in raw:
            return

        self.raw_response_count += 1
        rows = parse_batchexecute_text(raw, restaurant_id=self.restaurant_id)
        if rows:
            self.parsed_response_count += 1

        added = 0
        for row in rows:
            review_id = row.get("review_id")
            if review_id and review_id not in self.by_id:
                self.by_id[review_id] = row
                added += 1

        while len(self.by_id) >= self.next_progress_report:
            print(f"progress: parsed {self.next_progress_report} reviews.")
            self.next_progress_report += 100

    async def handle_response(self, response: Response):
        if "batchexecute" not in response.url:
            return

        try:
            raw = await response.text()
        except Exception:
            return

        self.add_raw(raw)


async def click_reviews_tab(page: Page):
    reviews_tab = page.locator('button:has-text("評論")').first
    if await reviews_tab.count() > 0:
        await reviews_tab.click()
        await page.wait_for_timeout(2000)


async def click_side_and_reload(page: Page):
    viewport = page.viewport_size or {"width": 1280, "height": 1080}
    x = max(100, min(viewport["width"] - 80, int(viewport["width"] * 0.85)))
    y = max(100, min(viewport["height"] - 80, int(viewport["height"] * 0.45)))

    print("Clicking side area, then reloading to reveal review tab.")
    try:
        await page.mouse.click(x, y)
        await page.wait_for_timeout(700)
        await page.reload(wait_until="domcontentloaded", timeout=15000)
    except Exception as exc:
        print(f"Side click/reload timed out or failed, continuing: {exc}")

    await page.wait_for_timeout(3000)


async def wait_for_lowest_rating_listugc_response(page: Page, timeout_ms: int = 30000):
    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()

    async def inspect_response(response: Response):
        if "batchexecute" not in response.url:
            return
        try:
            raw = await response.text()
        except Exception:
            return

        if SERVICE_NAME not in raw or future.done():
            return

        rows = parse_batchexecute_text(raw)
        if looks_like_lowest_rating_batch(rows):
            future.set_result(raw)
        elif rows:
            print("Ignored batch that was not sorted by lowest rating.")

    def schedule(response: Response):
        asyncio.create_task(inspect_response(response))

    page.on("response", schedule)
    try:
        return await asyncio.wait_for(future, timeout=timeout_ms / 1000)
    finally:
        page.remove_listener("response", schedule)


async def click_sort_lowest_rating_or_fail(page: Page):
    for attempt in range(1, 4):
        try:
            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except Exception:
                pass
            await page.wait_for_timeout(1000)

            sort_button = page.locator('button:has-text("排序")').first
            await sort_button.wait_for(timeout=7000)
            await sort_button.click()
            await page.wait_for_timeout(800)

            lowest_option = page.locator(
                'div[role="menuitemradio"]:has-text("最低"), '
                'div[role="menuitem"]:has-text("最低"), '
                'div[role="option"]:has-text("最低"), '
                'button:has-text("最低"), '
                'span:has-text("最低")'
            ).first
            await lowest_option.wait_for(timeout=7000)

            response_task = asyncio.create_task(wait_for_lowest_rating_listugc_response(page))
            await asyncio.sleep(0)
            await lowest_option.click()
            raw = await response_task
            await page.wait_for_timeout(2500)
            print("Confirmed sorting by lowest rating.")
            return raw
        except Exception as exc:
            print(f"Lowest-rating sort attempt {attempt} failed: {exc}")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1200)

    raise RuntimeError("Could not confirm lowest-rating sorting. Stop to avoid scraping the wrong order.")


async def find_scroll_pane(page: Page):
    selectors = [
        ".m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde",
        'div[role="main"] .m6QErb.DxyBCb.kA9KIf',
        'div[aria-label*="評論"]',
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(timeout=5000)
            return locator
        except Exception:
            pass
    raise RuntimeError("Could not find the review scroll pane.")


async def scroll_to_collect_all(page: Page, scroll_pane, collector: BatchReviewCollector, max_reviews: int | None):
    no_growth_rounds = 0
    last_count = len(collector.by_id)
    last_height = await scroll_pane.evaluate("el => el.scrollHeight")

    while True:
        if max_reviews is not None and len(collector.by_id) >= max_reviews:
            print(f"Reached max_reviews={max_reviews}.")
            break

        await scroll_pane.evaluate("el => el.scrollTo(0, el.scrollHeight)")
        await page.wait_for_timeout(random.randint(1400, 2400))

        for _ in range(random.randint(4, 7)):
            distance = random.randint(450, 950)
            await scroll_pane.evaluate("(el, y) => el.scrollBy(0, y)", distance)
            await page.wait_for_timeout(random.randint(500, 1100))

        await page.wait_for_timeout(1800)

        current_count = len(collector.by_id)
        current_height = await scroll_pane.evaluate("el => el.scrollHeight")
        if current_count == last_count and current_height == last_height:
            no_growth_rounds += 1
            if no_growth_rounds >= 6:
                print("No new reviews for several rounds. Finished.")
                break
        else:
            no_growth_rounds = 0

        last_count = current_count
        last_height = current_height


async def scrape_reviews_to_json(
    restaurant_id: str = DEFAULT_RESTAURANT_ID,
    url: str = DEFAULT_URL,
    output_path: Path | None = None,
    max_reviews: int | None = DEFAULT_MAX_REVIEWS,
    headless: bool = DEFAULT_HEADLESS,
    session_dir: Path | None = None,
):
    async with async_playwright() as p:
        output_path = output_path or Path(DEFAULT_OUTPUT)
        user_data_dir = session_dir or Path.cwd() / "playwright_google_session"

        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=headless,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 1080},
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        stealth_obj = Stealth()
        await stealth_obj.apply_stealth_async(browser)

        print("Opening Google Maps.")
        navigation_url = google_maps_url_with_language(url)
        try:
            await page.goto(navigation_url, wait_until="domcontentloaded", timeout=15000)
        except Exception as exc:
            print(f"Initial page load timed out or failed, continuing: {exc}")

        await page.wait_for_timeout(3000)
        await click_side_and_reload(page)
        await click_reviews_tab(page)
        lowest_rating_raw = await click_sort_lowest_rating_or_fail(page)

        collector = BatchReviewCollector(restaurant_id=restaurant_id)
        collector.add_raw(lowest_rating_raw)

        pending_tasks: set[asyncio.Task] = set()

        def schedule_response_parse(response: Response):
            task = asyncio.create_task(collector.handle_response(response))
            pending_tasks.add(task)
            task.add_done_callback(pending_tasks.discard)

        page.on("response", schedule_response_parse)

        scroll_pane = await find_scroll_pane(page)
        await scroll_to_collect_all(page, scroll_pane, collector, max_reviews=max_reviews)

        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        rows = list(collector.by_id.values())
        rows.sort(key=lambda row: (review_sort_score(row), -review_sort_timestamp(row)))
        if max_reviews is not None:
            rows = rows[:max_reviews]
        created_at = datetime.now().date().isoformat()
        for row in rows:
            row.pop("_sort_timestamp", None)
            row["created_at"] = created_at

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "review_id",
            "restaurant_id",
            "review_score",
            "review_content",
            "food_score",
            "service_score",
            "atmosphere_score",
            "created_at",
        ]
        with output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        print(f"Wrote {len(rows)} reviews to {output_path}")

        await browser.close()


async def main():
    print(f"restaurant_id: {DEFAULT_RESTAURANT_ID}")
    print(f"output: {DEFAULT_OUTPUT}")
    await scrape_reviews_to_json()


if __name__ == "__main__":
    asyncio.run(main())
