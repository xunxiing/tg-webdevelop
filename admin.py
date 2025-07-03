from datetime import timedelta
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session as flask_session
from werkzeug.security import generate_password_hash, check_password_hash

from models import ChipCreation, AiRequestLog

ADMIN_USERNAME = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASS", "adminpass"), method='pbkdf2:sha256')

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
            flask_session.permanent = True
            from flask import current_app
            current_app.permanent_session_lifetime = timedelta(hours=1)
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
