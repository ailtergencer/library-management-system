from flask import Flask, jsonify, request, g
from flask_swagger_ui import get_swaggerui_blueprint
import mysql.connector
import bcrypt
import jwt
from datetime import datetime, timedelta
from functools import wraps
from enums import BookReturnStatus  
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
app.config['SECRET_KEY'] = 'gizli_anahtar_buraya'
CORS(app)

SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.json"

swagger_ui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="kutuphane"
    )
    return conn

@app.route("/")
def home_page():
    return jsonify("ilter")

@app.route("/api/users")
def get_db_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

@app.route("/api/books", methods=["GET"])
def get_books():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM book_list")
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(books)

@app.route("/api/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM book_list WHERE id = %s", (book_id,))
    book = cursor.fetchone()
    cursor.close()
    conn.close()

    if book:
        return jsonify(book)
    else:
        return jsonify({"error": "kitap bulunamadi"}), 404


@app.route("/api/return", methods=["POST"])
def returnBook():
    data = request.get_json()
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "Eksik bilgi girdiniz"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT isAvailable FROM book_list WHERE id = %s", (book_id,))
        book = cursor.fetchone()

        if not book:
            return jsonify({"error": "Böyle bir kitap bulunamadi"}), 404

        if book["isAvailable"] == 0:
            return jsonify({"error": "Bu kitap zaten kütüphanede"}), 400

        cursor.execute("UPDATE book_list SET isAvailable = 0 WHERE id = %s", (book_id,))
        cursor.execute("""
            UPDATE borrowed_books 
            SET return_date = NOW(), status = %s 
            WHERE book_id = %s
        """, (BookReturnStatus.PENDING.value, book_id))

        conn.commit()
        return jsonify({"message": "Kitap başariyla iade edildi, admin onayı bekliyor"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    user_name = data.get("user_name")
    password = data.get("password")

    if not user_name or not password:
        return jsonify({"error": "Kullanici adi ve şifre gereklidir"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM user WHERE user_name = %s", (user_name,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()
        return jsonify({"error": "Bu kullanici adi zaten mevcut"}), 409

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    cursor.execute("INSERT INTO user (user_name, password) VALUES (%s, %s)", (user_name, hashed_pw))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": "Kullanici basariyla eklendi"}), 201

# Şifreyi hashleyen fonksiyon
def hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

# Kullanicinin girdiği şifreyi, veritabanindaki hash ile doğrulayan fonksiyon
def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))




def token_gerekli(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]

        if not token:
            return jsonify({'message': 'Token eksik!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token süresi dolmuş!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Geçersiz token!'}), 401

        return f(current_user, *args, **kwargs)
    return decorated



@app.route("/loginJWT", methods=["POST"])
def loginJWT():
    auth = request.get_json()

    if not auth or not auth.get("username") or not auth.get("password"):
        return jsonify({"message": "Kullanıcı adı ve şifre gerekli!"}), 400

    username = auth["username"]
    password = auth["password"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE user_name = %s", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        print("Veritabanındaki hash:", user["password"])
        print("Kullanıcının gönderdiği şifre:", password)

        if verify_password(password, user["password"]):
            token = jwt.encode({
                "username": username,
                "exp": datetime.utcnow() + timedelta(minutes=30)

            }, app.config["SECRET_KEY"], algorithm="HS256")
            if isinstance(token, bytes):
                token = token.decode('utf-8')

            return jsonify({"token": token})
        else:
            return jsonify({"message": "Hatalı şifre!"}), 401
    else:
        return jsonify({"message": "Kullanıcı bulunamadı!"}), 401


@app.route("/api/books/search", methods = ["GET"])
def search_books():
   query = request.args.get("query", "")

   if not query:
        return jsonify({"error": "Arama terimi gerkli"}), 400
      
   
   conn = get_db_connection()
   cursor = conn.cursor(dictionary = True)
   search_term = f"%{query}%" 
   cursor.execute("""
        SELECT * FROM book_list 
        WHERE book_name LIKE %s OR writer LIKE %s
    """, (search_term, search_term)) 
    
   results = cursor.fetchall()
   cursor.close()
   conn.close()

   return jsonify({"results": results})


@app.route('/gizli-veri', methods=['GET'])
@token_gerekli
def gizli_veri(current_user):
    return jsonify({"message": f"Hoşgeldin {current_user}, bu gizli bir veridir!"})


    


@app.route("/api/my-books", methods=["GET"])
@token_gerekli
def get_my_borrowed_books(current_user):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Önce kullanıcı adından user_id'yi bulalım
    cursor.execute("SELECT user_id FROM user WHERE user_name = %s", (current_user,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    user_id = user["user_id"]

    cursor.execute("""
    SELECT b.id AS book_id, b.book_name, b.writer AS author, bb.borrow_date, bb.return_date
    FROM borrowed_books bb
    JOIN book_list b ON bb.book_id = b.id
    WHERE bb.user_id = %s
    ORDER BY bb.borrow_date DESC
    """, (user_id,))


    borrowed_books = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"borrowed_books": borrowed_books})


@app.route("/api/borrow", methods=["POST"])
@token_gerekli
def borrow_book(current_user):
    if current_user == "admin":
        return jsonify({"error": "Admin kitap kiralayamaz!"}), 403

    data = request.get_json()
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "Kitap ID’si gerekli"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT user_id FROM user WHERE user_name = %s", (current_user,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    user_id = user["user_id"]

    cursor.execute("SELECT book_name, isAvailable FROM book_list WHERE id = %s", (book_id,))
    book = cursor.fetchone()

    if not book:
        cursor.close()
        conn.close()
        return jsonify({"error": "Kitap bulunamadı"}), 404

    if book["isAvailable"] == 1:
        cursor.close()
        conn.close()
        return jsonify({"error": "Kitap zaten kiralanmış"}), 400

    odunc_suresi = 14
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=odunc_suresi)

    borrow_date_str = borrow_date.strftime('%Y-%m-%d %H:%M:%S')
    due_date_str = due_date.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(
        "INSERT INTO borrowed_books (book_id, user_id, borrow_date, due_date) VALUES (%s, %s, %s, %s)",
        (book_id, user_id, borrow_date_str, due_date_str)
    )
    cursor.execute(
        "INSERT INTO borrow_history (borrow_history_book_id, borrow_history_user_id) VALUES (%s, %s)",
        (book_id, user_id)
    )
    cursor.execute("UPDATE book_list SET isAvailable = 1 WHERE id = %s", (book_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": f"{book['book_name']} kitabı başarıyla kiralandı",
        "due_date": due_date_str
    }), 201



@app.route("/api/admin/borrowed-books/page", methods=["GET"])
@token_gerekli
def paginated_borrowed_books(current_user):
    if current_user != "admin":
        return jsonify({"error": "Bu işlem yalnızca admin tarafından yapılabilir"}), 403

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        return jsonify({"error": "Sayfa numarası geçersiz"}), 400

    per_page = 5
    offset = (page - 1) * per_page

    conn = get_db_connection()  
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM borrowed_books")
    total_records = cursor.fetchone()["total"]
    total_pages = (total_records + per_page - 1) // per_page

    cursor.execute("""
        SELECT 
            u.user_id, u.user_name, 
            b.id AS book_id, b.book_name, b.writer AS author, 
            bb.borrow_date, bb.return_date
        FROM borrowed_books bb
        JOIN user u ON bb.user_id = u.user_id
        JOIN book_list b ON bb.book_id = b.id
        ORDER BY bb.borrow_date DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    borrowed_books = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total_records": total_records,
        "total_pages": total_pages,
        "borrowed_books": borrowed_books
    })

@app.route("/api/admin/borrowed-books-user/<int:user_id>", methods=["GET"])
@token_gerekli
def get_borrowed_books_by_user(current_user, user_id):
    if current_user != "admin":
        return jsonify({"error": "Bu işlem yalnızca admin tarafından yapılabilir"}), 403

    try:
        # Sayfa numarası al
        page = int(request.args.get('page', 1))
    except ValueError:
        return jsonify({"error": "Sayfa numarası geçersiz"}), 400

    per_page = 5
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Toplam kayıt sayısı
    cursor.execute("SELECT COUNT(*) as total FROM borrowed_books WHERE user_id = %s", (user_id,))
    total_records = cursor.fetchone()["total"]
    total_pages = (total_records + per_page - 1) // per_page

    # Sayfa verileri
    cursor.execute("""
        SELECT b.book_name, b.writer AS author, bb.borrow_date, bb.return_date
        FROM borrowed_books bb
        JOIN book_list b ON bb.book_id = b.id
        WHERE bb.user_id = %s
        ORDER BY bb.borrow_date DESC
        LIMIT %s OFFSET %s
    """, (user_id, per_page, offset))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        "user_id": user_id,
        "page": page,
        "per_page": per_page,
        "total_records": total_records,
        "total_pages": total_pages,
        "borrowed_books": rows
    })

    
    
@app.route("/api/admin/borrowed-books/<int:id>", methods=["GET"])
@token_gerekli
def get_borrowed_books_book(current_user, id):
    if current_user != "admin":
        return jsonify({"error": "Bu işlem yalnızca admin tarafından yapılabilir"}), 403

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        return jsonify({"error": "Sayfa numarası geçersiz"}), 400

    per_page = 5
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Toplam kayıt sayısı
    cursor.execute("SELECT COUNT(*) as total FROM borrowed_books WHERE book_id = %s", (id,))
    total_records = cursor.fetchone()["total"]
    total_pages = (total_records + per_page - 1) // per_page

    # Sayfa verileri
    cursor.execute("""
        SELECT b.book_name, u.user_name AS kullanici_adi,
               bb.borrow_date AS kiralama_tarihi, bb.return_date AS iade_tarihi
        FROM borrowed_books bb
        JOIN book_list b ON bb.book_id = b.id
        JOIN user u ON bb.user_id = u.user_id
        WHERE b.id = %s
        ORDER BY bb.borrow_date DESC
        LIMIT %s OFFSET %s
    """, (id, per_page, offset))

    sonuc = cursor.fetchall()
    cursor.close()
    conn.close()

    if not sonuc:
        return jsonify({"mesaj": "Kitap ile ilgili kayıt bulunamadı."}), 404

    return jsonify({
        "book_id": id,
        "page": page,
        "per_page": per_page,
        "total_records": total_records,
        "total_pages": total_pages,
        "borrowed_books": sonuc
    })



@app.route("/api/admin/pending-returns", methods=["GET"])
@token_gerekli
def get_pending_returns(current_user):
    if current_user != "admin":
        return jsonify({"error": "Bu işlem yalnızca admin tarafından yapılabilir"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT bb.id AS borrow_id, u.user_name, b.book_name, bb.borrow_date, bb.return_date, bb.status
    FROM borrowed_books bb
    JOIN user u ON bb.user_id = u.user_id
    JOIN book_list b ON bb.book_id = b.id
    WHERE bb.status = %s
    ORDER BY bb.borrow_date DESC
""", (BookReturnStatus.PENDING.value,))


    pending_returns = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({"pending_returns": pending_returns})


@app.route("/api/admin/return-status/<int:borrow_id>", methods=["PATCH"])
@token_gerekli
def update_return_status(current_user, borrow_id):
    if current_user != "admin":
        return jsonify({"error": "Bu işlem yalnızca admin tarafından yapılabilir"}), 403

    data = request.get_json()
    status = data.get("status")

    # Enum değer kontrolü
    try:
        status_enum = BookReturnStatus(status)
    except ValueError:
        return jsonify({
            "error": "Geçersiz status değeri!",
            "valid_values": {e.value: e.name for e in BookReturnStatus}
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE borrowed_books SET status = %s WHERE id = %s", (status_enum.value, borrow_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "message": f"İade edilen kitabın durumu güncellendi → {status_enum.name}"
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
