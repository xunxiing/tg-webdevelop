# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy() # SQLAlchemy实例将在app.py中初始化并绑定到app

class ChipCreation(db.Model):
    """存储用户成功生成的芯片JSON数据。"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=True) # 可以是匿名用户，所以nullable=True
    chip_json_str = db.Column(db.Text, nullable=False) # 存储JSON字符串
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True) # 记录请求IP (注意隐私)
    user_agent = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<ChipCreation {self.id} by {self.username or "Anonymous"} at {self.created_at}>'

class AiRequestLog(db.Model):
    """记录用户向AI发起的请求。"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False) # AI请求通常需要用户登录
    description = db.Column(db.Text, nullable=False) # 用户输入的描述
    raw_ai_response = db.Column(db.Text, nullable=True) # AI返回的原始文本（可能包含错误或非JSON内容）
    generated_json_str = db.Column(db.Text, nullable=True) # 成功解析出的JSON字符串
    succeeded = db.Column(db.Boolean, default=False) # AI是否成功返回并解析出JSON
    error_message = db.Column(db.Text, nullable=True) # 如果AI调用或解析失败的错误信息
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        status = "Success" if self.succeeded else "Failed"
        return f'<AiRequestLog {self.id} by {self.username} ({status}) at {self.created_at}>'

# 你也可以在这里定义 User 模型 (如果不想和 app.py 中的 UserMixin 混淆)
# 但为了简单，我们继续使用 app.py 中定义的 UserMixin 类进行登录管理，
# 而这里的模型主要用于数据记录。