from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from bs4 import BeautifulSoup
import mysql.connector
from datetime import datetime
import sys

# Ensure UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

# Kết nối đến cơ sở dữ liệu MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",  # Thay bằng user của bạn
    password="123456",  # Thay bằng mật khẩu của bạn
    database="project_db"
)
cursor = conn.cursor()

# Cấu hình Selenium
options = Options()
options.add_argument("--headless")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('start-maximized')
options.add_argument("disable-infobars")
options.add_argument("User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36")
options.add_argument("Accept-Language=en-US,en;q=0.9,vi;q=0.8")
options.add_argument("Accept-Encoding=gzip, deflate, br")
options.add_argument("Connection=keep-alive")

driver_path = 'D:/Downloads/chromedriver-win64/chromedriver.exe'
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=options)

# Truy cập trang web
url = 'https://baomoi.com/tag/t%C3%ACnh-nguy%E1%BB%87n.epi'
driver.get(url)
time.sleep(3)  # Đợi tải trang

# Cuộn trang
scroll_pause_time = 2
screen_height = driver.execute_script("return window.innerHeight")
scroll_height = driver.execute_script("return document.body.scrollHeight")
current_position = 0

while current_position < scroll_height:
    driver.execute_script(f"window.scrollTo(0, {current_position + screen_height});")
    current_position += screen_height
    time.sleep(scroll_pause_time)
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.TAG_NAME, "img"))
    )

# Parse nội dung trang
soup = BeautifulSoup(driver.page_source, 'html.parser')
cards = soup.find_all('div', class_='bm-card')
num_articles = len(cards)
print(f"Số lượng bài báo tìm được: {num_articles}")

# Lấy thời gian mới nhất từ database (nếu có)
cursor.execute("SELECT MAX(full_datetime) FROM articles")
last_crawled = cursor.fetchone()[0]

# Lưu dữ liệu vào cơ sở dữ liệu MySQL
for card in cards:
    description_tag = card.find('p', class_='description')
    description = description_tag.get_text(strip=True) if description_tag else None
    if not description:
        continue

    title_tag = card.find('h3', class_='font-semibold')
    title = title_tag.get_text(strip=True) if title_tag else 'No title'

    link_tag = card.find('a', href=True)
    link = f"https://baomoi.com{link_tag['href']}" if link_tag and link_tag['href'].startswith('/') else 'No link'

    img_tag = card.find('img')
    image_url = img_tag['src'] if img_tag else 'No image'

    time_tag = card.find('time', class_='content-time')
    if time_tag and time_tag.has_attr('datetime'):
        displayed_time = time_tag.get_text(strip=True)
        try:
            full_datetime = datetime.strptime(time_tag['datetime'], "%Y-%m-%dT%H:%M:%S")  # ISO 8601
        except ValueError:
            full_datetime = None
        
        # Kiểm tra nếu bài báo mới hơn thời gian đã crawl trước đó
        if last_crawled and full_datetime and full_datetime <= last_crawled:
            print(f"Bỏ qua bài báo cũ: {title}")
            continue  # Bỏ qua nếu bài báo cũ hơn
        is_new = 'Yes'
    else:
        displayed_time = 'No time'
        full_datetime = None  # Giá trị NULL cho MySQL
        is_new = 'No'

    source_tag = card.find('a', class_='bm-card-source')
    if source_tag:
        logo_tag = source_tag.find('img')
        logo_url = logo_tag['src'] if logo_tag else 'No logo'
        source_name = logo_tag['alt'] if logo_tag else 'No source alt name'
    else:
        logo_url = 'No logo'
        source_name = 'No source name'

    # Kiểm tra xem bài báo đã tồn tại chưa
    cursor.execute("SELECT COUNT(*) FROM articles WHERE link = %s", (link,))
    exists = cursor.fetchone()[0]

    if exists == 0:
        # Chỉ chèn nếu bài báo chưa tồn tại
        cursor.execute("""
            INSERT INTO articles (title, link, image_url, displayed_time, full_datetime, is_new, source_name, logo_url, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            title,
            link,
            image_url,
            displayed_time,
            full_datetime if full_datetime else None,  # Gán NULL nếu không có giá trị datetime
            is_new,
            source_name,
            logo_url,
            description
        ))
    else:
        # Cập nhật thông tin bài báo nếu đã tồn tại
        cursor.execute("""
            UPDATE articles
            SET title = %s,
                image_url = %s,
                displayed_time = %s,
                full_datetime = %s,
                is_new = %s,
                source_name = %s,
                logo_url = %s,
                description = %s,
                updated_at = NOW()  -- Thêm trường updated_at để theo dõi thời gian cập nhật
            WHERE link = %s
        """, (
            title,
            image_url,
            displayed_time,
            full_datetime if full_datetime else None,
            is_new,
            source_name,
            logo_url,
            description,
            link
        ))
# Lưu thay đổi và đóng kết nối
conn.commit()
cursor.close()
conn.close()

# Đóng trình duyệt
driver.quit()
print("Data has been saved to the MySQL database")
