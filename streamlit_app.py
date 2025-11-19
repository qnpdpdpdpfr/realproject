import streamlit as st
import pandas as pd
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

st.title("📚 도서 대출 분석 대시보드")

# -------------------------
# 1. 데이터 불러오기 — 절대 수정 X
# -------------------------
@st.cache_data
def load_data():
    # 너가 처음 준 코드 그대로 사용
    df = pd.read_csv("2025_books.csv", encoding="utf-8")
    return df

df = load_data()

st.write("### 데이터 미리보기")
st.dataframe(df.head())

# -------------------------
# 2. 연도별 대출량 추세 (선 그래프)
# -------------------------
st.subheader("📈 연도별 전체 대출 추세")

yearly = df.groupby("연도")["대출권수"].sum().reset_index()

fig1 = px.line(
    yearly,
    x="연도",
    y="대출권수",
    markers=True,
    title="연도별 전체 대출 변화",
)
st.plotly_chart(fig1, use_container_width=True)


# -------------------------
# 3. 자료 유형별 대출 비중 (Treemap)
# -------------------------
st.subheader("🌳 자료 유형별 대출 비중 (Treemap)")

type_count = df.groupby("자료유형")["대출권수"].sum().reset_index()

fig2 = px.treemap(
    type_count,
    path=["자료유형"],
    values="대출권수",
    title="자료 유형별 대출 비중 (Treemap)",
)
st.plotly_chart(fig2, use_container_width=True)


# -------------------------
# 4. 주제별 대출 분포 (Sunburst)
# -------------------------
st.subheader("🌞 주제별 대출 분포 (Sunburst)")

subject = df.groupby(["대분류", "중분류"])["대출권수"].sum().reset_index()

fig3 = px.sunburst(
    subject,
    path=["대분류", "중분류"],
    values="대출권수",
    title="주제별 대출 비중",
)
st.plotly_chart(fig3, use_container_width=True)


# -------------------------
# 5. 연령대별 대출 비교 (막대 + 선 혼합)
# -------------------------
st.subheader("👤 연령별 대출 비교")

age = df.groupby("연령대")["대출권수"].sum().reset_index()

fig4 = px.bar(
    age,
    x="연령대",
    y="대출권수",
    title="연령대별 대출량",
    text_auto=True
)
fig4.update_traces(marker=dict(line=dict(width=1)))
st.plotly_chart(fig4, use_container_width=True)


# -------------------------
# 6. 월별 대출량 추세 (오버레이)
# -------------------------
st.subheader("📅 월별 대출 추세")

monthly = df.groupby("월")["대출권수"].sum().reset_index()

fig5 = px.area(
    monthly,
    x="월",
    y="대출권수",
    title="월별 대출 추세",
)
st.plotly_chart(fig5, use_container_width=True)


# -------------------------
# 7. 자료 유형 + 연령대 교차 (Bubble chart)
# -------------------------
st.subheader("🔵 자료 유형 × 연령대 (버블 차트)")

bubble = df.groupby(["자료유형", "연령대"])["대출권수"].sum().reset_index()

fig6 = px.scatter(
    bubble,
    x="자료유형",
    y="연령대",
    size="대출권수",
    color="자료유형",
    title="자료 유형 × 연령대 버블 차트",
)
st.plotly_chart(fig6, use_container_width=True)


# -------------------------
# 8. 상관관계 히트맵 (오류 없음 / seaborn)
# -------------------------
st.subheader("🔥 수치 변수 상관관계 히트맵")

corr = df.select_dtypes("number").corr()

fig7, ax = plt.subplots()
sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
st.pyplot(fig7)
