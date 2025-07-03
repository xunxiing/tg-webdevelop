import json
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_FOLDER_PATH = os.path.join(BASE_DIR, '..', 'instance')
if not os.path.exists(INSTANCE_FOLDER_PATH):
    os.makedirs(INSTANCE_FOLDER_PATH)

USERS_FILE = os.path.join(INSTANCE_FOLDER_PATH, 'users.json')
API_KEY_STORE_FILE = os.path.join(INSTANCE_FOLDER_PATH, 'api_keys.json')
VISIT_COUNT_FILE = os.path.join(INSTANCE_FOLDER_PATH, 'visit_count.txt')


def load_json(filepath, default=None):
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        print(f"文件 {filepath} 不存在，将返回默认数据。")
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"读取或解析文件 {filepath} 失败: {e}。将返回默认数据。")
        return default


def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"错误: 无法写入文件 {filepath}: {e}")
        return False


def load_users():
    return load_json(USERS_FILE)


def save_users(users):
    return save_json(USERS_FILE, users)


def save_api_key_for_user(username, api_key):
    keys_data = load_json(API_KEY_STORE_FILE)
    keys_data[username] = api_key
    if save_json(API_KEY_STORE_FILE, keys_data):
        print(f"用户 '{username}' 的 API Key 已保存。")
        return True
    return False


def get_api_key_for_user(username):
    keys_data = load_json(API_KEY_STORE_FILE)
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
        return count - 1
