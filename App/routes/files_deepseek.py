from flask import Blueprint, render_template, request, jsonify
import requests
import openai
import os

# 配置你的 DeepSeek API Key
DEEPSEEK_API_KEY = "sk-03e0602a15394cc7b8a747c1aec5a8ae"
DEEPSEEK_API_URL = "https://api.deepseek.com"  # 请替换为真实 DeepSeek API

API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-03e0602a15394cc7b8a747c1aec5a8ae")
BASE_URL = "https://api.deepseek.com"

# 配置 OpenAI
openai.api_key = API_KEY
openai.api_base = BASE_URL

deepseek_routes = Blueprint('deepseek_routes', __name__)


def chat_with_deepseek(user_message,
                       model="deepseek-chat",
                       system_message="You are a helpful assistant",
                       stream=False):
    """
    与 DeepSeek 进行对话

    :param user_message: 用户输入的消息
    :param model: 使用的 DeepSeek 模型 (默认 deepseek-chat)
    :param system_message: 设定 AI 角色的系统提示 (默认 "You are a helpful assistant")
    :param stream: 是否使用流式输出 (默认 False)
    :return: AI 的回复内容
    """
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message},
    ]

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            stream=stream
        )
        return response.choices[0].message.content  # 返回 AI 回复
    except Exception as e:
        return f"Error: {str(e)}"  # 处理异常


@deepseek_routes.route('/ask', methods=['POST'])
def ask():
    """
        处理前端发送的用户消息，并调用 DeepSeek API 获取 AI 回复
        """
    data = request.get_json()
    user_input = data.get('message')

    if not user_input:
        return jsonify({"status": "error", "message": "消息不能为空"}), 400

    try:
        # 调用封装好的 chat_with_deepseek 函数
        ai_reply = chat_with_deepseek(user_input)

        return jsonify({
            "status": "success",
            "reply": ai_reply
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
