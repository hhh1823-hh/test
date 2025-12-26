# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai",
# ]
# ///

import os
import json
import sys
import time
from openai import OpenAI

# ==========================================
# 配置区域
# ==========================================
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# 允许从环境变量覆盖模型名称，默认为 deepseek-chat
MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")

if not API_KEY:
    print("❌ Error: 请设置环境变量 DEEPSEEK_API_KEY")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

class LongArticleAgent:
    def __init__(self, topic):
        self.topic = topic
        self.outline = []
        self.articles = []

    def step1_generate_outline(self):
        """Step 1: 生成章节大纲"""
        print(f"📋 正在规划主题: {self.topic}...")
        
        # TODO: 编写 Prompt 让模型生成纯 JSON 列表
        prompt = prompt = f"""
        你是一个内容结构化生成模型，只允许输出合法 JSON。

        请为主题《{self.topic}》生成一个 JSON 数组（Array），数组包含 3 个对象，每个对象对应一个章节。

        严格要求：
        1. 输出必须是【纯 JSON】，禁止出现任何解释性文字、Markdown、代码块标记
        2. 顶层结构必须是 JSON 数组
        3. 数组长度必须为 3
        4. 每个章节对象必须包含以下字段：
           - chapter_id：章节序号（整数，1~3）
           - title：章节标题（字符串）
           - summary：章节核心内容概述（字符串）
        5. 不得增加、删除或改名字段
        6. 不得嵌套额外层级
        7. 输出语言为中文

        现在开始生成。
        """
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,  # 使用配置的模型名
                messages=[
                    {"role": "system", "content": "你是一个专业的写作规划师，只输出 JSON Array。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            
            # TODO: 解析返回的 JSON 内容到 self.outline
            data = json.loads(content)
            
            # 简单的容错逻辑示例（候选人需要完善）
            if isinstance(data, list):
                self.outline = data
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        self.outline = value
                        break
            
            if not self.outline:
                raise ValueError("未找到有效的大纲列表")

            print(f"✅ 大纲已生成: {self.outline}")

        except Exception as e:
            print(f"❌ 大纲生成失败: {e}")
            print(f"Raw Content: {content if 'content' in locals() else 'None'}")
            sys.exit(1)

    def step2_generate_content_loop(self):
        """Step 2: 循环生成内容，并维护 Context"""
        if not self.outline:
            return

        # 初始化上下文摘要
        previous_summary = "文章开始。"
        
        print("\n🚀 开始撰写正文...")
        for i, chapter in enumerate(self.outline):
            print(f"[{i+1}/{len(self.outline)}] 正在撰写: {chapter}...")
            
            # TODO: 构造 Prompt，核心在于 Context 的注入
            prompt = f"""
            你是一名长文本写作模型，当前任务是撰写正文内容，而不是规划或总结。

            【当前章节】
            {chapter}

            【前情提要（必须严格承接，不得复述）】
            {previous_summary}

            写作要求（必须全部遵守）：
            1. 仅输出正文内容，不要出现标题、序号或解释性文字
            2. 内容必须在逻辑上直接承接【前情提要】，视其为已发生的事实背景
            3. 不得重复【前情提要】中的表述或结论
            4. 如需引入新概念，必须基于前情自然展开
            5. 正文字数控制在约 300 字（±50 字）
            6. 语言为中文，风格客观、连贯、偏书面

            现在开始撰写正文。
            """
            
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,  # 使用配置的模型名
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                content = response.choices[0].message.content
                self.articles.append(f"## {chapter}\n\n{content}")
                
                # TODO: 更新 Context (核心考察点)
                # 简单策略：截取最后 200 字
                MAX_CONTEXT_LEN = 200

                previous_summary = content[-MAX_CONTEXT_LEN:] if len(content) > MAX_CONTEXT_LEN else content
                
            except Exception as e:
                print(f"⚠️ 章节 {chapter} 生成失败: {e}")

    def save_result(self):
        if not self.articles:
            print("⚠️ 没有生成任何内容")
            return
            
        filename = "final_article.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {self.topic}\n\n")
            f.write("\n\n".join(self.articles))
        print(f"\n🎉 文章已保存至 {filename}")

if __name__ == "__main__":
    print(f"🔌 Endpoint: {BASE_URL}")
    print(f"🧠 Model: {MODEL_NAME}\n")
    
    agent = LongArticleAgent("2025年 DeepSeek 对 AI 行业的影响")
    agent.step1_generate_outline()
    agent.step2_generate_content_loop()
    agent.save_result()
