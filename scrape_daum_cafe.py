import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import datetime
import argparse

DATABASE_NAME = 'reservations.db'

# URL mapping for different categories and days of the week
# IMPORTANT: Fill in the actual URLs for all days and categories as needed.
# If a URL is missing, scraping for that specific day/category combination will be skipped.
URL_MAPPING = {
    "스튜디오/랩/라운지": {
        "월요일": "https://m.cafe.daum.net/musicpop/OM2T?boardType=",
        "화요일": "https://m.cafe.daum.net/musicpop/OM2S?boardType=",
        "수요일": "https://m.cafe.daum.net/musicpop/OM2R?boardType=",
        "목요일": "https://m.cafe.daum.net/musicpop/OM2Q?boardType=",
        "금요일": "https://m.cafe.daum.net/musicpop/OM2P?boardType=",
        "토요일": "https://m.cafe.daum.net/musicpop/OM2O?boardType=",
        "일요일": "https://m.cafe.daum.net/musicpop/OM2N?boardType=",
    },
    "일반 연습실": {
        "월요일": "https://m.cafe.daum.net/musicpop/OOSy?boardType=",
        "화요일": "https://m.cafe.daum.net/musicpop/OOSx?boardType=",
        "수요일": "https://m.cafe.daum.net/musicpop/OOUf?boardType=",
        "목요일": "https://m.cafe.daum.net/musicpop/OOUe?boardType=",
        "금요일": "https://m.cafe.daum.net/musicpop/OOUd?boardType=",
        "토요일": "https://m.cafe.daum.net/musicpop/OOUc?boardType=",
        "일요일": "https://m.cafe.daum.net/musicpop/OOSw?boardType=",
    },
    "드럼 연습실": {
        "월요일": "https://m.cafe.daum.net/musicpop/ONMu?boardType=",
        "화요일": "https://m.cafe.daum.net/musicpop/ONMt?boardType=",
        "수요일": "https://m.cafe.daum.net/musicpop/ONMs?boardType=",
        "목요일": "https://m.cafe.daum.net/musicpop/ONMr?boardType=",
        "금요일": "https://m.cafe.daum.net/musicpop/ONMq?boardType=",
        "토요일": "https://m.cafe.daum.net/musicpop/ONMp?boardType=",
        "일요일": "https://m.cafe.daum.net/musicpop/ONMo?boardType=",
    }
}

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            room_name TEXT NOT NULL,
            student_id TEXT,
            student_name TEXT,
            reservation_date TEXT NOT NULL, -- YYYY-MM-DD format
            reservation_time_slot TEXT NOT NULL, -- HH-MM format
            original_title TEXT NOT NULL,
            crawled_at TEXT NOT NULL -- YYYY-MM-DD HH:MM:SS format
        )
    ''')
    conn.commit()
    conn.close()

def scrape_and_store_reservations(target_date_str, target_category):
    init_db()
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    current_crawl_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        target_date = datetime.datetime.strptime(target_date_str, '%Y-%m-%d').date()
        prev_date = target_date - datetime.timedelta(days=1)
        prev_date_str = prev_date.strftime('%Y-%m-%d')
    except ValueError:
        print(f"Invalid date format: {target_date_str}. Please use YYYY-MM-DD.")
        return []

    # Clear existing data for both target date and previous date to avoid duplicates
    cursor.execute("DELETE FROM reservations WHERE reservation_date = ? OR reservation_date = ?", (target_date_str, prev_date_str))
    conn.commit()

    all_extracted_data = []

    # Dates to scrape: target date and the day before (for cross-midnight reservations)
    dates_to_scrape = {
        target_date_str: ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'][target_date.weekday()],
        prev_date_str: ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'][prev_date.weekday()]
    }

    categories_to_scrape = []
    if target_category == 'all':
        categories_to_scrape = URL_MAPPING.keys()
    else:
        categories_to_scrape = [target_category]

    for current_date_str, current_day_of_week in dates_to_scrape.items():
        for category in categories_to_scrape:
            if category in URL_MAPPING and current_day_of_week in URL_MAPPING[category]:
                url = URL_MAPPING[category][current_day_of_week]
                if not url:
                    print(f"No URL configured for {current_day_of_week} {category}. Skipping.")
                    continue
                
                print(f"Attempting to scrape URL: {url} for category: {category} on {current_day_of_week} ({current_date_str})")
                try:
                    response = requests.get(url)
                    response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching URL {url} for category {category}: {e}")
                    continue

                script_tags = BeautifulSoup(response.text, 'html.parser').find_all('script')
                
                found_articles_script = False
                for script in script_tags:
                    script_content = script.string
                    if script_content and 'articles.push' in script_content:
                        found_articles_script = True
                        
                        for article_data in re.findall(r'articles\.push\(\{(.*?)\}\);', script_content, re.DOTALL):
                            title_match = re.search(r'title:\s*"(.*?)"', article_data)
                            head_cont_match = re.search(r'headCont:\s*"(.*?)"', article_data)

                            title_text = title_match.group(1) if title_match else ""
                            room_name_from_headcont = head_cont_match.group(1) if head_cont_match else ""

                            final_room_name = room_name_from_headcont if room_name_from_headcont else category

                            match = re.search(r'^(\d+)/([^/]+)/(\d{1,2}\.\d{1,2})/(\d{2})-(\d{2})', title_text)
                            if match:
                                student_id = match.group(1)
                                student_name = match.group(2)
                                date_str_raw = match.group(3)
                                start_time_str = match.group(4)
                                end_time_str = match.group(5)

                                try:
                                    month, day = map(int, date_str_raw.split('.'))
                                    # Assuming the year is the current year for the reservation
                                    reservation_start_date = datetime.date(datetime.datetime.now().year, month, day)
                                except ValueError:
                                    print(f"Could not parse date {date_str_raw} from title {title_text}. Skipping.")
                                    continue

                                start_hour = int(start_time_str)
                                end_hour = int(end_time_str)

                                # Handle reservations that cross midnight
                                if start_hour > end_hour: # e.g., 23-02
                                    # Part 1: Reservation on the original date until midnight
                                    if reservation_start_date.strftime('%Y-%m-%d') == target_date_str or reservation_start_date.strftime('%Y-%m-%d') == prev_date_str:
                                        extracted_data_part1 = {
                                            "category": category,
                                            "room_name": final_room_name, 
                                            "student_id": student_id,
                                            "student_name": student_name,
                                            "reservation_date": reservation_start_date.strftime('%Y-%m-%d'),
                                            "reservation_time_slot": f"{start_time_str}-24",
                                            "original_title": title_text,
                                            "crawled_at": current_crawl_time
                                        }
                                        all_extracted_data.append(extracted_data_part1)
                                        cursor.execute('''
                                            INSERT INTO reservations (
                                                category, room_name, student_id, student_name, reservation_date, reservation_time_slot, original_title, crawled_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                        ''',
                                        (
                                            extracted_data_part1['category'],
                                            extracted_data_part1['room_name'],
                                            extracted_data_part1['student_id'],
                                            extracted_data_part1['student_name'],
                                            extracted_data_part1['reservation_date'],
                                            extracted_data_part1['reservation_time_slot'],
                                            extracted_data_part1['original_title'],
                                            extracted_data_part1['crawled_at']
                                        ))
                                        conn.commit()

                                    # Part 2: Reservation on the next day from midnight
                                    next_day_date = reservation_start_date + datetime.timedelta(days=1)
                                    if next_day_date.strftime('%Y-%m-%d') == target_date_str or next_day_date.strftime('%Y-%m-%d') == prev_date_str:
                                        extracted_data_part2 = {
                                            "category": category,
                                            "room_name": final_room_name, 
                                            "student_id": student_id,
                                            "student_name": student_name,
                                            "reservation_date": next_day_date.strftime('%Y-%m-%d'),
                                            "reservation_time_slot": f"00-{end_time_str}",
                                            "original_title": title_text,
                                            "crawled_at": current_crawl_time
                                        }
                                        all_extracted_data.append(extracted_data_part2)
                                        cursor.execute('''
                                            INSERT INTO reservations (
                                                category, room_name, student_id, student_name, reservation_date, reservation_time_slot, original_title, crawled_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                        ''',
                                        (
                                            extracted_data_part2['category'],
                                            extracted_data_part2['room_name'],
                                            extracted_data_part2['student_id'],
                                            extracted_data_part2['student_name'],
                                            extracted_data_part2['reservation_date'],
                                            extracted_data_part2['reservation_time_slot'],
                                            extracted_data_part2['original_title'],
                                            extracted_data_part2['crawled_at']
                                        ))
                                        conn.commit()
                                else: # Normal reservation within the same day
                                    if reservation_start_date.strftime('%Y-%m-%d') == target_date_str or reservation_start_date.strftime('%Y-%m-%d') == prev_date_str:
                                        extracted_data = {
                                            "category": category,
                                            "room_name": final_room_name, 
                                            "student_id": student_id,
                                            "student_name": student_name,
                                            "reservation_date": reservation_start_date.strftime('%Y-%m-%d'),
                                            "reservation_time_slot": f"{start_time_str}-{end_time_str}",
                                            "original_title": title_text,
                                            "crawled_at": current_crawl_time
                                        }
                                        all_extracted_data.append(extracted_data)
                                        cursor.execute('''
                                            INSERT INTO reservations (
                                                category, room_name, student_id, student_name, reservation_date, reservation_time_slot, original_title, crawled_at
                                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                        ''',
                                        (
                                            extracted_data['category'],
                                            extracted_data['room_name'],
                                            extracted_data['student_id'],
                                            extracted_data['student_name'],
                                            extracted_data['reservation_date'],
                                            extracted_data['reservation_time_slot'],
                                            extracted_data['original_title'],
                                            extracted_data['crawled_at']
                                        ))
                                        conn.commit()
                            else:
                                print(f"Title did not match regex: {title_text}")
                if not found_articles_script:
                    print(f"No script tag containing 'articles.push' found in {url}.")
            else:
                print(f"No URL mapping found for category: {category} on {current_day_of_week}. Skipping.")

    conn.close()
    return all_extracted_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape Daum Cafe for practice room reservations.')
    parser.add_argument('date', type=str, help='The date for which to scrape reservations (YYYY-MM-DD).')
    parser.add_argument('category', type=str, help='The category to scrape (e.g., "일반 연습실", "스튜디오/랩/라운지", or "all").')
    
    args = parser.parse_args()

    print(f"Starting data scraping and storage for date: {args.date}, category: {args.category}...")
    data = scrape_and_store_reservations(args.date, args.category)
    
    if not data:
        print("No reservation data found or stored.")
    else:
        print(f"Successfully scraped and stored {len(data)} reservations.")
        # Optional: Print a few examples
        for i, item in enumerate(data[:5]): # Print first 5 items
            print(f"Sample {i+1}: Room: {item['room_name']}, Date: {item['reservation_date']}, Time: {item['reservation_time_slot']}, Name: {item['student_name']}")