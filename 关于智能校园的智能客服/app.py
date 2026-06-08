import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import re
from difflib import get_close_matches

# ---------- 页面配置 ----------
st.set_page_config(page_title="智能校园客服", page_icon="💬", layout="wide")

st.title("💬 智能校园客服系统")
st.markdown("> 自然语言处理 + 校园知识图谱 | 支持课程/设施/政策问答 | 动态知识子图")

# ---------- 知识图谱数据 ----------
# 课程节点
courses = {
    "高等数学": {"type": "课程", "credit": 5, "teacher": "王教授", "prereq": []},
    "线性代数": {"type": "课程", "credit": 3, "teacher": "李教授", "prereq": []},
    "离散数学": {"type": "课程", "credit": 4, "teacher": "赵教授", "prereq": ["高等数学"]},
    "数据结构": {"type": "课程", "credit": 4, "teacher": "张教授", "prereq": ["离散数学"]},
    "机器学习": {"type": "课程", "credit": 4, "teacher": "孙教授", "prereq": ["线性代数", "高等数学"]},
}
# 设施节点
facilities = {
    "图书馆": {"type": "设施", "hours": "8:00-22:00", "location": "图书馆楼", "service": "借书、自习"},
    "第一食堂": {"type": "设施", "hours": "6:30-20:00", "location": "生活区", "service": "餐饮"},
    "计算中心": {"type": "设施", "hours": "8:30-21:30", "location": "信息楼", "service": "上机、打印"},
}
# 政策节点
policies = {
    "奖学金": {"type": "政策", "condition": "绩点≥3.5，无挂科", "amount": "一等5000元，二等3000元"},
    "转专业": {"type": "政策", "condition": "第一学年成绩前30%", "process": "申请→面试→审批"},
}

# 合并所有节点
all_nodes = {**courses, **facilities, **policies}

# 构建图谱（用于可视化）
@st.cache_resource
def build_graph():
    G = nx.Graph()
    for name, info in all_nodes.items():
        G.add_node(name, type=info["type"])
    # 添加关系边
    # 课程-教师关系（虚拟教师节点，为了演示，直接连接课程与教师名）
    teachers = set()
    for course, info in courses.items():
        teacher = info["teacher"]
        teachers.add(teacher)
        G.add_node(teacher, type="教师")
        G.add_edge(course, teacher, relation="授课")
    # 先修关系
    for course, info in courses.items():
        for prereq in info["prereq"]:
            G.add_edge(prereq, course, relation="先修")
    # 设施-位置关系
    for fac, info in facilities.items():
        loc = info["location"]
        G.add_node(loc, type="位置")
        G.add_edge(fac, loc, relation="位于")
    return G

G = build_graph()

# ---------- NLP 意图识别与实体提取 ----------
def extract_intent_and_entities(question):
    """返回 (intent, entities)   intent: course, facility, policy, unknown"""
    q = question.lower()
    # 意图识别
    if any(word in q for word in ["课程", "学分", "老师", "教授", "先修", "前置"]):
        intent = "course"
    elif any(word in q for word in ["图书馆", "食堂", "计算中心", "几点", "开放时间", "在哪", "位置"]):
        intent = "facility"
    elif any(word in q for word in ["奖学金", "转专业", "政策", "条件", "申请"]):
        intent = "policy"
    else:
        intent = "unknown"
    
    # 实体提取（精确匹配 + 模糊匹配）
    candidates = list(all_nodes.keys())
    entities = []
    for name in candidates:
        if name in question:
            entities.append(name)
    if not entities:
        # 尝试模糊匹配
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', question)
        for w in words:
            match = get_close_matches(w, candidates, n=1, cutoff=0.6)
            if match:
                entities.append(match[0])
    return intent, list(set(entities))

# ---------- 推理回答 ----------
def answer_question(question):
    intent, entities = extract_intent_and_entities(question)
    
    # 课程查询
    if intent == "course":
        for course in entities:
            if course in courses:
                info = courses[course]
                prereq_str = "、".join(info["prereq"]) if info["prereq"] else "无"
                return f"📖 **{course}**：{info['credit']}学分，授课教师：{info['teacher']}，先修课程：{prereq_str}。"
        # 如果没有明确实体，尝试查找常见课程问题
        if "学分" in question:
            for course, info in courses.items():
                if course in question:
                    return f"《{course}》学分为 {info['credit']}。"
        if "老师" in question or "教授" in question:
            for course, info in courses.items():
                if course in question:
                    return f"《{course}》由 {info['teacher']} 讲授。"
        if "先修" in question:
            for course, info in courses.items():
                if course in question:
                    prereq_str = "、".join(info["prereq"]) if info["prereq"] else "无"
                    return f"《{course}》的先修课程：{prereq_str}。"
        return "未找到相关课程信息，请尝试输入完整课程名（如高等数学）。"
    
    # 设施查询
    elif intent == "facility":
        for fac in entities:
            if fac in facilities:
                info = facilities[fac]
                return f"🏢 **{fac}**：开放时间 {info['hours']}，位于 {info['location']}，提供 {info['service']}。"
        # 常见问题：图书馆几点开门？
        if "图书馆" in question:
            return "图书馆开放时间：8:00-22:00，位于图书馆楼。"
        if "食堂" in question:
            return "第一食堂开放时间：6:30-20:00，位于生活区。"
        return "未找到相关设施信息，可询问图书馆、食堂、计算中心等。"
    
    # 政策查询
    elif intent == "policy":
        for pol in entities:
            if pol in policies:
                info = policies[pol]
                if "condition" in info:
                    return f"📋 **{pol}**：条件：{info['condition']}。奖励/金额：{info.get('amount', '详见规定')}。"
                else:
                    return f"📋 **{pol}**：{info.get('process', '请咨询教务处')}"
        if "奖学金" in question:
            return "奖学金：一等5000元，二等3000元，要求绩点≥3.5且无挂科。"
        if "转专业" in question:
            return "转专业条件：第一学年成绩前30%，流程：申请→面试→审批。"
        return "未找到相关政策信息，可询问奖学金、转专业等。"
    
    else:
        return "💡 您可以问：高等数学的学分是多少？图书馆几点开门？奖学金有什么条件？"

# ---------- 动态子图可视化 ----------
def get_subgraph_by_entities(entities, G, hops=1):
    """根据实体列表提取子图（包含这些实体及其hops跳邻居）"""
    if not entities:
        return G  # 返回全图
    nodes_to_keep = set(entities)
    for ent in entities:
        if ent in G.nodes:
            neighbors = list(nx.single_source_shortest_path_length(G, ent, cutoff=hops).keys())
            nodes_to_keep.update(neighbors)
    return G.subgraph(nodes_to_keep).copy()

def draw_dynamic_graph(question, G):
    intent, entities = extract_intent_and_entities(question)
    subG = get_subgraph_by_entities(entities, G, hops=1)
    fig, ax = plt.subplots(figsize=(9, 6))
    if subG.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "无相关实体", ha='center', va='center')
        ax.axis('off')
        return fig
    pos = nx.spring_layout(subG, seed=42, k=2.0)
    # 节点颜色按类型
    node_colors = []
    for node in subG.nodes():
        if node in entities:
            node_colors.append("#FFD700")  # 高亮黄色
        elif node in all_nodes:
            typ = all_nodes[node]["type"]
            if typ == "课程":
                node_colors.append("#FF6B6B")
            elif typ == "设施":
                node_colors.append("#4D9DE0")
            elif typ == "政策":
                node_colors.append("#90BE6D")
            else:
                node_colors.append("#AAAAAA")
        else:
            # 教师、位置等辅助节点
            node_colors.append("#C0C0C0")
    nx.draw_networkx_nodes(subG, pos, ax=ax, node_color=node_colors, node_size=1000, alpha=0.9)
    # 显示节点名称（白色背景）
    labels = {node: node for node in subG.nodes}
    nx.draw_networkx_labels(subG, pos, labels=labels, ax=ax, font_size=9, font_weight="bold",
                            bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=1))
    # 绘制边
    if subG.edges:
        nx.draw_networkx_edges(subG, pos, ax=ax, edge_color="gray", width=1.5, alpha=0.6)
    ax.set_title("智能客服知识图谱（动态子图）", fontsize=12)
    ax.axis('off')
    plt.tight_layout()
    return fig

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📊 知识库统计")
    st.metric("课程", len(courses))
    st.metric("设施", len(facilities))
    st.metric("政策", len(policies))
    st.divider()
    st.subheader("📌 实体列表")
    with st.expander("课程"):
        st.write("、".join(courses.keys()))
    with st.expander("设施"):
        st.write("、".join(facilities.keys()))
    with st.expander("政策"):
        st.write("、".join(policies.keys()))
    st.caption("💬 智能客服支持自然语言问答，右侧图谱动态变化。")

# ---------- 主界面 ----------
col_left, col_right = st.columns([1.5, 1])

with col_left:
    st.subheader("✨ 智能问答")
    # 示例问题
    ex_questions = [
        "高等数学的学分是多少？", "数据结构由哪位老师教？", "图书馆几点开门？",
        "奖学金有什么条件？", "转专业怎么申请？", "离散数学的先修课程是什么？"
    ]
    for i in range(0, len(ex_questions), 2):
        cols = st.columns(2)
        for j in range(2):
            if i+j < len(ex_questions):
                if cols[j].button(ex_questions[i+j], key=f"ex_{i+j}", use_container_width=True):
                    st.session_state["question"] = ex_questions[i+j]
                    st.rerun()
    st.divider()
    
    question = st.text_input("💬 输入你的问题：", value=st.session_state.get("question", ""), key="question_input")
    if st.button("🔍 开始推理", type="primary", use_container_width=True):
        if question:
            with st.spinner("思考中..."):
                answer = answer_question(question)
            st.success("✅ 回答")
            st.info(answer)
            # 展示推理过程（NLP步骤）
            with st.expander("📐 推理过程"):
                intent, entities = extract_intent_and_entities(question)
                st.write(f"**意图识别**：{intent}")
                st.write(f"**提取实体**：{', '.join(entities) if entities else '无'}")
                st.write("**知识图谱匹配** → 检索属性 → 生成回答")
            # 保存问题用于右侧图谱
            st.session_state["last_question"] = question
        else:
            st.warning("请输入问题")

with col_right:
    st.subheader("🗺️ 动态知识图谱")
    last_q = st.session_state.get("last_question", "")
    if last_q:
        fig = draw_dynamic_graph(last_q, G)
        st.pyplot(fig)
    else:
        # 默认显示一个简单的全图（限于节点过多时可能拥挤，但可接受）
        fig = draw_dynamic_graph("图书馆", G)  # 默认以图书馆为种子
        st.pyplot(fig)
    st.caption("黄色节点：问题涉及实体 | 连线表示关系（授课、先修、位于等）")

st.divider()
st.caption("💬 智能校园客服 | 基于规则NLP + 知识图谱 | 支持课程/设施/政策问答")