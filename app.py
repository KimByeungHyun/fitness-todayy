from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

# client = MongoClient('localhost', 27017)
client = MongoClient('mongodb://test:test@localhost', 27017)
db = client.dbsparta_plus_week4

# 메인화면 구현 및 쿠키 저장
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        all_users_info = list(db.users.find({}, {'_id': False}))

        return render_template('index.html', user_info=user_info, all_users_info=all_users_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# 포스트 작성화면 구현 및 쿠키 저장
@app.route('/posting/<username>')
def user_post(username):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]}, {"_id": False})

        return render_template('posting.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# 로그인 및 회원가입 화면 구현
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

# 상세페이지 구현 및 쿠키 저장
@app.route('/post/<num>')
def detailpage(num):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        user_info = db.users.find_one({"username": payload["id"]}, {"_id": False})
        return render_template('detailpage.html', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# 로그인성공시 쿠키에 유저정보 저장
@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# 회원가입시 db에 회원정보 저장
@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    username1_receive = request.form['username1_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username1": username1_receive,                             # 이름
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디
        "profile_pic": "",                                          # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지
        "profile_info": ""                                          # 프로필 한 마디
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

# 회원가입시 받은 유저정보를 가져옴
@app.route('/sign_up/save', methods=['GET'])
def users_get():
    users_list = list(db.users.find({}, {'_id': False}))
    return jsonify({'users':users_list})

# 회원가입시 아이디 존재여부 확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

# 포스트 작성완료 시 db에 포스트 정보 저장
@app.route('/posting/save', methods=['POST'])
def posting():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})

        title_receive = request.form['title_give']
        datepicker_receive = request.form['datepicker_give']
        time_receive = request.form['time_give']
        kind_receive = request.form['kind_give']
        comment_receive = request.form['comment_give']

        file = request.files["file_give"]

        post_list = list(db.posts.find({}, {'_id': False}))
        count = len(post_list) + 1

        save_to = f'static/{count}.png'
        file.save(save_to)

        doc = {
            "num": count,
            "username": user_info["username"],
            "username1": user_info["username1"],
            "title": title_receive,
            "datepicker": datepicker_receive,
            "time": time_receive,
            "kind": kind_receive,
            "comment": comment_receive,
            "hide": 1
        }
        db.posts.insert_one(doc)
        return jsonify({'result': 'success'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# db에서 저장된 포스트 정보 가져오기
@app.route('/posting/save', methods=['GET'])
def get_post():
    posts_list = list(db.posts.find({}, {'_id': False}))
    return jsonify({'posts':posts_list})

# db에 댓글 저장
@app.route('/posting/feedback_save', methods=['POST'])
def post_feedback():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        feedback_receive = request.form['feedback_give']
        num = request.form['num_give']

        doc = {
            "name": user_info["username1"],
            "feedback": feedback_receive,
            "num": num
        }
        db.feedback.insert_one(doc)
        return jsonify({'result': 'success'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# db에 저장된 댓글 불러오기
@app.route('/posting/feedback_save', methods=['GET'])
def look_feedback():
    feedback_list = list(db.feedback.find({}, {'_id':False}))
    return jsonify({'feedbacks':feedback_list})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)