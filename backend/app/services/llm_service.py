import json
import re
import logging
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Lazy initialization of clients to avoid crashing on import if API keys are missing
_gemini_configured = False
_openai_client = None

def _configure_gemini():
    global _gemini_configured
    if not _gemini_configured and settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            client_options = {}
            if settings.GEMINI_API_BASE and settings.GEMINI_API_BASE.strip():
                # Strip trailing slash or protocol if necessary, but keep it clean
                endpoint = settings.GEMINI_API_BASE.strip()
                if endpoint.startswith("http://"):
                    endpoint = endpoint[7:]
                elif endpoint.startswith("https://"):
                    endpoint = endpoint[8:]
                # Remove trailing slash
                if endpoint.endswith("/"):
                    endpoint = endpoint[:-1]
                client_options["api_endpoint"] = endpoint
            genai.configure(api_key=settings.GEMINI_API_KEY, client_options=client_options)
            _gemini_configured = True
        except Exception as e:
            logger.error(f"Failed to configure Gemini API client: {e}")

def _get_openai_client():
    global _openai_client
    if _openai_client is None and settings.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            base_url = settings.OPENAI_API_BASE.strip() if settings.OPENAI_API_BASE and settings.OPENAI_API_BASE.strip() else None
            _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=base_url)
        except Exception as e:
            logger.error(f"Failed to configure OpenAI client: {e}")
    return _openai_client

def _clean_json_response(text: str) -> str:
    """Helper to extract json string from markdown formatting like ```json ... ```"""
    text = text.strip()
    # Remove markdown code block markers
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

import time

def _call_llm_raw(prompt: str, json_mode: bool = False) -> str:
    """Helper to invoke LLM based on current config."""
    if settings.LLM_PROVIDER == "gemini":
        _configure_gemini()
        if not _gemini_configured:
            raise ValueError("Gemini API key is not configured.")
        import google.generativeai as genai
        
        generation_config = {}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"
            
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text
    elif settings.LLM_PROVIDER == "openai":
        client = _get_openai_client()
        if not client:
            raise ValueError("OpenAI API key is not configured.")
        
        messages = [{"role": "user", "content": prompt}]
        response_format = {"type": "json_object"} if json_mode else None
        
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            response_format=response_format,
            temperature=0.3
        )
        return response.choices[0].message.content
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

def _call_llm(prompt: str, json_mode: bool = False, max_retries: int = 3) -> str:
    """Invokes LLM with automatic retry and exponential backoff on 429 quota errors."""
    retries = 0
    delay = 3.0
    while True:
        try:
            return _call_llm_raw(prompt, json_mode=json_mode)
        except Exception as e:
            err_msg = str(e).lower()
            
            # If the limit is explicitly 0, it is a permanent billing/quota restriction. Do not retry!
            if "limit: 0" in err_msg or "limit:0" in err_msg:
                logger.error(f"Permanent quota limit (0) detected. Aborting retries immediately: {e}")
                raise e
                
            is_rate_limit = "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg or "resourceexhausted" in err_msg or "rate limit" in err_msg
            
            if is_rate_limit and retries < max_retries:
                retries += 1
                logger.warning(f"Rate limited (429/Quota). Retrying in {delay}s... (Attempt {retries}/{max_retries})")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"LLM API call failed: {e}")
                raise e

def _get_brief_body(body: str, word_limit: int = 40, char_limit: int = 150) -> str:
    if not body:
        return ""
    words = body.strip().split()
    if len(words) > 5:
        if len(words) > word_limit:
            return " ".join(words[:word_limit]) + "..."
        return body
    else:
        if len(body) > char_limit:
            return body[:char_limit] + "..."
        return body

def classify_email(subject: str, sender: str, body: str) -> Dict[str, Any]:
    """
    Classify email into: Rejection, Opportunity, Applied, Other.
    Extract key details if it is an Opportunity or Applied.
    """
    brief_body = _get_brief_body(body)
    prompt = f"""
你是一个专业的求职助手。请分析以下邮件的标题、发件人和内容，并将其归类。

发件人: {sender}
邮件标题: {subject}
邮件内容:
{brief_body}

请根据内容进行严格判定：
1. 类别 (category) 必须为以下四者之一：
   - "Opportunity": 代表邮件是一封有实际价值的进展通知，例如：面试邀约、在线笔试邀请 (OA)、电话沟通、hr沟通邀请、简历通过筛选等。
   - "Applied": 代表邮件是一封明确的**成功提交申请/投递简历的系统确认信**（例如：“我们已收到您的简历/申请”、“感谢您申请该职位”、“您已成功投递”等收条确认，或者英文确认信如“your application for ... was successfully submitted to ...”，但尚无具体的面试或测评要求）。
   - "Rejection": 代表邮件是一封明确的系统自动拒绝信 / 感谢信（例如：“感谢您的投递，您的背景与岗位暂不匹配”、“我们决定推进其他候选人”、“已放入人才库”等）。
   - "Other": 代表其他与面试求职无关的邮件（例如：订阅的职位推送、注册确认信、广告邮件、非求职相关的个人通知等）。

2. 提取以下字段（如果无法提取则返回空字符串/空列表）：
   - company: 招聘的公司名称（如：字节跳动、腾讯、Google 等）。
   - role: 投递或沟通的岗位名称（如：后端开发工程师、Python 实习生）。
   - sender_name: 邮件中署名的发件人姓名或角色（如：HR 小张、系统自动）。
   - next_step: 邮件要求的下一步动作或截止时间（如果是 Applied，通常可以为空，或者“等待简历初筛”）。
   - summary: 一句话总结该邮件的内容（20字以内）。

请以 JSON 格式返回，不要包含任何 markdown 块或 HTML 标记，只输出 JSON。
JSON 格式示例如下：
{{
  "category": "Applied",
  "company": "示例公司",
  "role": "Python后端开发",
  "sender_name": "招聘系统",
  "next_step": "等待初筛",
  "summary": "成功投递Python后端岗位，已收到确认信"
}}
"""
    try:
        response_text = _call_llm(prompt, json_mode=True)
        cleaned_text = _clean_json_response(response_text)
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error classifying email: {e}")
        # Default fallback safely
        return {
            "category": "Other",
            "company": "",
            "role": "",
            "sender_name": "",
            "next_step": "",
            "summary": f"解析失败: {str(e)}"
        }

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate vector embeddings for a list of strings."""
    if not texts:
        return []
        
    if settings.LLM_PROVIDER == "gemini":
        _configure_gemini()
        if not _gemini_configured:
            raise ValueError("Gemini API key is not configured.")
        import google.generativeai as genai
        
        # Gemini expects single or batch texts
        try:
            result = genai.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                content=texts,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            # Fallback to single calls if batch fails
            logger.warning(f"Batch embedding failed, retrying individually: {e}")
            embeddings = []
            for text in texts:
                res = genai.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(res['embedding'])
            return embeddings
            
    elif settings.LLM_PROVIDER == "openai":
        client = _get_openai_client()
        if not client:
            raise ValueError("OpenAI API key is not configured.")
            
        try:
            response = client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise e
    else:
        raise ValueError(f"Unsupported embedding provider: {settings.LLM_PROVIDER}")

def parse_jd(jd_text: str) -> Dict[str, Any]:
    """Parse job description text to extract skills and responsibilities."""
    prompt = f"""
请分析以下招聘职位描述 (Job Description, JD)，提取出岗位核心信息，并以 JSON 格式输出。

职位描述文本:
{jd_text}

你需要提取并生成以下 JSON 字段：
- role_name: 职位名称。
- company_name: 公司名称（若未提及，请返回空）。
- required_skills: 岗位核心要求的专业技能或技术栈列表（如 Python, Docker, PyTorch 等，不超过10个）。
- soft_skills: 软实力或加分项列表（如 沟通协作、自驱力、快速学习等，不超过5个）。
- responsibilities: 岗位主要职责的要点总结列表（不超过5项）。
- summary: 一句话简单概述这个职位（30字以内）。

请以 JSON 格式返回，不要包含任何 markdown 块或 HTML 标记，只输出 JSON。
格式示例：
{{
  "role_name": "算法工程师",
  "company_name": "百度",
  "required_skills": ["Python", "PyTorch", "Transformer"],
  "soft_skills": ["团队协作", "快速学习"],
  "responsibilities": ["负责大语言模型微调", "优化检索增强生成 RAG 系统性能"],
  "summary": "负责大语言模型应用和 RAG 系统优化的算法工程师岗位"
}}
"""
    try:
        response_text = _call_llm(prompt, json_mode=True)
        cleaned_text = _clean_json_response(response_text)
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error parsing JD: {e}")
        return {
            "role_name": "未知职位",
            "company_name": "",
            "required_skills": [],
            "soft_skills": [],
            "responsibilities": [],
            "summary": "解析失败，未能成功分析职位描述"
        }

def generate_match_and_coach(jd_analysis: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate tailored interview answers and prep guides based on JD analysis and retrieved RAG context.
    """
    # Format retrieved project information for the prompt
    context_str = ""
    for idx, chunk in enumerate(retrieved_chunks):
        context_str += f"【项目来源】: {chunk['project_name']}\n"
        context_str += f"【内容片段 {idx+1}】:\n{chunk['text']}\n"
        context_str += "-" * 40 + "\n"

    prompt = f"""
你是一位资深的面试辅导专家和技术架构师。你的任务是将求职者的“个人项目经历（知识库检索结果）”与“目标岗位JD”进行深度匹配，生成一份极具针对性的面试通关指南。

--- 目标岗位信息 ---
职位: {jd_analysis.get('role_name', '未知职位')}
公司: {jd_analysis.get('company_name', '未知公司')}
核心要求技术栈: {', '.join(jd_analysis.get('required_skills', []))}
岗位职责要点:
{chr(10).join(['- ' + r for r in jd_analysis.get('responsibilities', [])])}

--- 候选人相关的项目经历（RAG 检索出的个人知识库片段） ---
{context_str}

请结合上面的输入，生成一份结构化、深度的 Markdown 报告，输出为 JSON 格式，包含以下字段：
- match_summary: 人岗匹配度综合分析（评估求职者目前的经历与该岗位的契合点、优势以及可能的技术短板，字数150-250字）。
- highlights: 定制化的“闪光点/项目话术对接”（列出3个候选人可以在简历或面试中重点突出的卖点。将岗位要求和检索出来的项目经历精确缝合。例如：“针对 Kubernetes 要求，重点讲你在 WhyFi 项目中如何部署...”）。
- prep_questions: 精选 3 个该岗位常问的面试问题，以及如何使用检索出来的项目经历（黄金 STAR 法则）进行高分回答的指导。
- technical_focus: 技术准备清单（根据岗位要求，列出 3-4 个候选人面试前必须温习的核心技术概念，并给出简要的复习提示）。

请以 JSON 格式返回，保证所有的 markdown 文本格式正确无误。不要包含任何 markdown 块或 HTML 标记，只输出 JSON。
格式示例：
{{
  "match_summary": "候选人非常契合该岗位...",
  "highlights": [
    "针对XX要求：可以在面试中介绍你在 WhyFi 项目中...",
    "针对YY技术栈..."
  ],
  "prep_questions": [
    {{
      "question": "面试问题 1",
      "star_answer": "STAR回答框架及切入点指导..."
    }}
  ],
  "technical_focus": [
    "技术概念1：需要温习的概念及其在项目中的体现...",
    "技术概念2..."
  ]
}}
"""
    try:
        response_text = _call_llm(prompt, json_mode=True)
        cleaned_text = _clean_json_response(response_text)
        return json.loads(cleaned_text)
    except Exception as e:
        logger.error(f"Error generating match and coach guide: {e}")
        return {
            "match_summary": f"生成失败。错误信息: {str(e)}",
            "highlights": ["请先在设置中配置可用的 API 密钥，并确保项目知识库中包含相关内容。"],
            "prep_questions": [
                {
                    "question": "无法生成面试问题",
                    "star_answer": "请检查大模型 API 状态。"
                }
            ],
            "technical_focus": ["基础计算机知识", "个人简历项目回顾"]
        }
