from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import bcrypt
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Cấu hình kết nối cơ sở dữ liệu
db_config = {
    'host': 'localhost',
    'user': 'root',  # Thay bằng tên người dùng MySQL của bạn
    'password': '123456',  # Thay bằng mật khẩu của bạn
    'database': 'project_db'  # Tên cơ sở dữ liệu
}

# -----------------------------------------
# Kết nối MySQL
# -----------------------------------------
def get_db_connection():
    return mysql.connector.connect(**db_config)

# -----------------------------------------
# Hàm hỗ trợ lấy dữ liệu
# -----------------------------------------
def get_articles(query='', date='', category='', source=''):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    sql = """
        SELECT id, 
               title AS 'Tiêu đề', 
               description AS 'Mô tả', 
               COALESCE(full_datetime, displayed_time) AS 'Ngày',  -- Lấy giá trị từ displayed_time hoặc full_datetime
               source_name AS 'Nguồn báo',  
               image_url AS 'Ảnh',  
               link AS 'Link',  
               is_new AS 'Mới',
               logo_url AS 'Logo'  
        FROM articles
        WHERE 1=1
    """
    params = []
    if query:
        sql += " AND (title LIKE %s OR description LIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])
    if date:
        sql += " AND DATE(full_datetime) = %s"
        params.append(date)
    if category:
        sql += " AND category = %s"
        params.append(category)
    if source:
        sql += " AND source_name = %s"
        params.append(source)
    
    # Sắp xếp theo trạng thái 'is_new' và 'full_datetime'
    sql += " ORDER BY is_new DESC, full_datetime DESC"
    
    cursor.execute(sql, params)
    articles = cursor.fetchall()
    cursor.close()
    conn.close()
    return articles

def get_sources():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT source_name FROM articles WHERE source_name IS NOT NULL")
    sources = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return sources

# -----------------------------------------
# Trang chính
# -----------------------------------------
@app.route('/', methods=['GET'])
def index():
    query = request.args.get('query', '')
    date = request.args.get('date', '')
    category = request.args.get('category', '')
    source = request.args.get('source', '')
    
    # Lấy các bài viết
    articles = get_articles(query=query, date=date, category=category, source=source)
    sources = get_sources()

    # Kiểm tra xem các bài viết đã được lưu chưa nếu người dùng đã đăng nhập
    if 'username' in session:
        user_id = session['user_id']
        
        # Lấy danh sách các bài viết đã được lưu của người dùng
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT article_id 
            FROM favorite_articles 
            WHERE user_id = %s
        """, (user_id,))
        
        # Chuyển đổi kết quả trả về thành danh sách các article_id
        saved_articles = cursor.fetchall()
        cursor.close()
        conn.close()

        # Kiểm tra kết quả trả về là tuple và sử dụng chỉ mục theo kiểu số
        saved_article_ids = [article[0] for article in saved_articles]  # article[0] là ID của bài viết

        # Thêm thuộc tính 'is_saved' vào các bài viết để kiểm tra đã lưu chưa
        for article in articles:
            article['is_saved'] = article['id'] in saved_article_ids

    return render_template('index.html', articles=articles, sources=sources)

# -----------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = username
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'danger')

        cursor.close()
        conn.close()

    return render_template('login.html')

# -----------------------------------------
# Xử lý đăng ký
# -----------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash.decode('utf-8')))
            conn.commit()
            flash('Đăng ký thành công! Bạn có thể đăng nhập.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f'Đã xảy ra lỗi: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# -----------------------------------------
# Lưu bài viết yêu thích
# -----------------------------------------
@app.route('/save_article', methods=['POST'])
def save_article():
    if 'username' in session:
        article_id = request.form['article_id']
        user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO favorite_articles (user_id, article_id) VALUES (%s, %s)", (user_id, article_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            # Trả về phản hồi JSON cho AJAX
            return jsonify(success=True)

        except mysql.connector.Error as err:
            cursor.close()
            conn.close()
            return jsonify(success=False, message=str(err))

    return jsonify(success=False, message="User not logged in")

# -----------------------------------------
# Xem bài viết đã lưu
# -----------------------------------------
@app.route('/saved')
def favorite_articles():
    if 'username' in session:
        user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT a.id, a.title AS 'Tiêu đề', a.description AS 'Mô tả', 
                   DATE_FORMAT(a.full_datetime, '%Y-%m-%d') AS 'Ngày', 
                   a.source_name AS 'Nguồn báo', a.image_url AS 'Ảnh', 
                   a.logo_url AS 'Logo', a.is_new AS 'Mới', 
                   sa.article_id, link AS 'Link'
            FROM favorite_articles sa
            JOIN articles a ON sa.article_id = a.id
            WHERE sa.user_id = %s
        """, (user_id,))
        favorite_articles = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('favorite_articles.html', articles=favorite_articles)

    return redirect(url_for('login'))

# -----------------------------------------
# Xóa bài viết đã lưu
# -----------------------------------------
@app.route('/delete_saved_article/<int:article_id>', methods=['POST'])
def delete_saved_article(article_id):
    if 'username' in session:
        user_id = session.get('user_id')  # Đảm bảo lấy đúng user_id từ session

        if not user_id:
            return jsonify(success=False, message="User ID not found in session")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Kiểm tra xem bài viết có tồn tại trong bảng yêu thích hay không
            cursor.execute("SELECT * FROM favorite_articles WHERE user_id = %s AND article_id = %s", (user_id, article_id))
            if not cursor.fetchone():  # Nếu không tìm thấy bài viết trong bảng yêu thích
                return jsonify(success=False, message="Article not found in saved articles")

            # Xóa bài viết khỏi bảng yêu thích
            cursor.execute("DELETE FROM favorite_articles WHERE user_id = %s AND article_id = %s", (user_id, article_id))
            conn.commit()

            # Trả về phản hồi JSON khi xóa thành công
            return jsonify({'success': True})

        except mysql.connector.Error as err:
            # Trả về phản hồi lỗi nếu có
            return jsonify(success=False, message=f'Error occurred: {err}')
        finally:
            cursor.close()
            conn.close()
    
    return jsonify(success=False, message="User not logged in")



# -----------------------------------------
# Đăng xuất
# -----------------------------------------
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# -----------------------------------------
# Chạy ứng dụng Flask
# -----------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
