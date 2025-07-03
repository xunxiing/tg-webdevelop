# ai_service.py
import openai
import json
import os
import traceback

SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
PROMPT_TUTORIAL_FILE = os.path.join(os.path.dirname(__file__), '芯片教程_gemini优化版 - v1.0.5.txt')


def load_system_prompt_from_file():
    try:
        with open(PROMPT_TUTORIAL_FILE, 'r', encoding='utf-8') as f:
            tutorial_content = f.read()
        base_system_prompt = (
            "You are an expert AI assistant specialized in generating JSON configurations "
            "for a chip logic diagram visualizer. Your goal is to convert a user's natural language "
            "description of a chip's logic into a valid JSON object. "
            "The JSON must have two top-level keys: 'nodes' and 'edges'. "
            "Strictly adhere to the JSON structure and type definitions provided in the tutorial. "
            "Do NOT add any explanatory text before or after the JSON object itself. "
            "Your entire response should be ONLY the valid JSON object, starting with '{' and ending with '}'."
        )
        full_system_prompt = f"{base_system_prompt}\n\nHere is a detailed guide and examples on the JSON structure you must follow:\n{tutorial_content}"
        return full_system_prompt
    except FileNotFoundError:
        print(f"错误: 提示词教程文件 '{PROMPT_TUTORIAL_FILE}' 未找到。将使用默认提示。")
        return ("You are an AI assistant that generates JSON for chip diagrams. The JSON must have 'nodes' and 'edges' arrays. Respond ONLY with the valid JSON object.")
    except Exception as e:
        print(f"错误: 读取提示词教程文件失败: {e}")
        # 在这种情况下，返回一个基础的、不依赖教程的提示可能更安全
        return "You are an AI assistant that generates JSON for chip diagrams. Respond ONLY with the valid JSON object with 'nodes' and 'edges' keys."

SYSTEM_PROMPT = load_system_prompt_from_file()


# 尝试从环境变量获取后备Key，如果应用需要即使在用户未提供Key时也能列出模型
FALLBACK_API_KEY_FOR_MODELS = os.environ.get("SILICONFLOW_FALLBACK_KEY_MODELS")

# 预设一些推荐的 SiliconFlow 模型 (请根据实际情况和SiliconFlow文档更新这些模型ID)
# 确保 DEFAULT_CHAT_MODEL 是这个列表中的一个，或者是一个API保证能返回的有效模型
PRESET_SILICONFLOW_MODELS = [
    "deepseek-ai/DeepSeek-V2-Chat",
    "deepseek-ai/DeepSeek-R1",
    "alibaba/Qwen2-7B-Instruct",
    "alibaba/Qwen1.5-7B-Chat",
    "THUDM/chatglm3-6b",
    "01-ai/Yi-6B-Chat",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    "mistralai/Mixtral-8x7B-Instruct-v0.1", # 可能需要付费或特定访问权限
    "meta-llama/Llama-2-13b-chat-hf",      # 可能需要付费或特定访问权限
    "google/gemma-7b-it"
]
DEFAULT_CHAT_MODEL = "deepseek-ai/DeepSeek-V2-Chat"


def get_available_models(user_api_key=None):
    """
    尝试从 SiliconFlow API 获取模型列表。
    如果失败或用户未提供有效 key，则返回预设模型列表。
    """
    key_to_use = user_api_key or FALLBACK_API_KEY_FOR_MODELS

    if not key_to_use:
        print("AI Service (get_models): 用户Key和后备Key均未提供。返回预设模型列表。")
        return PRESET_SILICONFLOW_MODELS, None # 直接返回预设，无错误信息

    fetched_model_ids = []
    error_message_str = None # 用于存储错误信息字符串

    try:
        client_for_models = openai.OpenAI(
            api_key=key_to_use,
            base_url=SILICONFLOW_BASE_URL,
            timeout=10.0, # 设置10秒超时
        )
        masked_key = f"...{key_to_use[-4:]}" if len(key_to_use) > 4 else "****"
        print(f"AI Service (get_models): 正在使用 API Key (Masked: {masked_key}) 获取模型列表...")
        
        models_response = client_for_models.models.list()
        
        if models_response and hasattr(models_response, 'data') and isinstance(models_response.data, list):
            for model_obj in models_response.data:
                if hasattr(model_obj, 'id') and isinstance(model_obj.id, str):
                    fetched_model_ids.append(model_obj.id)
            
            if fetched_model_ids:
                print(f"AI Service (get_models): 从API获取到 {len(fetched_model_ids)} 个模型。")
                # 合并API获取的列表和预设列表，确保预设的都在，并且去重
                # 并且确保默认模型在最前面（如果存在）
                combined_models = []
                if DEFAULT_CHAT_MODEL in PRESET_SILICONFLOW_MODELS or DEFAULT_CHAT_MODEL in fetched_model_ids:
                    combined_models.append(DEFAULT_CHAT_MODEL)
                
                for model_id in PRESET_SILICONFLOW_MODELS: # 先加预设
                    if model_id not in combined_models:
                        combined_models.append(model_id)
                for model_id in fetched_model_ids: # 再加API获取的
                    if model_id not in combined_models:
                        combined_models.append(model_id)
                
                print(f"AI Service (get_models): 合并和去重后模型数量: {len(combined_models)}")
                return combined_models, None # 返回成功获取的列表
            else: # API返回了空列表
                error_message_str = "API返回了空模型列表。"
                print(f"AI Service (get_models): {error_message_str}")
        else:
            error_message_str = "未能从API获取到有效的模型数据结构。"
            print(f"AI Service (get_models): {error_message_str} 响应: {models_response}")

    except openai.AuthenticationError as e:
        err_body_msg = e.body.get('message', str(e)) if hasattr(e, 'body') and e.body else str(e)
        error_message_str = f"API认证失败 (API Key可能无效): {err_body_msg}"
        print(f"AI Service (get_models): {error_message_str}")
    except openai.APITimeoutError as e:
        error_message_str = f"API请求超时: {str(e)}"
        print(f"AI Service (get_models): {error_message_str}")
    except openai.APIConnectionError as e:
        error_message_str = f"API连接错误: {str(e)}"
        print(f"AI Service (get_models): {error_message_str}")
    except Exception as e:
        error_message_str = f"获取模型列表时发生未知错误: {str(e)}"
        print(f"AI Service (get_models): {error_message_str}")
        traceback.print_exc()

    # 如果从API获取失败，则返回预设模型列表，并附带错误信息（如果发生错误）
    print(f"AI Service (get_models): 由于从API获取模型列表时发生问题 ('{error_message_str}'), 返回预设模型列表。")
    return PRESET_SILICONFLOW_MODELS, error_message_str


def generate_chip_json_stream(user_description: str, api_key: str, model_name: str = None):
    if not api_key:
        print("AI Service (generate_stream): API Key 未提供。")
        # 为了确保生成器行为一致，即使是错误也通过yield json.dumps返回
        yield json.dumps({"error": "API Key for AI service is missing."})
        return

    try:
        client_for_request = openai.OpenAI(
            api_key=api_key,
            base_url=SILICONFLOW_BASE_URL,
            timeout=30.0, # 为生成内容设置更长的超时
        )
    except Exception as e:
        print(f"AI Service (generate_stream): 初始化OpenAI客户端失败: {e}")
        yield json.dumps({"error": f"Failed to initialize AI service client: {e}"})
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_description}
    ]
    
    model_to_use = model_name if model_name and model_name.strip() else DEFAULT_CHAT_MODEL
    masked_key = f"...{api_key[-4:]}" if len(api_key) > 4 else "****"
    print(f"AI Service (generate_stream): 模型 '{model_to_use}', API Key (Masked: {masked_key}), 描述长度 {len(user_description)}.")

    try:
        stream = client_for_request.chat.completions.create(
            model=model_to_use,
            messages=messages,
            stream=True,
            max_tokens=4096, # 确保足够生成复杂的JSON
            temperature=0.2, # 较低的温度以获得更确定的输出
            top_p=0.9,
        )
        for chunk in stream:
            # 检查 chunk 和 choices 是否存在且不为空
            if chunk and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    content_chunk = delta.content
                    yield content_chunk # 直接 yield 字符串内容块
            # else:
                # print(f"AI Service (generate_stream): Received an empty or improperly structured chunk: {chunk}")
                # 可以选择忽略或记录这些空块
    
    except openai.APIConnectionError as e:
        err_msg = f"AI API 连接错误: {str(e)}"
        print(f"AI Service (generate_stream): {err_msg}")
        yield json.dumps({"error": err_msg})
    except openai.AuthenticationError as e:
        err_body_msg = e.body.get('message', str(e)) if hasattr(e, 'body') and e.body else str(e)
        err_msg = f"AI 认证失败 (API Key 可能无效或模型 '{model_to_use}' 不可用): {err_body_msg}"
        print(f"AI Service (generate_stream): {err_msg}")
        yield json.dumps({"error": err_msg})
    except openai.RateLimitError as e:
        err_msg = f"AI 速率限制错误: {str(e)}"
        print(f"AI Service (generate_stream): {err_msg}")
        yield json.dumps({"error": err_msg})
    except openai.APIStatusError as e:
        err_body_text = e.response.text if hasattr(e, 'response') else str(e)
        try: 
            err_detail_json = json.loads(err_body_text)
            err_detail = err_detail_json.get("message", err_body_text)
        except json.JSONDecodeError:
            err_detail = err_body_text
        err_msg = f"AI API 状态错误 (Status {e.status_code}) 使用模型 '{model_to_use}': {err_detail}"
        print(f"AI Service (generate_stream): {err_msg}")
        yield json.dumps({"error": err_msg})
    except Exception as e:
        err_msg = f"AI 生成时发生未知错误，模型 '{model_to_use}': {str(e)}"
        print(f"AI Service (generate_stream): {err_msg}")
        traceback.print_exc()
        yield json.dumps({"error": err_msg})