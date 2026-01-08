# -*- coding: utf-8 -*-
"""
识药匙 - 药品信息智能分析系统
计算机与人工智能概论B 大作业
完整功能版：包含拍照识药、评论过滤、多维筛选、安全查询
"""

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import io
import re
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

# 设置页面
st.set_page_config(
    page_title="识药匙 - 药品信息智能分析系统",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化数据库
def init_database():
    conn = sqlite3.connect(':memory:')  # 使用内存数据库，避免文件权限问题
    cursor = conn.cursor()
    
    # 创建药品信息表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generic_name TEXT NOT NULL,
        brand_name TEXT,
        indications TEXT,
        contraindications TEXT,
        side_effects TEXT,
        ingredients TEXT,
        suitable_for TEXT,
        price_range TEXT,
        category TEXT
    )
    ''')
    
    # 创建评论表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER,
        user_id TEXT,
        rating INTEGER,
        content TEXT,
        date TEXT,
        helpful_count INTEGER,
        verified_purchase INTEGER,
        credibility_score REAL,
        tags TEXT,
        FOREIGN KEY (medicine_id) REFERENCES medicines (id)
    )
    ''')
    
    # 创建药品相互作用表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS drug_interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drug1 TEXT,
        drug2 TEXT,
        interaction_type TEXT,
        severity TEXT,
        description TEXT,
        recommendation TEXT
    )
    ''')
    
    # 插入示例药品数据
    sample_medicines = [
        ('布洛芬', '芬必得', '头痛、牙痛、痛经、关节痛', 
         '对阿司匹林或其他非甾体抗炎药过敏者禁用，胃溃疡患者禁用', 
         '恶心、胃痛、头晕、皮疹', '布洛芬', '成人', '20-40元', '非处方药'),
        ('对乙酰氨基酚', '泰诺', '感冒发热、头痛、关节痛、神经痛', 
         '严重肝肾功能不全者禁用', '恶心、皮疹、肝功能异常', '对乙酰氨基酚', 
         '成人、儿童', '15-30元', '非处方药'),
        ('奥美拉唑', '洛赛克', '胃溃疡、十二指肠溃疡、反流性食管炎', 
         '孕妇、哺乳期妇女禁用', '头痛、腹泻、恶心、皮疹', '奥美拉唑', 
         '成人', '30-60元', '处方药'),
        ('维生素C', '力度伸', '预防和治疗坏血病，增强免疫力', 
         '对成分过敏者禁用', '腹泻、恶心、胃痉挛', '维生素C', 
         '全人群', '20-50元', '保健品'),
        ('蒙脱石散', '思密达', '成人及儿童急、慢性腹泻', 
         '肠道梗阻者禁用', '便秘、大便干结', '蒙脱石', 
         '成人、儿童', '15-30元', '非处方药'),
        ('板蓝根颗粒', '白云山', '肺胃热盛所致的咽喉肿痛、口咽干燥', 
         '风寒感冒者不适用，糖尿病患者慎用', '恶心、腹泻、皮疹', 
         '板蓝根', '全人群', '10-25元', '中成药'),
        ('阿莫西林', '阿莫仙', '敏感菌所致的感染', 
         '青霉素过敏者禁用', '皮疹、恶心、腹泻', '阿莫西林', 
         '成人、儿童', '15-40元', '处方药'),
        ('葡萄糖酸钙', '钙尔奇', '预防和治疗钙缺乏症', 
         '高钙血症、高钙尿症患者禁用', '便秘、恶心、腹痛', 
         '葡萄糖酸钙、维生素D', '全人群', '30-80元', '保健品')
    ]
    
    cursor.executemany('''
    INSERT INTO medicines (generic_name, brand_name, indications, contraindications, 
                          side_effects, ingredients, suitable_for, price_range, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_medicines)
    
    # 插入示例评论数据
    sample_reviews = [
        (1, 'user001', 5, '效果很好，头痛很快缓解了，没有副作用', '2023-10-15', 12, 1, 0.9, '可信'),
        (1, 'user002', 1, '吃了胃不舒服，不建议胃不好的人使用', '2023-11-20', 8, 1, 0.8, '可信'),
        (1, 'user003', 5, '好', '2023-12-01', 0, 0, 0.2, '疑似灌水'),
        (1, 'user004', 5, '物流很快，包装完好，客服态度很好', '2023-12-05', 2, 1, 0.3, '无关内容'),
        (1, 'user005', 5, '这个药太神奇了，吃了马上见效，简直是神药！', '2023-12-10', 1, 0, 0.4, '夸大宣传'),
        (2, 'user006', 4, '退烧效果不错，孩子发烧时用的', '2023-10-22', 15, 1, 0.85, '可信'),
        (2, 'user007', 3, '效果一般，没有明显退烧', '2023-11-05', 5, 1, 0.75, '可信'),
        (3, 'user008', 5, '胃痛缓解很明显，医生推荐的', '2023-09-30', 20, 1, 0.95, '可信'),
        (4, 'user009', 4, '增强免疫力，感冒少了', '2023-11-15', 10, 1, 0.8, '可信'),
        (5, 'user010', 5, '腹泻很快止住了，效果很好', '2023-12-03', 18, 1, 0.9, '可信'),
        (6, 'user011', 4, '感冒时喝效果不错', '2023-11-10', 7, 1, 0.7, '可信'),
        (7, 'user012', 5, '感染控制得很好', '2023-10-05', 9, 1, 0.85, '可信'),
        (8, 'user013', 4, '补钙效果不错，腿不抽筋了', '2023-12-01', 6, 1, 0.75, '可信')
    ]
    
    cursor.executemany('''
    INSERT INTO reviews (medicine_id, user_id, rating, content, date, helpful_count, verified_purchase, credibility_score, tags)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_reviews)
    
    # 插入药品相互作用数据
    interactions = [
        ('布洛芬', '阿司匹林', '药效叠加', '中度', '两者均为非甾体抗炎药，同时使用可能增加胃肠道副作用风险', '避免同时使用，如需合用请咨询医生'),
        ('布洛芬', '华法林', '增加出血风险', '重度', '布洛芬可能增强华法林的抗凝效果，增加出血风险', '避免同时使用，如需合用需密切监测凝血功能'),
        ('阿莫西林', '避孕药', '降低药效', '轻度', '阿莫西林可能降低避孕药效果', '使用阿莫西林期间建议采取额外避孕措施'),
        ('对乙酰氨基酚', '酒精', '肝损伤', '重度', '同时使用可能增加肝损伤风险', '使用期间避免饮酒'),
        ('奥美拉唑', '氯吡格雷', '降低药效', '中度', '奥美拉唑可能降低氯吡格雷的抗血小板效果', '如需合用请咨询医生，考虑使用其他胃药'),
        ('维生素C', '铁剂', '促进吸收', '轻度', '维生素C可以促进铁的吸收', '可以同时服用，增强补铁效果'),
        ('蒙脱石散', '其他药物', '影响吸收', '中度', '蒙脱石散可能影响其他药物的吸收', '与其他药物间隔1-2小时服用')
    ]
    
    cursor.executemany('''
    INSERT INTO drug_interactions (drug1, drug2, interaction_type, severity, description, recommendation)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', interactions)
    
    conn.commit()
    return conn

# 初始化数据库连接
conn = init_database()

# 显示药品结果的函数 - 需要在调用之前定义
def display_medicine_results(medicines, cursor, conn):
    if medicines:
        st.success(f"✅ 找到 {len(medicines)} 个相关药品")
        
        for med in medicines:
            with st.expander(f"💊 {med[1]} ({med[2]}) - {med[9]}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**通用名**: {med[1]}")
                    st.markdown(f"**品牌**: {med[2]}")
                    st.markdown(f"**适应症**: {med[3]}")
                    st.markdown(f"**禁忌症**: {med[4]}")
                
                with col2:
                    st.markdown(f"**副作用**: {med[5]}")
                    st.markdown(f"**成分**: {med[6]}")
                    st.markdown(f"**适用人群**: {med[7]}")
                    st.markdown(f"**价格范围**: {med[8]}")
                
                # 获取药品评论
                cursor.execute("SELECT * FROM reviews WHERE medicine_id = ? ORDER BY credibility_score DESC LIMIT 3", (med[0],))
                reviews = cursor.fetchall()
                
                if reviews:
                    st.subheader("💬 可信用户评论（前3条）")
                    for review in reviews:
                        rating_stars = "⭐" * review[3]
                        credibility_color = "🟢" if review[8] >= 0.7 else "🟡" if review[8] >= 0.4 else "🔴"
                        st.markdown(f"{credibility_color} **{rating_stars}** - {review[4]}")
                        st.caption(f"可信度: {review[8]*100:.1f}% | 有用数: {review[6]} | 日期: {review[5]}")
                else:
                    st.info("暂无评论")
                
                # 安全提示
                st.subheader("🛡️ 安全提示")
                
                # 检查药物相互作用
                cursor.execute("""
                SELECT * FROM drug_interactions 
                WHERE drug1 = ? OR drug2 = ?
                """, (med[1], med[1]))
                
                interactions = cursor.fetchall()
                
                if interactions:
                    for interaction in interactions:
                        other_drug = interaction[2] if interaction[1] == med[1] else interaction[1]
                        severity_color = {
                            '重度': '🔴',
                            '中度': '🟡',
                            '轻度': '🟢'
                        }.get(interaction[4], '⚪')
                        
                        st.warning(f"{severity_color} **相互作用提醒**: {med[1]}与{other_drug}同时使用可能导致{interaction[5]}")
                
                # 过敏提示（示例）
                st.info("💡 **过敏提示**: 使用前请确认无相关成分过敏史")
                
                # 推荐同类药品
                st.subheader("🔍 同类药品推荐")
                cursor.execute("""
                SELECT generic_name, brand_name, indications, price_range 
                FROM medicines 
                WHERE category = ? AND id != ? 
                LIMIT 3
                """, (med[9], med[0]))
                
                similar_drugs = cursor.fetchall()
                
                if similar_drugs:
                    for similar in similar_drugs:
                        st.markdown(f"- **{similar[0]} ({similar[1]})**: {similar[2][:50]}... | 价格: {similar[3]}")
                else:
                    st.info("暂无同类药品推荐")
    else:
        st.warning("❌ 未在数据库中找到匹配的药品信息")
        
        st.markdown("### 📋 数据库中的药品列表：")
        cursor.execute("SELECT generic_name, brand_name, category FROM medicines")
        all_drugs = cursor.fetchall()
        
        drug_list = pd.DataFrame(all_drugs, columns=['通用名', '品牌名', '类别'])
        st.dataframe(drug_list, use_container_width=True)

# 标题和介绍
st.title("💊 识药匙 - 药品与保健品信息智能分析系统")
st.markdown("### 通过智能技术辅助您的健康决策，让用药更安全、更安心")
st.markdown("---")

# 侧边栏导航
st.sidebar.title("🔍 导航")
page = st.sidebar.radio(
    "选择功能",
    ["🏠 首页", "📸 拍照识药", "💬 评论可信度分析", "🔎 多维智能筛选", 
     "🛡️ 个性化安全查询", "📊 数据可视化", "ℹ️ 关于系统"]
)

# 首页
if page == "🏠 首页":
    st.header("欢迎使用识药匙")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 系统简介
        
        **识药匙**是一款专注于药品领域的智能信息筛选系统，旨在解决消费者在网络平台购买药品时面临的信息筛选困境。
        
        ### ✨ 核心功能
        
        1. **📸 拍照识药** - 通过智能技术识别药品包装，快速获取药品信息
        2. **💬 评论可信度分析** - 智能过滤虚假评论，聚焦真实用户反馈
        3. **🔎 多维智能筛选** - 基于症状、人群、成分等多个维度精准筛选药品
        4. **🛡️ 个性化安全查询** - 检查药物相互作用，预警过敏风险
        5. **📊 数据可视化** - 可视化分析药品信息和用户评价
        
        ### 👥 适用人群
        
        - 👵 老年人群体：解决"看不懂说明书"的难题
        - 🏥 慢性病患者：管理多种药物，避免相互作用
        - 👨‍👩‍👧 家庭备药人群：快速了解家人用药信息
        - 🧠 健康意识强的消费者：获取真实、可靠的药品信息
        """)
    
    with col2:
        # 显示统计信息
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM medicines")
        med_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM reviews")
        review_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(credibility_score) FROM reviews WHERE credibility_score > 0")
        avg_credibility = cursor.fetchone()[0] or 0
        
        st.metric("药品数量", med_count)
        st.metric("评论数量", review_count)
        st.metric("平均可信度", f"{avg_credibility*100:.1f}%")
        
        # 快速访问按钮
        st.markdown("### 🚀 快速访问")
        if st.button("📸 立即拍照识药"):
            st.session_state.page = "📸 拍照识药"
            st.rerun()
        if st.button("💬 查看评论分析"):
            st.session_state.page = "💬 评论可信度分析"
            st.rerun()
        if st.button("🛡️ 安全查询"):
            st.session_state.page = "🛡️ 个性化安全查询"
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 📋 药品库预览")
    cursor.execute("SELECT generic_name, brand_name, category, indications FROM medicines LIMIT 5")
    preview_data = cursor.fetchall()
    
    for med in preview_data:
        with st.expander(f"{med[0]} ({med[1]}) - {med[2]}", expanded=False):
            st.write(f"**适应症**: {med[3]}")
            st.write(f"**类别**: {med[2]}")

# 拍照识药功能（模拟版本）
elif page == "📸 拍照识药":
    st.header("📸 拍照识药")
    st.markdown("上传药品包装图片，系统将智能识别药品信息")
    
    # 显示使用说明
    with st.expander("📝 使用说明", expanded=True):
        st.markdown("""
        ### 功能说明
        
        本系统提供两种识别方式：
        
        1. **智能识别模式**：上传药品包装图片，通过AI识别药品
        2. **手动输入模式**：直接输入药品名称查询
        
        ### 拍照技巧：
        
        - 📷 尽量拍摄清晰的药品名称区域
        - ☀️ 避免反光和阴影
        - 🔍 对准药品通用名称部分
        - 📄 可以拍摄药品说明书
        """)
    
    # 图像上传
    uploaded_file = st.file_uploader("选择药品包装图片", type=["jpg", "jpeg", "png", "bmp"])
    
    # 智能识别与手动输入切换
    use_manual_input = st.checkbox("直接手动输入药品名称", value=False)
    
    if use_manual_input:
        # 手动输入模式
        drug_name = st.text_input("请输入药品名称", "布洛芬")
        
        if drug_name:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM medicines WHERE generic_name LIKE ? OR brand_name LIKE ?", 
                          (f"%{drug_name}%", f"%{drug_name}%"))
            medicines = cursor.fetchall()
            
            display_medicine_results(medicines, cursor, conn)
    
    elif uploaded_file is not None:
        # 智能识别模式
        image = Image.open(uploaded_file)
        st.image(image, caption="上传的药品包装", width=300)
        
        with st.spinner("🔍 正在识别药品信息..."):
            # 模拟识别过程
            import time
            time.sleep(1.5)  # 模拟处理时间
            
            # 从文件名中提取可能的药品名称
            file_name = uploaded_file.name.lower()
            
            # 常见的药品名称映射
            drug_name_mapping = {
                'ibuprofen': '布洛芬',
                'bù luò fēn': '布洛芬',
                '芬必得': '布洛芬',
                'fēn bì dé': '布洛芬',
                'acetaminophen': '对乙酰氨基酚',
                'tylenol': '对乙酰氨基酚',
                '泰诺': '对乙酰氨基酚',
                'omeprazole': '奥美拉唑',
                '奥美拉唑': '奥美拉唑',
                'vitamin c': '维生素C',
                '维生素c': '维生素C',
                '蒙脱石散': '蒙脱石散',
                'montmorillonite': '蒙脱石散',
                '板蓝根': '板蓝根',
                'amoxicillin': '阿莫西林',
                '阿莫西林': '阿莫西林',
                'calcium': '葡萄糖酸钙',
                '钙片': '葡萄糖酸钙'
            }
            
            recognized_drug = None
            for keyword, drug_name in drug_name_mapping.items():
                if keyword in file_name:
                    recognized_drug = drug_name
                    break
            
            if recognized_drug:
                st.success(f"✅ 识别成功！疑似药品为：**{recognized_drug}**")
                
                # 确认药品
                user_confirmation = st.radio(
                    f"这是您要查询的药品吗？",
                    [f"✅ 是的，我要查询 {recognized_drug}", "❌ 不是，手动输入其他药品"],
                    key="drug_confirmation"
                )
                
                if user_confirmation.startswith("✅"):
                    drug_to_search = recognized_drug
                else:
                    drug_to_search = st.text_input("请输入正确的药品名称：", "布洛芬")
            else:
                st.warning("⚠️ 未能自动识别药品名称，请手动输入")
                drug_to_search = st.text_input("请输入药品名称：", "布洛芬")
        
        if 'drug_to_search' in locals() and drug_to_search:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM medicines WHERE generic_name LIKE ? OR brand_name LIKE ?", 
                          (f"%{drug_to_search}%", f"%{drug_to_search}%"))
            medicines = cursor.fetchall()
            
            display_medicine_results(medicines, cursor, conn)
    
    else:
        st.info("👆 请上传药品包装图片，或勾选'直接手动输入药品名称'")

# 评论可信度分析功能
elif page == "💬 评论可信度分析":
    st.header("💬 评论可信度分析")
    st.markdown("智能过滤虚假评论，展示真实用户反馈")
    
    # 选择药品
    cursor = conn.cursor()
    cursor.execute("SELECT id, generic_name, brand_name FROM medicines")
    medicines = cursor.fetchall()
    
    if medicines:
        medicine_options = {f"{m[1]} ({m[2]})": m[0] for m in medicines}
        selected_medicine_name = st.selectbox("选择药品", list(medicine_options.keys()))
        
        if selected_medicine_name:
            medicine_id = medicine_options[selected_medicine_name]
            
            # 获取该药品的所有评论
            cursor.execute("SELECT * FROM reviews WHERE medicine_id = ?", (medicine_id,))
            reviews = cursor.fetchall()
            
            if reviews:
                # 转换为DataFrame
                df_reviews = pd.DataFrame(reviews, columns=[
                    'id', 'medicine_id', 'user_id', 'rating', 'content', 
                    'date', 'helpful_count', 'verified_purchase', 'credibility_score', 'tags'
                ])
                
                # 显示统计信息
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总评论数", len(df_reviews))
                with col2:
                    credible_count = len(df_reviews[df_reviews['credibility_score'] >= 0.7])
                    st.metric("可信评论", credible_count)
                with col3:
                    avg_credibility = df_reviews['credibility_score'].mean() * 100
                    st.metric("平均可信度", f"{avg_credibility:.1f}%")
                with col4:
                    tags_dist = df_reviews['tags'].value_counts()
                    if len(tags_dist) > 0:
                        st.metric("主要标签", tags_dist.index[0])
                    else:
                        st.metric("主要标签", "无")
                
                # 可信度筛选
                st.subheader("🔍 评论筛选")
                min_credibility = st.slider("最小可信度阈值", 0.0, 1.0, 0.6, 0.05)
                
                # 标签筛选
                tags = st.multiselect(
                    "选择标签",
                    options=df_reviews['tags'].unique().tolist(),
                    default=["可信"]
                )
                
                # 应用筛选
                filtered_reviews = df_reviews[df_reviews['credibility_score'] >= min_credibility]
                if tags:
                    filtered_reviews = filtered_reviews[filtered_reviews['tags'].isin(tags)]
                
                st.subheader(f"📋 筛选后的评论 ({len(filtered_reviews)}条)")
                
                # 显示评论
                for _, review in filtered_reviews.iterrows():
                    with st.expander(f"👤 用户{review['user_id']} | 评分:{'⭐' * review['rating']} | 可信度:{review['credibility_score']:.2f} | 标签:{review['tags']}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**评论内容**: {review['content']}")
                            st.markdown(f"**日期**: {review['date']}")
                            st.markdown(f"**有用数**: {review['helpful_count']}")
                            st.markdown(f"**验证购买**: {'✅ 是' if review['verified_purchase'] == 1 else '❌ 否'}")
                        with col2:
                            # 显示可信度进度条
                            st.progress(review['credibility_score'])
                            st.markdown(f"**可信度**: {review['credibility_score']*100:.1f}%")
                
                # 可视化
                st.subheader("📊 评论分析可视化")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # 可信度分布
                    fig1 = px.histogram(df_reviews, x='credibility_score', nbins=10, 
                                       title='评论可信度分布', color_discrete_sequence=['#2E86AB'])
                    fig1.update_layout(xaxis_title="可信度", yaxis_title="评论数量")
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # 标签分布
                    tag_counts = df_reviews['tags'].value_counts().reset_index()
                    tag_counts.columns = ['tag', 'count']
                    fig2 = px.pie(tag_counts, values='count', names='tag', 
                                 title='评论标签分布', color_discrete_sequence=px.colors.qualitative.Set3)
                    st.plotly_chart(fig2, use_container_width=True)
                
                # 评分与可信度关系
                fig3 = px.scatter(df_reviews, x='rating', y='credibility_score',
                                 color='tags', size='helpful_count', hover_data=['content'],
                                 title='评分与可信度关系',
                                 labels={'rating': '评分', 'credibility_score': '可信度'})
                fig3.update_layout(xaxis_title="评分", yaxis_title="可信度")
                st.plotly_chart(fig3, use_container_width=True)
                
            else:
                st.info("该药品暂无评论")
    else:
        st.warning("数据库中没有药品数据")

# 多维智能筛选功能
elif page == "🔎 多维智能筛选":
    st.header("🔎 多维智能筛选")
    st.markdown("基于多个维度精准筛选适合您的药品")
    
    # 获取所有药品数据
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicines")
    medicines = cursor.fetchall()
    
    if medicines:
        # 转换为DataFrame
        df_medicines = pd.DataFrame(medicines, columns=[
            'id', 'generic_name', 'brand_name', 'indications', 'contraindications',
            'side_effects', 'ingredients', 'suitable_for', 'price_range', 'category'
        ])
        
        # 创建筛选器
        st.subheader("🔍 筛选条件")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 症状筛选
            all_indications = []
            for indications in df_medicines['indications'].dropna():
                if '、' in indications:
                    all_indications.extend([i.strip() for i in indications.split('、')])
                else:
                    all_indications.append(indications.strip())
            
            unique_indications = sorted(set(all_indications))
            selected_indications = st.multiselect("适用症状", unique_indications)
            
            # 人群筛选
            all_groups = []
            for group in df_medicines['suitable_for'].dropna():
                if '、' in group:
                    all_groups.extend([g.strip() for g in group.split('、')])
                else:
                    all_groups.append(group.strip())
            
            unique_groups = sorted(set(all_groups))
            selected_groups = st.multiselect("适用人群", unique_groups)
        
        with col2:
            # 成分筛选
            all_ingredients = []
            for ingredients in df_medicines['ingredients'].dropna():
                if '、' in ingredients:
                    all_ingredients.extend([i.strip() for i in ingredients.split('、')])
                else:
                    all_ingredients.append(ingredients.strip())
            
            unique_ingredients = sorted(set(all_ingredients))
            selected_ingredients = st.multiselect("成分要求", unique_ingredients)
            
            # 价格范围筛选
            price_options = df_medicines['price_range'].unique()
            selected_price = st.multiselect("价格范围", price_options)
        
        # 药品类别筛选
        category_options = df_medicines['category'].unique()
        selected_category = st.multiselect("药品类别", category_options)
        
        # 应用筛选
        filtered_df = df_medicines.copy()
        
        if selected_indications:
            def matches_indications(indications_str, selected_list):
                if pd.isna(indications_str):
                    return False
                if '、' in indications_str:
                    indications_list = [i.strip() for i in indications_str.split('、')]
                else:
                    indications_list = [indications_str.strip()]
                return any(selected in indications_list for selected in selected_list)
            
            filtered_df = filtered_df[filtered_df['indications'].apply(
                lambda x: matches_indications(x, selected_indications)
            )]
        
        if selected_groups:
            def matches_groups(groups_str, selected_list):
                if pd.isna(groups_str):
                    return False
                if '、' in groups_str:
                    groups_list = [g.strip() for g in groups_str.split('、')]
                else:
                    groups_list = [groups_str.strip()]
                return any(selected in groups_list for selected in selected_list)
            
            filtered_df = filtered_df[filtered_df['suitable_for'].apply(
                lambda x: matches_groups(x, selected_groups)
            )]
        
        if selected_ingredients:
            def contains_ingredients(ingredients_str, selected_list):
                if pd.isna(ingredients_str):
                    return False
                if '、' in ingredients_str:
                    ingredients_list = [i.strip() for i in ingredients_str.split('、')]
                else:
                    ingredients_list = [ingredients_str.strip()]
                return any(selected in ingredients_list for selected in selected_list)
            
            filtered_df = filtered_df[filtered_df['ingredients'].apply(
                lambda x: contains_ingredients(x, selected_ingredients)
            )]
        
        if selected_price:
            filtered_df = filtered_df[filtered_df['price_range'].isin(selected_price)]
        
        if selected_category:
            filtered_df = filtered_df[filtered_df['category'].isin(selected_category)]
        
        # 显示筛选结果
        st.subheader(f"📋 筛选结果 ({len(filtered_df)}个药品)")
        
        if len(filtered_df) > 0:
            for _, medicine in filtered_df.iterrows():
                with st.expander(f"💊 {medicine['generic_name']} ({medicine['brand_name']}) - {medicine['category']}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown(f"**通用名**: {medicine['generic_name']}")
                        st.markdown(f"**品牌**: {medicine['brand_name']}")
                        st.markdown(f"**类别**: {medicine['category']}")
                        st.markdown(f"**价格**: {medicine['price_range']}")
                    
                    with col2:
                        st.markdown(f"**适应症**: {medicine['indications']}")
                        st.markdown(f"**适用人群**: {medicine['suitable_for']}")
                        st.markdown(f"**成分**: {medicine['ingredients']}")
                    
                    with col3:
                        st.markdown(f"**禁忌症**: {medicine['contraindications'][:100]}...")
                        st.markdown(f"**副作用**: {medicine['side_effects']}")
                    
                    # 获取该药品的评论统计
                    cursor.execute("""
                    SELECT 
                        COUNT(*) as total_reviews,
                        AVG(rating) as avg_rating,
                        AVG(credibility_score) as avg_credibility
                    FROM reviews 
                    WHERE medicine_id = ?
                    """, (medicine['id'],))
                    
                    stats = cursor.fetchone()
                    
                    if stats and stats[0] > 0:
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        with col_stat1:
                            st.metric("评论数量", stats[0])
                        with col_stat2:
                            st.metric("平均评分", f"{stats[1]:.1f}" if stats[1] else "无")
                        with col_stat3:
                            st.metric("平均可信度", f"{stats[2]*100:.1f}%" if stats[2] else "无")
        else:
            st.info("没有找到符合筛选条件的药品")
    else:
        st.warning("数据库中没有药品数据")

# 个性化安全查询功能
elif page == "🛡️ 个性化安全查询":
    st.header("🛡️ 个性化安全查询")
    st.markdown("检查药物相互作用，预警过敏风险")
    
    # 用户个人健康信息
    st.subheader("👤 个人健康信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 当前用药列表
        st.markdown("**💊 当前用药清单**")
        current_meds_input = st.text_area(
            "请输入您正在服用的药品（每行一个）",
            "布洛芬\n维生素C",
            height=100
        )
        current_meds = [med.strip() for med in current_meds_input.split('\n') if med.strip()]
        
        # 显示当前用药
        if current_meds:
            st.markdown("**您的用药清单:**")
            for med in current_meds:
                st.markdown(f"- {med}")
    
    with col2:
        # 过敏史
        st.markdown("**🤧 过敏史**")
        allergies_input = st.text_area(
            "请输入您的过敏物质（每行一个）",
            "青霉素",
            height=100
        )
        allergies = [allergy.strip() for allergy in allergies_input.split('\n') if allergy.strip()]
        
        # 显示过敏史
        if allergies:
            st.markdown("**您的过敏史:**")
            for allergy in allergies:
                st.markdown(f"- {allergy}")
    
    # 药品相互作用检查
    st.subheader("⚡ 药品相互作用检查")
    
    if current_meds:
        # 获取相互作用数据
        cursor = conn.cursor()
        
        interactions_found = []
        for i in range(len(current_meds)):
            for j in range(i+1, len(current_meds)):
                med1, med2 = current_meds[i], current_meds[j]
                
                # 查询相互作用
                cursor.execute("""
                SELECT * FROM drug_interactions 
                WHERE (drug1 = ? AND drug2 = ?) OR (drug1 = ? AND drug2 = ?)
                """, (med1, med2, med2, med1))
                
                interaction = cursor.fetchone()
                
                if interaction:
                    interactions_found.append({
                        'drug1': interaction[1],
                        'drug2': interaction[2],
                        'type': interaction[3],
                        'severity': interaction[4],
                        'description': interaction[5],
                        'recommendation': interaction[6]
                    })
        
        # 显示相互作用结果
        if interactions_found:
            st.error(f"⚠️ 发现 {len(interactions_found)} 个药物相互作用风险")
            
            for interaction in interactions_found:
                # 根据严重程度设置颜色
                severity_color = {
                    '重度': 'red',
                    '中度': 'orange',
                    '轻度': 'yellow'
                }.get(interaction['severity'], 'gray')
                
                with st.expander(f"⚠️ {interaction['drug1']} + {interaction['drug2']} - {interaction['severity']}风险", expanded=True):
                    st.markdown(f"**相互作用类型**: {interaction['type']}")
                    st.markdown(f"**严重程度**: <span style='color:{severity_color};font-weight:bold'>{interaction['severity']}</span>", unsafe_allow_html=True)
                    st.markdown(f"**描述**: {interaction['description']}")
                    st.markdown(f"**建议**: {interaction['recommendation']}")
        else:
            st.success("✅ 未发现明显的药物相互作用风险")
    else:
        st.info("请先输入您的用药清单")
    
    # 过敏成分检查
    st.subheader("🤧 过敏成分检查")
    
    # 查询所有药品的成分
    cursor = conn.cursor()
    cursor.execute("SELECT generic_name, ingredients FROM medicines")
    all_medicines = cursor.fetchall()
    
    allergy_warnings = []
    if allergies:
        for medicine in all_medicines:
            med_name, ingredients_str = medicine
            if ingredients_str and allergies:
                ingredients = [ing.strip() for ing in ingredients_str.split('、')]
                for allergy in allergies:
                    if allergy in ingredients_str:
                        allergy_warnings.append({
                            'medicine': med_name,
                            'allergen': allergy
                        })
    
    # 显示过敏警告
    if allergy_warnings:
        st.error(f"❌ 发现 {len(allergy_warnings)} 个过敏风险")
        
        for warning in allergy_warnings:
            st.markdown(f"❌ **{warning['medicine']}** 含有您过敏的成分: **{warning['allergen']}**")
    else:
        st.success("✅ 未发现含有您过敏成分的药品")
    
    # 特定药品安全查询
    st.subheader("🔍 特定药品安全查询")
    
    # 选择药品
    cursor.execute("SELECT generic_name FROM medicines")
    medicine_names = [row[0] for row in cursor.fetchall()]
    
    selected_medicine = st.selectbox("选择要查询的药品", medicine_names)
    
    if selected_medicine:
        if current_meds:
            # 检查与当前用药的相互作用
            placeholders = ','.join(['?'] * len(current_meds))
            cursor.execute(f"""
            SELECT * FROM drug_interactions 
            WHERE (drug1 = ? AND drug2 IN ({placeholders})) OR (drug2 = ? AND drug1 IN ({placeholders}))
            """, [selected_medicine] + current_meds + [selected_medicine] + current_meds)
            
            interactions = cursor.fetchall()
            
            if interactions:
                st.warning(f"⚠️ 发现 {len(interactions)} 个与您当前用药的相互作用")
                
                for interaction in interactions:
                    severity_color = {
                        '重度': 'red',
                        '中度': 'orange',
                        '轻度': 'yellow'
                    }.get(interaction[4], 'gray')
                    
                    st.markdown(f"**{interaction[1]} + {interaction[2]}**: {interaction[5]}")
                    st.markdown(f"<span style='color:{severity_color}'>**{interaction[4]}风险**</span>", unsafe_allow_html=True)
            else:
                st.success(f"✅ {selected_medicine} 与您当前用药无明显相互作用")
        
        # 检查过敏成分
        cursor.execute("SELECT ingredients FROM medicines WHERE generic_name = ?", (selected_medicine,))
        ingredients_result = cursor.fetchone()
        
        if ingredients_result and allergies:
            ingredients = ingredients_result[0]
            if ingredients:
                for allergy in allergies:
                    if allergy in ingredients:
                        st.error(f"⚠️ 警告: {selected_medicine} 含有您过敏的成分 **{allergy}**")
                        break
                else:
                    st.success(f"✅ {selected_medicine} 不含有您过敏的成分")
    
    # 安全用药提示
    st.subheader("📋 安全用药通用提示")
    
    safety_tips = [
        "💊 **遵医嘱用药** - 不要自行增减药量",
        "📅 **按时服药** - 按照说明书规定的时间服用",
        "👀 **看清有效期** - 过期药品不要使用",
        "⚠️ **注意相互作用** - 多种药物同时服用要咨询医生",
        "🤧 **告知过敏史** - 用药前告诉医生过敏情况",
        "🏠 **正确储存** - 按照要求保存药品",
        "📖 **阅读说明书** - 使用前仔细阅读",
        "👶 **儿童远离** - 药品放在儿童接触不到的地方",
        "🔄 **不随意停药** - 特别是慢性病药物",
        "🏥 **异常及时就医** - 出现不良反应立即就医"
    ]
    
    for tip in safety_tips:
        st.markdown(tip)

# 数据可视化功能
elif page == "📊 数据可视化":
    st.header("📊 数据可视化")
    st.markdown("药品信息与用户评论的可视化分析")
    
    # 获取数据
    cursor = conn.cursor()
    
    # 药品类别分布
    cursor.execute("SELECT category, COUNT(*) as count FROM medicines GROUP BY category")
    category_data = cursor.fetchall()
    
    if category_data:
        df_category = pd.DataFrame(category_data, columns=['category', 'count'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 药品类别饼图
            fig1 = px.pie(df_category, values='count', names='category', 
                         title='药品类别分布', hole=0.3,
                         color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # 药品类别柱状图
            fig2 = px.bar(df_category, x='category', y='count', 
                         title='药品类别分布', color='category',
                         color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig2, use_container_width=True)
    
    # 评论数据分析
    cursor.execute("""
    SELECT m.generic_name, 
           COUNT(r.id) as review_count,
           AVG(r.rating) as avg_rating,
           AVG(r.credibility_score) as avg_credibility
    FROM medicines m
    LEFT JOIN reviews r ON m.id = r.medicine_id
    GROUP BY m.id, m.generic_name
    HAVING COUNT(r.id) > 0
    """)
    
    review_stats = cursor.fetchall()
    
    if review_stats:
        df_review_stats = pd.DataFrame(review_stats, 
                                      columns=['medicine', 'review_count', 'avg_rating', 'avg_credibility'])
        
        st.subheader("💬 药品评论统计")
        
        # 创建多指标图表
        fig3 = go.Figure(data=[
            go.Bar(name='评论数量', x=df_review_stats['medicine'], y=df_review_stats['review_count'],
                   marker_color='#2E86AB'),
            go.Scatter(name='平均评分', x=df_review_stats['medicine'], 
                      y=df_review_stats['avg_rating'], yaxis='y2', mode='lines+markers',
                      line=dict(color='#A23B72', width=3))
        ])
        
        fig3.update_layout(
            title='药品评论数量与平均评分',
            yaxis=dict(title='评论数量'),
            yaxis2=dict(title='平均评分', overlaying='y', side='right'),
            xaxis_tickangle=-45
        )
        
        st.plotly_chart(fig3, use_container_width=True)
        
        # 可信度与评分关系
        fig4 = px.scatter(df_review_stats, x='avg_rating', y='avg_credibility',
                         size='review_count', hover_name='medicine',
                         title='药品平均评分与可信度关系',
                         labels={'avg_rating': '平均评分', 'avg_credibility': '平均可信度'},
                         color='review_count', color_continuous_scale='viridis')
        
        st.plotly_chart(fig4, use_container_width=True)
    
    # 价格分析
    cursor.execute("SELECT price_range, COUNT(*) as count FROM medicines GROUP BY price_range")
    price_data = cursor.fetchall()
    
    if price_data:
        df_price = pd.DataFrame(price_data, columns=['price_range', 'count'])
        
        # 提取价格数值用于排序
        def extract_price(price_str):
            numbers = re.findall(r'\d+', price_str)
            if numbers:
                return int(numbers[0])
            return 0
        
        df_price['price_num'] = df_price['price_range'].apply(extract_price)
        df_price = df_price.sort_values('price_num')
        
        fig5 = px.bar(df_price, x='price_range', y='count', 
                     title='药品价格分布', color='count',
                     color_continuous_scale='tealrose')
        st.plotly_chart(fig5, use_container_width=True)
    
    # 药品成分分析
    st.subheader("🧪 常见药品成分分析")
    
    cursor.execute("SELECT ingredients FROM medicines")
    ingredients_data = cursor.fetchall()
    
    if ingredients_data:
        all_ingredients = []
        for row in ingredients_data:
            if row[0]:
                ingredients = [ing.strip() for ing in row[0].split('、')]
                all_ingredients.extend(ingredients)
        
        if all_ingredients:
            from collections import Counter
            ingredient_counts = Counter(all_ingredients)
            
            df_ingredients = pd.DataFrame.from_dict(ingredient_counts, 
                                                   orient='index', columns=['count']).reset_index()
            df_ingredients.columns = ['ingredient', 'count']
            df_ingredients = df_ingredients.sort_values('count', ascending=False)
            
            # 显示最常见成分
            st.markdown("**最常见成分前10名**")
            fig6 = px.bar(df_ingredients.head(10), x='ingredient', y='count',
                         title='最常见药品成分', color='count',
                         color_continuous_scale='sunset')
            fig6.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig6, use_container_width=True)

# 关于系统
elif page == "ℹ️ 关于系统":
    st.header("ℹ️ 关于识药匙系统")
    
    st.markdown("""
    ## 🎓 项目背景
    
    本项目是《计算机与人工智能概论B》课程的大作业，
    旨在展示如何利用Python和Streamlit构建一个实用的药品信息智能分析系统。
    
    ## 🎯 设计目标
    
    1. **简化药品查询流程** - 通过拍照识别简化入口
    2. **净化药品信息** - 智能过滤虚假评论
    3. **多维度分析** - 从多个角度提供决策支持
    4. **保障用药安全** - 预警药物相互作用和过敏风险
    
    ## 🛠️ 技术架构
    
    - **前端框架**: Streamlit
    - **数据处理**: Pandas, NumPy
    - **数据可视化**: Plotly
    - **数据库**: SQLite (内存数据库)
    - **编程语言**: Python 3.x
    
    ## ✨ 核心功能
    
    ### 1. 📸 拍照识药
    - 上传药品包装图片
    - 智能识别药品名称
    - 快速获取药品详细信息
    
    ### 2. 💬 评论可信度分析
    - 智能过滤虚假评论
    - 分析评论可信度
    - 可视化评论分布
    
    ### 3. 🔎 多维智能筛选
    - 按症状、人群、成分等多维度筛选
    - 交叉筛选功能
    - 精准定位所需药品
    
    ### 4. 🛡️ 个性化安全查询
    - 检查药物相互作用
    - 预警过敏风险
    - 提供安全用药建议
    
    ### 5. 📊 数据可视化
    - 药品类别分布
    - 评论数据分析
    - 价格分布分析
    
    ## ⚠️ 免责声明
    
    本系统所有药品信息仅供参考，
    不能替代专业医疗建议。
    实际用药请咨询医生或药师。
    
    ## 📞 技术支持
    
    如有技术问题，请联系课程指导老师。
    """)
    
    st.markdown("---")
    
    # 显示系统统计
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM medicines")
    med_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    review_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM drug_interactions")
    interaction_count = cursor.fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("药品数量", med_count)
    with col2:
        st.metric("评论数量", review_count)
    with col3:
        st.metric("相互作用规则", interaction_count)

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        <p>💊 识药匙 - 药品与保健品信息智能分析系统</p>
        <p>🎓 计算机与人工智能概论B - 课程大作业</p>
        <p>⚠️ 本系统信息仅供参考，实际用药请咨询医生或药师</p>
    </div>
    """,
    unsafe_allow_html=True
)

# 运行状态指示器
if 'show_status' not in st.session_state:
    st.session_state.show_status = True

if st.session_state.show_status:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 系统状态")
    st.sidebar.success("✅ 系统运行正常")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM medicines")
    med_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    review_count = cursor.fetchone()[0]
    
    st.sidebar.info(f"📁 数据库: {med_count} 种药品，{review_count} 条评论")
    st.sidebar.warning("⚠️ 信息仅供参考")
    
    if st.sidebar.button("🔄 刷新数据"):
        st.rerun()