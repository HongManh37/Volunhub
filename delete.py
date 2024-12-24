import mysql.connector

# Kết nối tới cơ sở dữ liệu MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",  # Thay đổi thành username của bạn
    password="123456",  # Thay đổi thành mật khẩu của bạn
    database="project_db"  # Thay đổi tên cơ sở dữ liệu nếu cần
)
cursor = conn.cursor()

# Tạo bảng tạm để lưu trữ các link duy nhất và ID nhỏ nhất
create_temp_table = """
CREATE TEMPORARY TABLE temp_articles AS
SELECT MIN(id) AS id, link
FROM articles
GROUP BY link;
"""
cursor.execute(create_temp_table)

# Xóa các bài báo không có trong bảng tạm (tức là bài báo trùng)
delete_query = """
DELETE FROM articles
WHERE id NOT IN (SELECT id FROM temp_articles);
"""
cursor.execute(delete_query)

# Xóa bảng tạm
drop_temp_table = "DROP TEMPORARY TABLE temp_articles;"
cursor.execute(drop_temp_table)

# Commit các thay đổi và đóng kết nối
conn.commit()

# Đóng kết nối cơ sở dữ liệu
cursor.close()
conn.close()

print("Đã xóa các bài báo trùng")
