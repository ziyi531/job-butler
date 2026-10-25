import streamlit as st
import requests
import os
import json

# Setup page config
st.set_page_config(
    page_title="JobButler Agent - 智能求职管家",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoint configuration
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")

# Custom CSS for rich aesthetics and premium dark mode look
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
    /* Global style overrides */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, .main-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    /* Title gradient */
    .main-title {
        background: linear-gradient(135deg, #a78bfa 0%, #6366f1 50%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
        text-align: left;
    }
    
    /* Styled container cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    
    /* Opportunity badge */
    .badge-opportunity {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Rejection badge */
    .badge-rejection {
        background: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Other badge */
    .badge-other {
        background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Applied badge */
    .badge-applied {
        background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Statistics cards styling */
    .stat-box {
        text-align: center;
        padding: 16px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stat-number {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: #818cf8;
        margin: 5px 0;
    }
    
    /* Custom button enhancements */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 24px;
        font-weight: 500;
        box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4);
        transition: all 0.2s ease;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.6);
        background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%);
    }
</style>
""", unsafe_allow_html=True)

# Helper function to fetch data from API
def api_request(method, endpoint, json_data=None, params=None):
    try:
        url = f"{BACKEND_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, params=params, timeout=90)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=90)
        else:
            return None
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        st.error(f"连接后端 API 失败: {str(e)}")
        return None

# Fetch settings state
api_settings = api_request("GET", "/settings")
api_keys_configured = False
if api_settings:
    api_keys_configured = api_settings.get("gemini_api_key_configured") or api_settings.get("openai_api_key_configured")

# Sidebar navigation
with st.sidebar:
    st.markdown("<h2 style='font-family:Outfit; color:#818cf8;'>💼 JobButler Agent</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Render Status
    if api_settings:
        st.sidebar.markdown("### 🔌 系统状态")
        provider = api_settings.get("llm_provider", "Unknown").upper()
        email_addr = api_settings.get("email_address")
        
        status_md = f"**当前模型**: `{provider}` "
        if api_keys_configured:
            status_md += "🟢"
        else:
            status_md += "🔴 (未配置Key)"
            
        st.sidebar.markdown(status_md)
        
        if email_addr:
            st.sidebar.markdown(f"**邮箱监听**: `{email_addr}` 🟢")
        else:
            st.sidebar.markdown("**邮箱监听**: `未配置 (演示模式)` 🟡")
    
    st.markdown("---")
    
    menu = st.radio(
        "导航菜单",
        ["📬 智能邮件监听", "🗂️ 项目知识库 (RAG)", "🎯 JD 人岗匹配器", "⚙️ 系统设置"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("🎒 *Powered by Google Gemini*")

# ==================== TAB 1: EMAIL DASHBOARD ====================
if menu == "📬 智能邮件监听":
    st.markdown('<div class="main-title">智能邮件监听与分类</div>', unsafe_allow_html=True)
    st.markdown("定时或按需抓取邮箱，大模型自动过滤和分类系统拒信、面试邀约、OA 笔试邀请。")
    
    # Sync button and info
    col_btn, col_info = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 同步并分析邮件"):
            with st.spinner("正在从邮箱同步并使用大模型分析..."):
                sync_res = api_request("POST", "/emails/sync")
                if sync_res:
                    st.success(f"成功同步并分类了 {sync_res.get('count', 0)} 封邮件！")
                    st.rerun()
                    
    with col_info:
        if not api_keys_configured:
            st.warning("⚠️ 检测到您尚未在【系统设置】中配置 LLM API Key，目前运行在【演示模式】，使用的是缓存的模拟邮件数据。")
        else:
            st.info("💡 邮件提取将自动通过您设置的 IMAP 服务器下载最近 14 天的邮件进行分类。")

    # Fetch all emails
    emails = api_request("GET", "/emails")
    
    if not emails:
        st.info("当前暂无邮件数据，请点击上方“同步并分析邮件”按钮。")
    else:
        # Compute stats
        total = len(emails)
        opps = len([e for e in emails if e.get("category") == "Opportunity"])
        applieds = len([e for e in emails if e.get("category") == "Applied"])
        rejs = len([e for e in emails if e.get("category") == "Rejection"])
        others = total - opps - applieds - rejs
        
        # Display stat widgets
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f'<div class="stat-box">全部邮件<div class="stat-number">{total}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-box" style="border-color: rgba(16, 185, 129, 0.3);">面试/流程机会 🟢<div class="stat-number" style="color:#10b981;">{opps}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-box" style="border-color: rgba(6, 182, 212, 0.3);">已投递申请 🔵<div class="stat-number" style="color:#06b6d4;">{applieds}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="stat-box" style="border-color: rgba(244, 63, 94, 0.3);">系统自动拒信 🔴<div class="stat-number" style="color:#f43f5e;">{rejs}</div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="stat-box">其他订阅邮件 ⚪<div class="stat-number" style="color:#9ca3af;">{others}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>### 📥 邮件列表", unsafe_allow_html=True)
        
        # Filter selectors
        cat_filter = st.tabs(["💡 全部", "🟢 有戏机会", "🔵 已投递", "🔴 系统拒信", "⚪ 其他/推送"])
        
        categories = [None, "Opportunity", "Applied", "Rejection", "Other"]
        
        for idx, tab in enumerate(cat_filter):
            with tab:
                curr_cat = categories[idx]
                filtered_emails = [e for e in emails if e.get("category") == curr_cat] if curr_cat else emails
                
                if not filtered_emails:
                    st.write("此分类下暂无邮件。")
                    continue
                
                for mail in filtered_emails:
                    cat = mail.get("category", "Other")
                    
                    # Select badge style
                    if cat == "Opportunity":
                        badge = '<span class="badge-opportunity">机会</span>'
                        opp_details = f"""
                        <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; padding: 12px; border-radius: 4px; margin-top: 10px; margin-bottom: 10px;">
                            <strong>🏢 归属公司：</strong> {mail.get('company', '未识别')} &nbsp;&nbsp;&nbsp;&nbsp;
                            <strong>💼 岗位职位：</strong> {mail.get('role', '未识别')} <br>
                            <strong>🙋 发件人/HR：</strong> {mail.get('sender_name', '未识别')} &nbsp;&nbsp;&nbsp;&nbsp;
                            <strong>📅 下一步行动：</strong> <span style="color:#10b981; font-weight:bold;">{mail.get('next_step', '无')}</span>
                        </div>
                        """
                    elif cat == "Applied":
                        badge = '<span class="badge-applied">已投递</span>'
                        opp_details = f"""
                        <div style="background: rgba(6, 182, 212, 0.08); border-left: 4px solid #06b6d4; padding: 12px; border-radius: 4px; margin-top: 10px; margin-bottom: 10px;">
                            <strong>🏢 投递公司：</strong> {mail.get('company', '未识别')} &nbsp;&nbsp;&nbsp;&nbsp;
                            <strong>💼 申请岗位：</strong> {mail.get('role', '未识别')} <br>
                            <strong>🙋 确认方/发件人：</strong> {mail.get('sender_name', '系统自动')} &nbsp;&nbsp;&nbsp;&nbsp;
                            <strong>📅 当前状态：</strong> <span style="color:#06b6d4; font-weight:bold;">{mail.get('next_step', '等待初筛')}</span>
                        </div>
                        """
                    elif cat == "Rejection":
                        badge = '<span class="badge-rejection">拒信</span>'
                        opp_details = ""
                    else:
                        badge = '<span class="badge-other">其他</span>'
                        opp_details = ""

                    header_html = f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                        <div>
                            {badge} <strong>{mail.get('subject')}</strong> 
                            <span style="color:#9ca3af; font-size:0.85rem; margin-left: 10px;">(发件人: {mail.get('sender')})</span>
                        </div>
                        <div style="color:#9ca3af; font-size:0.85rem;">{mail.get('date')}</div>
                    </div>
                    """
                    
                    with st.expander(f"{mail.get('date')} | {mail.get('company', '')} - {mail.get('subject')[:45]}..."):
                        st.markdown(header_html, unsafe_allow_html=True)
                        if opp_details:
                            st.markdown(opp_details, unsafe_allow_html=True)
                        st.markdown(f"**🤖 AI 摘要:** {mail.get('summary', '无摘要')}")
                        st.markdown("---")
                        st.markdown("**邮件正文:**")
                        st.code(mail.get("body", ""), language="text")
                        
                        # Add quick match action if opportunity or applied
                        if cat in ["Opportunity", "Applied"]:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("🎯 一键将该工作发起人岗匹配", key=f"match_{idx}_{mail.get('id')}"):
                                # Switch session state to matchmaker and feed the mail body
                                st.session_state["jd_input_text"] = mail.get("body", "")
                                st.session_state["selected_menu"] = "🎯 JD 人岗匹配器"
                                st.info("已将邮件正文导入 JD 匹配器，请点击左侧菜单切换到 [🎯 JD 人岗匹配器] 查看！")

# ==================== TAB 2: KNOWLEDGE BASE ====================
elif menu == "🗂️ 项目知识库 (RAG)":
    st.markdown('<div class="main-title">个人项目知识库 (RAG)</div>', unsafe_allow_html=True)
    st.markdown("管理和向量化您的个人项目经历。当遇到新岗位要求时，RAG 能瞬间帮您找出最契合的过往经验素材。")
    
    # Vector store status
    db_status_res = api_request("GET", "/settings")
    
    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        if st.button("⚙️ 重构项目向量索引"):
            with st.spinner("正在切片并为您的个人项目文件生成向量嵌入..."):
                index_res = api_request("POST", "/projects/index")
                if index_res and index_res.get("status") == "success":
                    st.success(f"索引重建成功！共处理了 {index_res.get('indexed_files')} 个文件，生成了 {index_res.get('chunks')} 个文本片段。")
                    st.rerun()
    with col_status:
        if not api_keys_configured:
            st.error("❌ 您尚未配置 LLM API 密钥，无法使用向量索引构建服务。请先前往【系统设置】进行配置。")
        else:
            st.success("🤖 已连接向量嵌入服务模型。可随时点击左侧按钮，将 `projects_kb/` 下的项目文件进行全量更新。")

    st.markdown("---")
    
    # List current project files
    projects = api_request("GET", "/projects")
    
    tab_list, tab_create = st.tabs(["📂 查看已有项目", "➕ 新增/编辑项目"])
    
    with tab_list:
        if not projects:
            st.info("目前还没有任何项目文档，请切换到“新增/编辑项目”选项卡添加您的第一个项目经历。")
        else:
            project_names = [p["name"] for p in projects]
            selected_proj_name = st.selectbox("选择要查看的项目文档", project_names)
            
            # Find chosen project content
            selected_proj = next(p for p in projects if p["name"] == selected_proj_name)
            
            col_view, col_raw = st.columns(2)
            with col_view:
                st.markdown("#### 📄 渲染后效果")
                st.markdown(f'<div class="glass-card">{selected_proj["content"]}</div>', unsafe_allow_html=True)
            with col_raw:
                st.markdown("#### 📝 Markdown 源码")
                st.text_area("编辑源码", selected_proj["content"], height=400, disabled=True)
                
    with tab_create:
        st.markdown("### ✍️ 创建新的个人项目 Markdown 文档")
        st.markdown("建议详细写明您的**项目介绍、核心技术栈、架构实现细节、高并发或难点优化**。越详细的背景，RAG 在面试匹配时的效果越好。")
        
        new_proj_name = st.text_input("项目英文/拼音标识 (用作文件名，如: whyfi_platform, ffmpeg_pipeline)", placeholder="my_new_project")
        
        # Default template
        template = """# 项目名称 (例如: 某某分布式电商系统)

简短的项目整体介绍，说明解决了什么痛点、核心业务是什么。

## 核心技术栈
- 后端/前端框架: Spring Boot / FastAPI / React
- 数据库: MySQL, Redis
- 部署与中间件: Docker, RabbitMQ

## 系统架构与实现细节
### 1. 核心模块一 (例如: 高并发抢购网关)
- 详细描述你怎么实现这个功能的。
- 遇到了什么技术挑战，又是如何攻克的。

### 2. 核心模块二 (例如: 分布式一致性设计)
- 解决数据一致性的具体实现。
"""
        new_proj_content = st.text_area("项目 Markdown 内容", value=template, height=350)
        
        if st.button("💾 保存项目文档"):
            if not new_proj_name.strip():
                st.error("项目标识不能为空！")
            else:
                save_res = api_request("POST", "/projects", json_data={"filename": new_proj_name, "content": new_proj_content})
                if save_res and save_res.get("status") == "success":
                    st.success(f"成功保存 `{new_proj_name}.md`！请记得在上方点击【重构项目向量索引】使更改生效。")
                    st.rerun()

# ==================== TAB 3: JD MATCHMAKER ====================
elif menu == "🎯 JD 人岗匹配器":
    st.markdown('<div class="main-title">人岗匹配与定制化面试指南</div>', unsafe_allow_html=True)
    st.markdown("输入或从邮件导入招聘 JD。Agent 会自动抽取硬/软实力技能，利用 RAG 检索个人项目经验，生成定制化的简历闪光点和专属面试复习通关指南。")

    # Get input text from session state (if imported from mail dashboard)
    default_jd = st.session_state.get("jd_input_text", "")
    
    # Sample JD templates to quickly test the application
    st.markdown("#### ⚡ 快速加载测试岗位 JD 模板")
    col_t1, col_t2, col_t3 = st.columns(3)
    
    sample_jd_whyfi = """【高薪诚聘】量化私募基金 - 高级 Python 研发工程师
岗位职责：
1. 负责量化交易回测系统和实时风控/数据推理平台的开发与架构优化；
2. 配合算法团队对高频交易策略进行容器化部署和上线调度；
3. 负责高并发数据清洗和异常流拦截过滤，保障核心交易链路毫秒级响应。

任职要求：
1. 3年以上Python核心开发经验，精通 FastAPI / Uvicorn 异步编程；
2. 熟练掌握 Docker 容器技术，有 Kubernetes 分布式集群部署经验者优先；
3. 熟悉 MLOps 流水线，了解 MLflow / Prometheus 等系统监控体系；
4. 拥有良好的沟通与抗压能力，注重代码质量。"""

    sample_jd_ffmpeg = """字节跳动 - UGC流媒体视频算法与架构工程师
职责描述：
1. 负责抖音/剪映等核心视频处理引擎的设计、优化与维护，优化视频转码和流媒体分片吞吐；
2. 开发高并发的音视频清洗流水线，包含动态水印添加、字幕硬烧录和图像画质矫正；
3. 优化视频在云端分布式计算集群（K8s）中的弹性伸缩策略。

任职要求：
1. 深入理解音视频编解码原理，熟练掌握 FFmpeg 命令行、libavcodec 库及滤镜设计；
2. 精通 Python / C++，熟悉 Celery / Redis 分布式任务调度与 RabbitMQ 数据队列；
3. 掌握分布式文件系统（如 MinIO / S3）及高并发 I/O 优化；
4. 能够在高压环境下进行独立技术攻坚，快速定位视频流异常。"""

    if col_t1.button("📊 量化金融 Python 工程师 (匹配 WhyFi)"):
        st.session_state["jd_input_text"] = sample_jd_whyfi
        st.rerun()
    if col_t2.button("🎬 UGC 视频架构师 (匹配 FFmpeg)"):
        st.session_state["jd_input_text"] = sample_jd_ffmpeg
        st.rerun()
    if col_t3.button("🧹 清空输入框"):
        st.session_state["jd_input_text"] = ""
        st.rerun()

    # JD Input Box
    jd_text = st.text_area("请粘贴招聘岗位描述 (Job Description, JD)", value=default_jd, height=220)
    
    if st.button("🚀 开始人岗精准匹配"):
        if not jd_text.strip():
            st.error("请先粘贴岗位 JD 文本后再点击匹配按钮。")
        elif not api_keys_configured:
            st.error("❌ 您尚未配置大模型 API Key。此核心匹配功能需要 LLM 进行语义推理与生成，请先前往【系统设置】进行配置。")
        else:
            with st.spinner("1. 正在深入解析岗位技术栈... \n2. 正在 RAG 检索您的个人项目库... \n3. 正在生成定制化面试回答指南..."):
                match_results = api_request("POST", "/match", json_data={"jd_text": jd_text})
                
                if match_results:
                    st.session_state["match_results"] = match_results
                    st.success("✨ 匹配分析完成！")

    # Render results if available in session
    if "match_results" in st.session_state:
        res = st.session_state["match_results"]
        jd_anal = res.get("jd_analysis", {})
        coach = res.get("coach_guide", {})
        chunks = res.get("retrieved_chunks", [])
        
        st.markdown("---")
        st.markdown(f"## 📊 匹配报告: {jd_anal.get('company_name', '')} - {jd_anal.get('role_name', '')}")
        
        # 1. Row 1: JD Analysis Summary & RAG Clues
        col_jd, col_rag = st.columns([1, 1])
        with col_jd:
            st.markdown("### 🔎 岗位画像提取")
            st.markdown(f"**岗位概述**: {jd_anal.get('summary', '无')}")
            
            # Skills tag display
            skills_html = ""
            for skill in jd_anal.get("required_skills", []):
                skills_html += f'<span style="background-color:#4f46e5; color:white; padding:2px 8px; border-radius:4px; margin-right:5px; font-size:0.85rem; display:inline-block; margin-bottom:5px;">{skill}</span>'
            st.markdown(f"**核心硬实力要求**:<br>{skills_html}", unsafe_allow_html=True)
            
            soft_skills_html = ""
            for skill in jd_anal.get("soft_skills", []):
                soft_skills_html += f'<span style="background-color:#374151; color:white; padding:2px 8px; border-radius:4px; margin-right:5px; font-size:0.85rem; display:inline-block; margin-bottom:5px;">{skill}</span>'
            st.markdown(f"**软实力/加分项**:<br>{soft_skills_html}", unsafe_allow_html=True)
            
            st.markdown("**岗位核心职责**:")
            for resp in jd_anal.get("responsibilities", []):
                st.markdown(f"- {resp}")
                
        with col_rag:
            st.markdown("### 📂 RAG 知识库检索线索")
            st.markdown("以下为系统自动从您的项目经历中检索到的最相似文本片段，已输入大模型作为面试辅导的素材背景：")
            
            for i, chunk in enumerate(chunks):
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                        <span style="color:#818cf8; font-weight:600; font-size:0.85rem;">📂 项目：{chunk.get('project_name')}</span>
                        <span style="color:#10b981; font-size:0.85rem;">相关度: {int(chunk.get('score', 0) * 100)}%</span>
                    </div>
                    <div style="font-size:0.85rem; color:#d1d5db; max-height:100px; overflow-y:auto; font-family:monospace; white-space: pre-wrap;">{chunk.get('text')}</div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("---")
        
        # 2. Main Match Guide Content
        st.markdown("### 🏆 专属面试通关指南")
        
        # Match Summary
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%); border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
            <h4 style="margin-top:0; color:#a78bfa; font-family:Outfit;">💡 人岗匹配度综合评估</h4>
            <p style="margin-bottom:0; font-size:0.95rem; line-height:1.6;">{coach.get('match_summary')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs for highlights, questions, technical review
        tab_highlights, tab_qa, tab_tech = st.tabs(["✨ 简历与自我介绍闪光点", "❓ 模拟面试黄金 QA (STAR)", "📚 面试前技术速记清单"])
        
        with tab_highlights:
            st.markdown("建议将以下亮点话术缝合进您的自我介绍或简历描述中：")
            for highlight in coach.get("highlights", []):
                st.markdown(f"""
                <div class="glass-card" style="border-left:4px solid #818cf8; padding:15px; margin-bottom:12px;">
                    {highlight}
                </div>
                """, unsafe_allow_html=True)
                
        with tab_qa:
            st.markdown("针对该岗位的核心面试设问，为您基于个人项目定制的黄金 STAR 回答框架：")
            for q_idx, q_item in enumerate(coach.get("prep_questions", [])):
                st.markdown(f"#### 问题 {q_idx+1}: {q_item.get('question')}")
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.03); border: 1px dashed rgba(255,255,255,0.1); border-radius:8px; padding:16px; margin-bottom:20px; line-height:1.6;">
                    <strong>🌟 STAR 回答要点/切入方案:</strong><br>
                    {q_item.get('star_answer')}
                </div>
                """, unsafe_allow_html=True)
                
        with tab_tech:
            st.markdown("该职位要求中您较薄弱或必须温习的核心技术概念，请在面试前快速复习：")
            for t_idx, tech_item in enumerate(coach.get("technical_focus", [])):
                st.markdown(f"- {tech_item}")

# ==================== TAB 4: SETTINGS ====================
elif menu == "⚙️ 系统设置":
    st.markdown('<div class="main-title">系统配置与设置</div>', unsafe_allow_html=True)
    st.markdown("配置您的大模型 API 密钥与邮箱监听 IMAP 服务器。配置后设置会安全保存到本地 `.env` 环境变量文件中。")
    
    if api_settings:
        # LLM Settings Form
        st.markdown("### 🤖 大模型配置 (LLM Configuration)")
        llm_provider = st.selectbox(
            "选择激活的 LLM 供应商",
            ["gemini", "openai"],
            index=0 if api_settings.get("llm_provider") == "gemini" else 1
        )
        
        col_g, col_o = st.columns(2)
        with col_g:
            gemini_key = st.text_input(
                "Gemini API Key",
                value="" if not api_settings.get("gemini_api_key_configured") else "🟢 KEY_ALREADY_CONFIGURED",
                type="password",
                help="如果需要重新设置 API Key，请在这里输入您的新密钥；留空代表沿用之前的密钥。"
            )
            gemini_base = st.text_input(
                "Gemini API Base URL (可选代理/中转端点)",
                value=api_settings.get("gemini_api_base", ""),
                help="选填。如果使用第三方 Gemini 代理端点（如: api.aigc360.com），请在此配置，留空则默认直连 Google 官方"
            )
            gemini_model = st.text_input(
                "Gemini 激活模型名称",
                value=api_settings.get("gemini_model", "gemini-2.0-flash"),
                help="指定调用的 Gemini 模型名称"
            )
        with col_o:
            openai_key = st.text_input(
                "OpenAI API Key",
                value="" if not api_settings.get("openai_api_key_configured") else "🟢 KEY_ALREADY_CONFIGURED",
                type="password",
                help="如果选择 OpenAI 供应商，请填入密钥。留空代表沿用之前的密钥。"
            )
            openai_base = st.text_input(
                "OpenAI API Base URL (中转 / 代理 / DeepSeek 地址)",
                value=api_settings.get("openai_api_base", ""),
                help="如果您使用中转 API 或 DeepSeek，请在此填写接口地址（如: https://api.deepseek.com/v1）"
            )
            openai_model = st.text_input(
                "OpenAI 激活模型名称",
                value=api_settings.get("openai_model", "gpt-4o-mini"),
                help="指定调用的模型名称（如果使用的是 DeepSeek，可配置为 deepseek-chat）"
            )

        st.markdown("---")
        
        # Email Settings Form
        st.markdown("### 📬 邮箱监听配置 (Email Listener Settings)")
        st.markdown("使用 IMAP 协议拉取招聘邮件。如果使用 Gmail，您必须生成一个专门的 **App Password (应用密码)**。")
        
        imap_server = st.text_input("IMAP 服务器地址 (Gmail 为 `imap.gmail.com`)", value=api_settings.get("email_imap_server", ""))
        email_address = st.text_input("您的邮箱地址 (如: username@gmail.com)", value=api_settings.get("email_address", ""))
        email_pwd = st.text_input(
            "邮箱密码 / 授权应用密码",
            value="" if not api_settings.get("email_password_configured") else "🟢 PASSWORD_ALREADY_CONFIGURED",
            type="password",
            help="输入您账号生成的 16 位邮箱 App 授权密码，而不是您的日常登录密码。"
        )
        
        st.markdown("---")
        st.markdown("### 🌐 网络代理配置 (Network Proxy Settings)")
        st.markdown("如果您在境内访问 Gemini / OpenAI API 或是同步 Gmail 遇到连接超时、配额受限（429）等问题，请在下方配置本地 network 代理端口。")
        http_proxy = st.text_input(
            "HTTP/HTTPS 代理地址",
            value=api_settings.get("http_proxy", ""),
            placeholder="http://127.0.0.1:7890",
            help="填写您本地代理软件运行的 HTTP 协议端口地址。留空代表使用网络直连。"
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Save Settings
        if st.button("💾 保存并应用设置"):
            # Construct update body
            update_data = {
                "llm_provider": llm_provider,
                "gemini_api_base": gemini_base,
                "gemini_model": gemini_model,
                "openai_api_base": openai_base,
                "openai_model": openai_model,
                "email_imap_server": imap_server,
                "email_address": email_address,
                "http_proxy": http_proxy
            }
            
            # Only update keys if user provided new inputs (different from status placeholder)
            if gemini_key and gemini_key != "🟢 KEY_ALREADY_CONFIGURED":
                update_data["gemini_api_key"] = gemini_key
            if openai_key and openai_key != "🟢 KEY_ALREADY_CONFIGURED":
                update_data["openai_api_key"] = openai_key
            if email_pwd and email_pwd != "🟢 PASSWORD_ALREADY_CONFIGURED":
                update_data["email_password"] = email_pwd
                
            save_res = api_request("POST", "/settings", json_data=update_data)
            if save_res:
                st.success("配置更新成功！环境变量已成功保存。")
                st.rerun()

# Handle dynamic page switching from email list button
if "selected_menu" in st.session_state:
    target_menu = st.session_state.pop("selected_menu")
    # Streamlit doesn't support dynamically changing radio select directly easily,
    # but we can advise user, or since session_state keys are matched to radio buttons, we handle reload.
    st.info(f"请使用左侧菜单栏切换到 [{target_menu}] 选项卡。")
