from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from utils import load_users, save_users

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "请先登录以访问此页面。"
login_manager.login_message_category = "info"


class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        users = load_users()
        if user_id in users:
            user_data = users[user_id]
            return User(id=user_id, username=user_data['username'], password_hash=user_data['password_hash'])
        return None


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('用户名和密码不能为空！', 'danger')
            return redirect(url_for('auth.register'))
        users = load_users()
        if username in users:
            flash('该用户名已被注册！', 'warning')
            return redirect(url_for('auth.register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users[username] = {'username': username, 'password_hash': hashed_password}
        if save_users(users):
            flash('注册成功！请登录。', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('注册过程中发生错误，请稍后再试。', 'danger')
            return redirect(url_for('auth.register'))
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        if not username or not password:
            flash('请输入用户名和密码。', 'warning')
            return redirect(url_for('auth.login'))
        user_obj = User.get(username)
        if not user_obj or not check_password_hash(user_obj.password_hash, password):
            flash('用户名或密码错误，请重试。', 'danger')
            return redirect(url_for('auth.login'))
        login_user(user_obj, remember=remember, duration=timedelta(days=7))
        flash(f'欢迎回来, {username}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('home'))
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('home'))
