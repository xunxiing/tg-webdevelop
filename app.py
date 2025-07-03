from flask import Flask, request
import os

from models import db
from auth import auth_bp, login_manager
from main_routes import main_bp
from admin import admin_bp
from utils import increment_and_get_visit_count, USERS_FILE, API_KEY_STORE_FILE, VISIT_COUNT_FILE

app = Flask(__name__)
app.template_folder = 'templates'
app.secret_key = os.urandom(32)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/app_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)


@app.before_request
def create_tables_first_time():
    if request.endpoint == 'main.home':
        increment_and_get_visit_count()
    if not hasattr(app, 'tables_created_flag_msut'):
        with app.app_context():
            db.create_all()
        app.tables_created_flag_msut = True
        print('数据库表已检查/创建。')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    # 初始化数据文件（如果不存在）
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            f.write('{}')
    if not os.path.exists(API_KEY_STORE_FILE):
        with open(API_KEY_STORE_FILE, 'w', encoding='utf-8') as f:
            f.write('{}')
    if not os.path.exists(VISIT_COUNT_FILE):
        with open(VISIT_COUNT_FILE, 'w') as f:
            f.write('0')

    app.run(host='0.0.0.0', port=5000, debug=True)
