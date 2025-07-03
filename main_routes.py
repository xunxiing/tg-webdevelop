import json
import traceback
from flask import Blueprint, render_template, request, jsonify, Response, current_app
from flask_login import login_required, current_user, copy_current_request_context

from models import db, ChipCreation, AiRequestLog
from chip_logic import chip_json_to_svg_html
from ai_service import generate_chip_json_stream, get_available_models
from utils import (
    get_visit_count,
    get_api_key_for_user,
    save_api_key_for_user,
)

main_bp = Blueprint('main', __name__)

EXAMPLE_JSON_INPUT = {
    "nodes": [
        {"id": "n1", "type": "INPUT", "label": "Input A", "attrs": {"name": "#A", "data_type": "DECIMAL"}},
        {"id": "n2", "type": "Constant (Decimal)", "label": "Value 10", "attrs": {"value": 10}},
        {"id": "add1", "type": "ADD", "label": "Add A+10"},
        {"id": "out1", "type": "OUTPUT", "label": "Result", "attrs": {"name": "#Res", "data_type": "DECIMAL"}}
    ],
    "edges": [
        {"from_node": "n1", "from_port": "OUTPUT", "to_node": "add1", "to_port": "A"},
        {"from_node": "n2", "from_port": "OUTPUT", "to_node": "add1", "to_port": "B"},
        {"from_node": "add1", "from_port": "A+B", "to_node": "out1", "to_port": "INPUT"}
    ]
}


@main_bp.route('/')
def home():
    visit_count = get_visit_count()
    return render_template('home.html', visit_count=visit_count)


@main_bp.route('/generator')
def generator():
    default_json_text = json.dumps(EXAMPLE_JSON_INPUT, indent=2, ensure_ascii=False)
    user_api_key = ""
    if current_user.is_authenticated:
        user_api_key = get_api_key_for_user(current_user.username) or ""
    return render_template('chip_generator.html', default_json=default_json_text, saved_api_key=user_api_key)


@main_bp.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')


@main_bp.route('/save_api_key', methods=['POST'])
@login_required
def handle_save_api_key():
    api_key = request.form.get('api_key', '')
    if not api_key:
        return jsonify({"success": False, "error": "API Key不能为空。"}), 400
    if save_api_key_for_user(current_user.username, api_key):
        return jsonify({"success": True, "message": "API Key已成功保存。"})
    else:
        return jsonify({"success": False, "error": "API Key保存失败，请检查服务器日志。"}), 500


@main_bp.route('/get_ai_models')
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
        return jsonify({"success": False, "error": "服务器内部错误，无法获取模型列表。"}), 500


@main_bp.route('/generate_chip_ai_stream', methods=['POST'])
@login_required
def generate_chip_ai_stream_route():
    user_description = request.form.get('description', '')
    api_key_from_form = request.form.get('api_key', '')
    model_name_from_form = request.form.get('model_name', '')
    logged_in_username = current_user.username
    request_ip_address = request.remote_addr
    request_user_agent = request.user_agent.string
    if not user_description:
        def error_stream_desc():
            yield f"data: {json.dumps({'error': '描述不能为空。'})}\n\n"
            return
        return Response(error_stream_desc(), mimetype='text/event-stream')
    current_api_key = api_key_from_form or get_api_key_for_user(logged_in_username)
    if not current_api_key:
        def error_stream_key():
            yield f"data: {json.dumps({'error': 'API Key未提供或未保存。请在高级工具中设置。'})}\n\n"
            return
        return Response(error_stream_key(), mimetype='text/event-stream')
    print(f"Streaming AI request for user '{logged_in_username}' using API key (length: {len(current_api_key)}), Model: '{model_name_from_form}'")
    raw_response_accumulator = []

    @copy_current_request_context
    def event_stream_with_logging(username_for_log, current_api_key_for_stream, selected_model, ip_addr, user_agent_str):
        succeeded_parsing_json = False
        final_generated_json_str = None
        ai_error_message = None
        try:
            for chunk in generate_chip_json_stream(user_description, current_api_key_for_stream, selected_model):
                if isinstance(chunk, str):
                    raw_response_accumulator.append(chunk)
                else:
                    print(f"警告：AI流收到非字符串块: {type(chunk)}, value: {chunk}")
                    raw_response_accumulator.append(str(chunk))
                yield f"data: {json.dumps({'content': str(chunk)})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            full_raw_response = "".join(map(str, raw_response_accumulator))
            json_candidate_str = full_raw_response.strip()
            if json_candidate_str.startswith("```json"):
                json_candidate_str = json_candidate_str[7:].strip()
            if json_candidate_str.endswith("```"):
                json_candidate_str = json_candidate_str[:-3].strip()
            first_brace = json_candidate_str.find('{')
            last_brace = json_candidate_str.rfind('}')
            if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
                final_generated_json_str = json_candidate_str[first_brace: last_brace + 1]
                try:
                    json.loads(final_generated_json_str)
                    succeeded_parsing_json = True
                except json.JSONDecodeError as je:
                    print(f"AI Post-Stream JSON Parse Error: {je}")
                    ai_error_message = ai_error_message or f"AI返回了无法解析为JSON的最终内容: {je}"
                    final_generated_json_str = full_raw_response
            else:
                ai_error_message = ai_error_message or "AI未能生成可识别的JSON结构."
                final_generated_json_str = full_raw_response
        except ValueError as ve:
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
                user_agent=user_agent_str,
            )
            try:
                with current_app.app_context():
                    db.session.add(log_entry)
                    db.session.commit()
                print(f"AI Request by {username_for_log} logged. Success: {succeeded_parsing_json}")
            except Exception as db_err:
                print(f"数据库日志记录失败: {db_err}")
                db.session.rollback()
    return Response(
        event_stream_with_logging(logged_in_username, current_api_key, model_name_from_form, request_ip_address, request_user_agent),
        mimetype='text/event-stream'
    )


@main_bp.route('/generate_manual', methods=['POST'])
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
                user_agent=request.user_agent.string,
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
    except KeyError as e:
        traceback.print_exc()
        return f"生成图表时发生内部服务器错误 (数据键错误): {str(e)}", 500
    except Exception as e:
        traceback.print_exc()
        return f"生成图表时发生内部错误: {str(e)}", 500
