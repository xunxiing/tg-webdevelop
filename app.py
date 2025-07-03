# app.py
import json
import os
import traceback
from flask import (
    Blueprint, Flask, render_template, request, jsonify, Response,
    redirect, url_for, flash, session as flask_session, copy_current_request_context
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta

from models import db, ChipCreation, AiRequestLog
from chip_logic import chip_json_to_svg_html
from ai_service import generate_chip_json_stream, get_available_models # <--- 添加 get_available_models

app = Flask(__name__)
# 替换 'index.html' 为 'chip_generator.html'
app.template_folder = 'templates' 
app.secret_key = os.urandom(32) # 用于session加密，确保安全

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/app_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Flask-Login 配置
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # 未登录用户访问受保护页面时重定向到的路由
login_manager.login_message = "请先登录以访问此页面。"
login_manager.login_message_category = "info" # Flash消息的类别

# 文件路径定义
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_FOLDER_PATH = os.path.join(BASE_DIR, '..', 'instance') # 保证 instance 文件夹在项目根目录的上一级
if not os.path.exists(INSTANCE_FOLDER_PATH):
    os.makedirs(INSTANCE_FOLDER_PATH)
    print(f"创建 instance 文件夹于: {INSTANCE_FOLDER_PATH}")

USERS_FILE = os.path.join(INSTANCE_FOLDER_PATH, 'users.json')
API_KEY_STORE_FILE = os.path.join(INSTANCE_FOLDER_PATH, 'api_keys.json')
VISIT_COUNT_FILE = os.path.join(INSTANCE_FOLDER_PATH, 'visit_count.txt')


# 管理员凭据 (从环境变量获取，提供默认值以供开发)
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASS", "adminpass"), method='pbkdf2:sha256')

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        users = _load_users()
        if user_id in users:
            user_data = users[user_id]
            return User(id=user_id, username=user_data['username'], password_hash=user_data['password_hash'])
        return None

def _load_data(filepath, default_data=None):
    if default_data is None:
        default_data = {}
    if not os.path.exists(filepath):
        print(f"文件 {filepath} 不存在，将返回默认数据。")
        return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"读取或解析文件 {filepath} 失败: {e}。将返回默认数据。")
        return default_data

def _save_data(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"错误: 无法写入文件 {filepath}: {e}")
        return False

def _load_users():
    return _load_data(USERS_FILE)

def _save_users(users):
    return _save_data(USERS_FILE, users)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

def save_api_key_for_user(username, api_key):
    keys_data = _load_data(API_KEY_STORE_FILE)
    keys_data[username] = api_key
    if _save_data(API_KEY_STORE_FILE, keys_data):
        print(f"用户 '{username}' 的 API Key 已保存。")
        return True
    return False

def get_api_key_for_user(username):
    keys_data = _load_data(API_KEY_STORE_FILE)
    return keys_data.get(username)

def get_visit_count():
    if not os.path.exists(VISIT_COUNT_FILE):
        return 0
    try:
        with open(VISIT_COUNT_FILE, 'r') as f:
            count_str = f.read().strip()
            return int(count_str) if count_str.isdigit() else 0
    except Exception as e:
        print(f"错误：读取访问次数文件 '{VISIT_COUNT_FILE}' 失败: {e}")
        return 0

def increment_and_get_visit_count():
    count = get_visit_count()
    count += 1
    try:
        with open(VISIT_COUNT_FILE, 'w') as f:
            f.write(str(count))
        return count
    except Exception as e:
        print(f"错误：写入访问次数文件 '{VISIT_COUNT_FILE}' 失败: {e}")
        return count - 1 # 返回增加前的值或一个错误指示


EXAMPLE_JSON_INPUT = {
    "nodes": [
        {"id":"n1","type":"INPUT","label":"Input A","attrs":{"name":"#A","data_type":"DECIMAL"}},
        {"id":"n2","type":"Constant (Decimal)","label":"Value 10","attrs":{"value":10}},
        {"id":"add1","type":"ADD","label":"Add A+10"},
        {"id":"out1","type":"OUTPUT","label":"Result","attrs":{"name":"#Res","data_type":"DECIMAL"}}
    ],
    "edges": [
        {"from_node":"n1","from_port":"OUTPUT","to_node":"add1","to_port":"A"},
        {"from_node":"n2","from_port":"OUTPUT","to_node":"add1","to_port":"B"},
        {"from_node":"add1","from_port":"A+B","to_node":"out1","to_port":"INPUT"}
    ]
}

@app.before_request
def create_tables_first_time():
    # 增加网站访问量只在访问首页时进行
    if request.endpoint == 'home':
        increment_and_get_visit_count()
    
    if not hasattr(app, 'tables_created_flag_msut'): # 使用独特的属性名避免冲突
        with app.app_context():
            db.create_all()
        app.tables_created_flag_msut = True
        print("数据库表已检查/创建。")

# --- ⭐ 新增首页路由 ---
@app.route('/', methods=['GET'])
def home():
    visit_count = get_visit_count()
    return render_template('home.html', visit_count=visit_count)

# --- ⭐ 原/路由改为/generator ---
@app.route('/generator', methods=['GET'])
def generator():
    # current_total_visits = get_visit_count() # 访问量统计移到home路由
    default_json_text = json.dumps(EXAMPLE_JSON_INPUT, indent=2, ensure_ascii=False)
    user_api_key = ""
    if current_user.is_authenticated:
        user_api_key = get_api_key_for_user(current_user.username) or ""
    return render_template('chip_generator.html', default_json=default_json_text, saved_api_key=user_api_key)
@app.route('/tutorial')
def tutorial():
    """
    渲染并显示芯片教程页面。
    这个页面是一个静态内容展示页，但通过继承base.html来保持网站风格统一。
    """
    return render_template('tutorial.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home')) # 改为重定向到首页
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('用户名和密码不能为空！', 'danger')
            return redirect(url_for('register'))
        users = _load_users()
        if username in users:
            flash('该用户名已被注册！', 'warning')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users[username] = {'username': username, 'password_hash': hashed_password}
        if _save_users(users):
            flash('注册成功！请登录。', 'success')
            return redirect(url_for('login'))
        else:
            flash('注册过程中发生错误，请稍后再试。', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home')) # 改为重定向到首页
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        if not username or not password:
            flash('请输入用户名和密码。', 'warning')
            return redirect(url_for('login'))
        user_obj = User.get(username)
        if not user_obj or not check_password_hash(user_obj.password_hash, password):
            flash('用户名或密码错误，请重试。', 'danger')
            return redirect(url_for('login'))
        login_user(user_obj, remember=remember, duration=timedelta(days=7)) # 记住7天
        flash(f'欢迎回来, {username}!', 'success')
        print(f"User {username} logged in.")
        next_page = request.args.get('next')
        return redirect(next_page or url_for('home')) # 默认重定向到首页
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功登出。', 'info')
    return redirect(url_for('home')) # 登出后返回首页

# ... (handle_save_api_key, get_ai_models_route, generate_chip_ai_stream_route, generate_diagram_post_manual 保持不变) ...
# ... (admin 蓝图和路由保持不变) ...

# (所有其他函数保持不变，为简洁起见省略)
@app.route('/save_api_key', methods=['POST'])
@login_required
def handle_save_api_key():
    api_key = request.form.get('api_key', '')
    if not api_key:
        return jsonify({"success": False, "error": "API Key不能为空。"}), 400
    if save_api_key_for_user(current_user.username, api_key):
         return jsonify({"success": True, "message": "API Key已成功保存。"})
    else:
        return jsonify({"success": False, "error": "API Key保存失败，请检查服务器日志。"}), 500

@app.route('/get_ai_models', methods=['GET'])
@login_required
def get_ai_models_route():
    api_key = get_api_key_for_user(current_user.username)
    print(f"获取模型列表：用户 {current_user.username} 的 API Key 长度为 {len(api_key) if api_key else 0}。")

    try:
        models, error = get_available_models(api_key)
        if error:
            status_code = 401 if "API Key" in error or "认证失败" in error else 500
            return jsonify({"success": False, "error": f"无法获取模型列表: {error}"}), status_code
        
        if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
            print(f"get_available_models 返回的格式不正确: {models}")
            return jsonify({"success": False, "error": "从AI服务获取的模型列表格式不正确。"}), 500
            
        return jsonify({"success": True, "models": models})
    except Exception as e:
        print(f"获取AI模型列表时发生严重服务器错误: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"服务器内部错误，无法获取模型列表。"}), 500


@app.route('/generate_chip_ai_stream', methods=['POST'])
@login_required
def generate_chip_ai_stream_route():
    user_description = request.form.get('description', '')
    api_key_from_form = request.form.get('api_key', '') # 前端通常会从保存的key获取，但也可以临时提供
    model_name_from_form = request.form.get('model_name', '') # 新增：获取模型名称
    logged_in_username = current_user.username

    request_ip_address = request.remote_addr
    request_user_agent = request.user_agent.string

    if not user_description:
        def error_stream_desc(): yield f"data: {json.dumps({'error': '描述不能为空。'})}\n\n"; return
        return Response(error_stream_desc(), mimetype='text/event-stream')

    current_api_key = api_key_from_form
    if not current_api_key:
        current_api_key = get_api_key_for_user(logged_in_username)
    
    if not current_api_key:
        def error_stream_key(): yield f"data: {json.dumps({'error': 'API Key未提供或未保存。请在高级工具中设置。'})}\n\n"; return
        return Response(error_stream_key(), mimetype='text/event-stream')
        
    print(f"Streaming AI request for user '{logged_in_username}' using API key (length: {len(current_api_key)}), Model: '{model_name_from_form}'")
    raw_response_accumulator = []
    
    @copy_current_request_context
    def event_stream_with_logging(username_for_log, current_api_key_for_stream, selected_model, ip_addr, user_agent_str):
        succeeded_parsing_json = False; final_generated_json_str = None; ai_error_message = None
        try:
            # 将选中的模型名称传递给AI服务函数
            for chunk in generate_chip_json_stream(user_description, current_api_key_for_stream, selected_model):
                if isinstance(chunk, str):
                     raw_response_accumulator.append(chunk)
                else:
                    print(f"警告：AI流收到非字符串块: {type(chunk)}, value: {chunk}")
                    raw_response_accumulator.append(str(chunk))
                yield f"data: {json.dumps({'content': str(chunk)})}\n\n"
            
            yield f"data: {json.dumps({'event': 'done'})}\n\n" # 发送流结束信号

            full_raw_response = "".join(map(str, raw_response_accumulator))
            json_candidate_str = full_raw_response.strip()
            if json_candidate_str.startswith("```json"):
                json_candidate_str = json_candidate_str[7:].strip()
            if json_candidate_str.endswith("```"):
                json_candidate_str = json_candidate_str[:-3].strip()
            
            first_brace = json_candidate_str.find('{')
            last_brace = json_candidate_str.rfind('}')
            if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
                final_generated_json_str = json_candidate_str[first_brace : last_brace + 1]
                try:
                    json.loads(final_generated_json_str)
                    succeeded_parsing_json = True
                except json.JSONDecodeError as je:
                    print(f"AI Post-Stream JSON Parse Error: {je}")
                    ai_error_message = ai_error_message or f"AI返回了无法解析为JSON的最终内容: {je}"
                    final_generated_json_str = full_raw_response # 保留原始响应
            else:
                ai_error_message = ai_error_message or "AI未能生成可识别的JSON结构."
                final_generated_json_str = full_raw_response
        
        except ValueError as ve: # 例如 json.dumps 错误
            ai_error_message = str(ve)
            yield f"data: {json.dumps({'error': ai_error_message})}\n\n"
        except Exception as e:
            ai_error_message = f'AI流式生成过程中发生错误: {str(e)}'
            traceback.print_exc()
            yield f"data: {json.dumps({'error': ai_error_message})}\n\n"
        finally:
            log_entry = AiRequestLog(
                username=username_for_log,
                description=user_description,
                raw_ai_response="".join(map(str, raw_response_accumulator)),
                generated_json_str=final_generated_json_str if succeeded_parsing_json else None,
                succeeded=succeeded_parsing_json,
                error_message=ai_error_message,
                ip_address=ip_addr,
                user_agent=user_agent_str
            )
            try:
                with app.app_context(): # 确保数据库操作在应用上下文中执行
                     db.session.add(log_entry)
                     db.session.commit()
                print(f"AI Request by {username_for_log} logged. Success: {succeeded_parsing_json}")
            except Exception as db_err:
                print(f"数据库日志记录失败: {db_err}")
                db.session.rollback()
            
    return Response(event_stream_with_logging(logged_in_username, current_api_key, model_name_from_form, request_ip_address, request_user_agent), mimetype='text/event-stream')

@app.route('/generate_manual', methods=['POST'])
def generate_diagram_post_manual():
    json_data_str = request.form.get('chip_json', '')
    try:
        if not json_data_str.strip():
            return "错误：没有提供JSON数据或数据为空。", 400
        chip_data = json.loads(json_data_str)
        if not isinstance(chip_data, dict):
            return "错误：JSON数据顶层必须是一个对象。", 400
        if 'nodes' not in chip_data or not isinstance(chip_data['nodes'], list):
            return "错误：JSON数据结构不正确，缺少 'nodes' 数组或格式错误。", 400
        
        html_output_fragment = chip_json_to_svg_html(chip_data)
        
        try:
            username_to_log = current_user.username if current_user.is_authenticated else None
            log_entry = ChipCreation(
                username=username_to_log,
                chip_json_str=json_data_str,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            db.session.add(log_entry)
            db.session.commit()
            print(f"Manual chip creation by {username_to_log or 'Anonymous'} logged.")
        except Exception as log_e:
            print(f"Error logging manual chip creation: {log_e}")
            db.session.rollback()
            
        return html_output_fragment
    except json.JSONDecodeError as e:
        return f"错误：提供的JSON数据格式无效。详情: {e}", 400
    except KeyError as e: # 例如，如果 chip_json_to_svg_html 内部期望特定键
        traceback.print_exc()
        return f"生成图表时发生内部服务器错误 (数据键错误): {str(e)}", 500
    except Exception as e:
        traceback.print_exc()
        return f"生成图表时发生内部错误: {str(e)}", 500

# --- 管理面板蓝图和路由 ---
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates/admin')

def is_admin_logged_in():
    return flask_session.get('admin_logged_in')

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login_route():
    if is_admin_logged_in():
        return redirect(url_for('admin.dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            flask_session['admin_logged_in'] = True
            flask_session.permanent = True # 使 session 持久
            app.permanent_session_lifetime = timedelta(hours=1) # session 有效期
            flash('管理员登录成功！', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            error = '无效的管理员凭据。'
            flash(error, 'danger')
    return render_template('admin_login.html', error=error)

@admin_bp.route('/logout')
def admin_logout_route():
    flask_session.pop('admin_logged_in', None)
    flash('管理员已登出。', 'info')
    return redirect(url_for('admin.admin_login_route'))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin_logged_in():
            flash("请先登录管理员账户。", "warning")
            return redirect(url_for('admin.admin_login_route', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_chip_creations = ChipCreation.query.count()
    total_ai_requests = AiRequestLog.query.count()
    successful_ai_requests = AiRequestLog.query.filter_by(succeeded=True).count()
    return render_template('dashboard.html', total_chips=total_chip_creations, total_ai=total_ai_requests, successful_ai=successful_ai_requests)

@admin_bp.route('/chip_creations')
@admin_required
def chip_creations_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    creations = ChipCreation.query.order_by(ChipCreation.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('chip_creations.html', creations=creations)

@admin_bp.route('/ai_requests')
@admin_required
def ai_requests_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    ai_logs = AiRequestLog.query.order_by(AiRequestLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template('ai_requests.html', ai_logs=ai_logs)

app.register_blueprint(admin_bp)
# --- 管理面板结束 ---


if __name__ == '__main__':
    with app.app_context():
        db.create_all() # 确保表已创建
    
    # 初始化数据文件（如果不存在）
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(API_KEY_STORE_FILE):
        with open(API_KEY_STORE_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(VISIT_COUNT_FILE):
        with open(VISIT_COUNT_FILE, 'w') as f:
            f.write('0')

    app.run(host='0.0.0.0', port=5000, debug=True)