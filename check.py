import mysql.connector

# Kết nối tới cơ sở dữ liệu MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",  # Thay đổi thành username của bạn
    password="123456",  # Thay đổi thành mật khẩu của bạn
    database="project_db"  # Thay đổi tên cơ sở dữ liệu nếu cần
)
cursor = conn.cursor()

# Kiểm tra số lượng bài báo trùng (có cùng link)
check_duplicates_query = """
SELECT link, COUNT(*) 
FROM articles 
GROUP BY link 
HAVING COUNT(*) > 1;
"""
cursor.execute(check_duplicates_query)

# In ra các bài báo trùng
duplicates = cursor.fetchall()
if duplicates:
    for duplicate in duplicates:
        print(f"Link: {duplicate[0]}, Count: {duplicate[1]}")
else:
    print("Không có bài báo trùng")

# Đóng kết nối cơ sở dữ liệu
cursor.close()
conn.close()
