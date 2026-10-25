import os
import json
import logging
import imaplib
import email
from email.header import decode_header
import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import time
import socket
from urllib.parse import urlparse

from backend.app.config import settings
from backend.app.services import llm_service

logger = logging.getLogger(__name__)

def _decode_mime_words(s: str) -> str:
    """Helper to decode email header fields safely."""
    if not s:
        return ""
    try:
        decoded_parts = decode_header(s)
        decoded_str = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_str += part.decode(encoding or "utf-8", errors="replace")
                except Exception:
                    decoded_str += part.decode("latin1", errors="replace")
            else:
                decoded_str += part
        return decoded_str
    except Exception as e:
        logger.warning(f"Error decoding email header element: {e}")
        return str(s)

def _get_email_body(msg: email.message.Message) -> str:
    """Helper to extract text/plain content from an email message structure."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body += part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                except Exception:
                    pass
            elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                # If plain text not found yet, extract from html
                try:
                    html_content = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    soup = BeautifulSoup(html_content, "html.parser")
                    body += soup.get_text(separator="\n")
                except Exception:
                    pass
    else:
        content_type = msg.get_content_type()
        if content_type in ["text/plain", "text/html"]:
            try:
                payload = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
                if content_type == "text/html":
                    soup = BeautifulSoup(payload, "html.parser")
                    body = soup.get_text(separator="\n")
                else:
                    body = payload
            except Exception:
                pass
    
    # Strip excessive white lines
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return "\n".join(lines)

def load_cached_emails() -> List[Dict[str, Any]]:
    """Load pre-fetched and classified emails from local cache."""
    if os.path.exists(settings.EMAIL_CACHE_PATH):
        try:
            with open(settings.EMAIL_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading email cache file: {e}")
    return []

def save_emails_to_cache(emails_data: List[Dict[str, Any]]):
    """Write list of emails to local JSON cache."""
    os.makedirs(os.path.dirname(settings.EMAIL_CACHE_PATH), exist_ok=True)
    try:
        with open(settings.EMAIL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(emails_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error writing email cache: {e}")

def get_mock_emails() -> List[Dict[str, Any]]:
    """Returns a list of high-quality mock emails for offline demonstration."""
    mock_data = [
        {
            "id": "mock_1",
            "sender": "recruit@bytedance.com",
            "subject": "【字节跳动】后端开发工程师 - 面试时间预约",
            "date": (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "您好！感谢您投递字节跳动的后端开发工程师职位。您的履历非常符合我们的要求，希望能与您进行一次视频面试。请点击以下链接选择您方便的面试时间：https://calendar.bytedance.com/interview/book/xyz123。如有任何疑问，请回复此邮件联系 HR 张女士。谢谢！",
            "category": "Opportunity",
            "company": "字节跳动",
            "role": "后端开发工程师",
            "sender_name": "HR 张女士",
            "next_step": "点击链接预约面试时间",
            "summary": "收到字节跳动后端开发工程师的面试时间预约邀请"
        },
        {
            "id": "mock_2",
            "sender": "no-reply@tencent.com",
            "subject": "腾讯科技 - 岗位投递进展通知",
            "date": (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "亲爱的候选人，感谢您投递腾讯科技的‘云原生SRE研发’岗位。我们非常重视您的申请，然而经过认真评估，我们遗憾地通知您，目前您的背景与该职位的要求还有一些差距，我们暂时无法推进您的申请。您的简历已存入我们的人才库，一旦有合适职位我们将优先与您取得联系。祝您求职顺利！",
            "category": "Rejection",
            "company": "腾讯",
            "role": "云原生SRE研发",
            "sender_name": "系统自动",
            "next_step": "",
            "summary": "腾讯科技云原生SRE岗位简历被拒"
        },
        {
            "id": "mock_3",
            "sender": "talent-acquisition@nvidia.com",
            "subject": "NVIDIA Job Application: Technical Assessment Invitation",
            "date": (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "Dear Applicant,\nThank you for your interest in NVIDIA. We are pleased to invite you to take the Technical Online Coding Assessment (OA) for the Deep Learning Software Engineer position. \nThe assessment will be hosted on HackerRank. You will have 90 minutes to complete 3 coding tasks involving system programming and video pipelines (FFmpeg / CUDA). \nPlease complete this assessment within 7 days from receiving this email. Access Link: https://hackerrank.com/nvidia-assessment-99824.\nBest regards,\nNVIDIA Recruiting Team",
            "category": "Opportunity",
            "company": "NVIDIA",
            "role": "Deep Learning Software Engineer",
            "sender_name": "Recruiting Team",
            "next_step": "在7天内完成 HackerRank 编程测评",
            "summary": "收到 NVIDIA 深度学习软件工程师岗位 OA 笔试邀请"
        },
        {
            "id": "mock_4",
            "sender": "careers@xiaomi.com",
            "subject": "【小米集团】感谢信 - 2026届校园招聘",
            "date": (datetime.datetime.now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "同学您好：\n非常感谢您对小米集团的关注与支持！我们在收到您的简历后，组织专家进行了认真的评估。由于岗位招聘名额有限，虽然您的简历非常优秀，但由于岗位匹配度等因素，我们遗憾地通知您，您未能进入本次面试环节。再次感谢您的投递，祝您在未来的职场道路上一帆风顺！",
            "category": "Rejection",
            "company": "小米",
            "role": "算法研究员",
            "sender_name": "校招组",
            "next_step": "",
            "summary": "小米集团算法研究员岗位校招被拒"
        },
        {
            "id": "mock_5",
            "sender": "newsletter@medium.com",
            "subject": "Medium Daily Digest: Python Tips and Tricks for FastAPI Users",
            "date": (datetime.datetime.now() - datetime.timedelta(days=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "Here are some top stories for you on Medium today: 'How to build production FastAPI applications', 'Why Python 3.12 is faster than ever', and 'Mastering docker containers'. Check them out now!",
            "category": "Other",
            "company": "Medium",
            "role": "",
            "sender_name": "",
            "next_step": "",
            "summary": "Medium 日常订阅技术资讯推送"
        },
        {
            "id": "mock_6",
            "sender": "no-reply@google.com",
            "subject": "Google Careers: Application Received - Software Engineer",
            "date": (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "Hi there,\nThank you for applying for the Software Engineer, Cloud Services position at Google! We have successfully received your application. \nOur recruiting team will review your background and get back to you if there is a match. You can track your application status anytime on your Google Careers portal.\nBest regards,\nGoogle Careers Team",
            "category": "Applied",
            "company": "Google",
            "role": "Software Engineer",
            "sender_name": "Careers Team",
            "next_step": "等待初筛",
            "summary": "成功投递 Google 云软件工程师岗位并收到确认信"
        },
        {
            "id": "mock_7",
            "sender": "jobs@alibaba-inc.com",
            "subject": "【阿里巴巴】感谢投递：您的简历已成功提交！",
            "date": (datetime.datetime.now() - datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "body": "同学您好，感谢您对阿里巴巴集团的关注！您申请的‘Java研发专家’岗位简历已成功提交。目前您的简历已进入初筛阶段，后续如果有面试安排，我们将通过短信或邮件与您联系。祝您求职顺利！",
            "category": "Applied",
            "company": "阿里巴巴",
            "role": "Java研发专家",
            "sender_name": "系统自动",
            "next_step": "等待初筛",
            "summary": "成功投递阿里巴巴Java研发专家岗位"
        }
    ]
    return mock_data

RECRUITMENT_KEYWORDS = [
    "面试", "笔试", "测评", "拒", "沟通", "邀约", "投递", "申请", "感谢信", "offer", "录用",
    "校招", "社招", "招聘", "职位", "简历", "评估", "筛选", "进度", "进展", "推荐",
    "interview", "assessment", "hackerrank", "apply", "application", "career", "job",
    "recruit", "hr", "hire", "hiring", "talent", "candidate", "welcome", "confirm",
    "status", "update", "online test", "coding test", "submitted", "received"
]

def _looks_like_recruitment(subject: str, sender: str) -> bool:
    text = (subject + " " + sender).lower()
    return any(kw in text for kw in RECRUITMENT_KEYWORDS)

def connect_via_http_proxy(host: str, port: int, proxy_url: str, timeout: float = 10.0) -> socket.socket:
    """Establishes a socket connection to host:port via an HTTP CONNECT proxy tunnel."""
    if not proxy_url.startswith("http://") and not proxy_url.startswith("https://"):
        proxy_url = "http://" + proxy_url
        
    parsed = urlparse(proxy_url)
    proxy_host = parsed.hostname
    proxy_port = parsed.port or 80
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((proxy_host, proxy_port))
    
    # Send CONNECT command
    connect_request = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
    sock.sendall(connect_request.encode('utf-8'))
    
    # Read response headers until \r\n\r\n
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(1024)
        if not chunk:
            break
        response += chunk
        if len(response) > 8192:
            break
            
    header_line = response.split(b"\r\n")[0].decode('utf-8', errors='ignore')
    if "200" not in header_line:
        sock.close()
        raise RuntimeError(f"HTTP CONNECT failed: {header_line}")
        
    return sock

class ProxyIMAP4_SSL(imaplib.IMAP4_SSL):
    def __init__(self, host, port=imaplib.IMAP4_SSL_PORT, proxy_url=None, **kwargs):
        self.proxy_url = proxy_url
        super().__init__(host, port, **kwargs)
        
    def _create_socket(self, timeout=None):
        if self.proxy_url and self.proxy_url.strip():
            logger.info(f"Connecting to IMAP {self.host}:{self.port} via HTTP Proxy {self.proxy_url}...")
            raw_sock = connect_via_http_proxy(self.host, self.port, self.proxy_url, timeout=timeout or 10.0)
            return self.ssl_context.wrap_socket(raw_sock, server_hostname=self.host)
        else:
            return super()._create_socket(timeout)

def sync_emails() -> List[Dict[str, Any]]:
    """
    Syncs emails from the IMAP server. If login fails or credentials are missing,
    it falls back to mock data so the application remains fully functional for evaluation.
    """
    # 1. Verification of credentials
    if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
        logger.info("Email credentials not configured. Falling back to Mock email data.")
        # If cache exists, use cache. If not, generate mock and cache it.
        cached = load_cached_emails()
        if not cached:
            mocks = get_mock_emails()
            save_emails_to_cache(mocks)
            return mocks
        return cached

    # 2. Try to fetch from real server via IMAP
    fetched_emails = []
    try:
        # Connect to IMAP with 10s connection timeout
        logger.info(f"Connecting to IMAP server {settings.EMAIL_IMAP_SERVER}:{settings.EMAIL_IMAP_PORT}...")
        if settings.HTTP_PROXY and settings.HTTP_PROXY.strip():
            mail = ProxyIMAP4_SSL(settings.EMAIL_IMAP_SERVER, settings.EMAIL_IMAP_PORT, proxy_url=settings.HTTP_PROXY, timeout=10.0)
        else:
            mail = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_SERVER, settings.EMAIL_IMAP_PORT, timeout=10.0)
        mail.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        mail.select("inbox")

        # Compute search date
        since_date = (datetime.date.today() - datetime.timedelta(days=settings.EMAIL_SYNC_DAYS)).strftime("%d-%b-%Y")
        search_query = f'(SINCE "{since_date}")'
        logger.info(f"Searching emails with query: {search_query}")
        
        status, response = mail.search(None, search_query)
        if status != "OK":
            raise RuntimeError("IMAP search failed")

        msg_ids = response[0].split()
        logger.info(f"Found {len(msg_ids)} emails since {since_date}.")
        
        # Take only the most recent N emails to prevent timeout/huge loading times
        recent_ids = msg_ids[-settings.EMAIL_MAX_FETCH:]
        # Reverse to get newest first
        recent_ids.reverse()

        cached_emails_dict = {e["id"]: e for e in load_cached_emails()}
        new_classifications_count = 0
        
        for msg_id in recent_ids:
            str_id = msg_id.decode("utf-8")
            
            # If already classified and cached, keep it (unless it was a failed classification previously)
            if str_id in cached_emails_dict:
                cached_item = cached_emails_dict[str_id]
                # If classification failed in a previous run due to API issues, try again
                if not cached_item.get("summary", "").startswith("解析失败:"):
                    fetched_emails.append(cached_item)
                    continue

            # Fetch email headers only first to determine if we should download the full body
            status, header_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER])")
            if status != "OK" or not header_data or not header_data[0]:
                continue
                
            raw_header = header_data[0][1]
            header_msg = email.message_from_bytes(raw_header)
            
            subject = _decode_mime_words(header_msg.get("Subject", ""))
            sender = _decode_mime_words(header_msg.get("From", ""))
            date_str = header_msg.get("Date", "")
            
            # Try to format the date
            try:
                parsed_date = email.utils.parsedate_to_datetime(date_str)
                formatted_date = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_date = str(date_str)

            # Apply pre-filtering based on headers
            if not _looks_like_recruitment(subject, sender):
                logger.info(f"Skipping body fetch & LLM classification for non-recruitment email: {subject[:30]}...")
                body = ""
                classification = {
                    "category": "Other",
                    "company": "",
                    "role": "",
                    "sender_name": "",
                    "next_step": "",
                    "summary": "自动过滤: 非求职相关邮件"
                }
            else:
                # Limit the number of active API calls per sync to avoid rate limits
                if new_classifications_count >= 5:
                    logger.info(f"Quota protection active. Skipping body fetch & LLM classification for recruitment email: {subject[:30]}")
                    body = ""
                    classification = {
                        "category": "Other",
                        "company": "",
                        "role": "",
                        "sender_name": "系统自动",
                        "next_step": "",
                        "summary": "配额限制: 达到单次同步大模型分类上限 (请稍后同步)"
                    }
                else:
                    # It is recruitment-related and we have quota: fetch full body
                    logger.info(f"Recruitment email detected. Fetching full body for ID {str_id}: {subject[:30]}...")
                    status, body_data = mail.fetch(msg_id, "(BODY.PEEK[])")
                    if status == "OK" and body_data and body_data[0]:
                        raw_email = body_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        body = _get_email_body(msg)
                    else:
                        body = ""

                    # Running LLM classification for new email:
                    logger.info(f"Classifying recruitment email ID {str_id}: {subject[:30]}...")
                    try:
                        classification = llm_service.classify_email(subject, sender, body)
                        
                        # Check if it failed internally (returned a fallback dict with "解析失败:" summary)
                        if classification.get("summary", "").startswith("解析失败:"):
                            logger.warning(f"LLM classification failed internally for email ID {str_id}.")
                            err_msg = classification.get("summary", "").lower()
                            # Abort on quota limits, rate limits, timeouts, or parsing errors to prevent cascading delays
                            if any(x in err_msg for x in ["429", "quota", "limit", "rate", "timeout", "json", "delimiter", "parse", "extra data"]):
                                logger.warning("Aborting subsequent LLM calls for this sync session due to failure.")
                                new_classifications_count = 9999
                        else:
                            new_classifications_count += 1
                            time.sleep(2.0)  # Sleep 2 seconds between API requests to prevent burst 429 rate limit errors
                    except Exception as e:
                        logger.error(f"LLM classification failed for email ID {str_id}: {e}")
                        classification = {
                            "category": "Other",
                            "company": "",
                            "role": "",
                            "sender_name": "系统自动",
                            "next_step": "",
                            "summary": f"解析失败: {str(e)}"
                        }
                        # If it's a quota or rate limit error, bypass any further LLM calls in this sync session
                        err_msg = str(e).lower()
                        if "429" in err_msg or "quota" in err_msg or "limit" in err_msg or "rate" in err_msg:
                            logger.warning("Quota or rate limit hit. Aborting subsequent LLM calls for this sync session to prevent timeout.")
                            new_classifications_count = 9999
            
            email_info = {
                "id": str_id,
                "sender": sender,
                "subject": subject,
                "date": formatted_date,
                "body": body,
                **classification
            }
            fetched_emails.append(email_info)

        mail.logout()
        logger.info(f"Successfully synced and classified {len(fetched_emails)} emails.")
        
        # Cache results
        save_emails_to_cache(fetched_emails)
        return fetched_emails

    except Exception as e:
        logger.error(f"Failed to fetch emails via IMAP: {e}. Falling back to cached or mock data.")
        # Fallback to cache
        cached = load_cached_emails()
        if not cached:
            mocks = get_mock_emails()
            save_emails_to_cache(mocks)
            return mocks
        return cached
