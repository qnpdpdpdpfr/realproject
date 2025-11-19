import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px

st.set_page_config(page_title="Library Dashboard", layout="wide")
st.title("📚 도서 대출 분석 대시보드")

# -----------------------------------------------------
# 데이터 불러오기
# -----------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("loan_data.csv")
    return df

df = load_data()

# -----------------------------------------------------
# 한국 지도 데이터 불러오기 (sido geojson)
# -----------------------------------------------------
@st.cache_data
def load_geo():
    geo = gpd.read_file("korea_sido.geojson")
    return geo

geo = load_geo()

# -----------------------------------------------------
# 사이드바 필터
# -----------------------------------------------------
with st.sidebar:
    st.header("🔎 필터")
    years = st.multiselect("연도 선택", sorted(df["연도"].unique()), default=sorted(df["연도"].unique()))
    materials = st.multiselect("자료유형 선택", sorted(df["자료유형"].unique()), default=sorted(df["자료유형"].unique()))
    topics = st.multiselect("주제 선택", sorted(df["주제"].unique()), default=sorted(df["주제"].unique()))

filtered = df[df["연도"].isin(years) & df["자료유형"].isin(materials) & df["주제"].isin(topics)]

# -----------------------------------------------------
# 1️⃣ 지역별 대출권수 지도 시각화
# -----------------------------------------------------
st.subheader("📍 지역별 대출권수 지도 (Choropleth Map)")

# 지역 집계
region_sum = filtered.groupby("지역")["대출권수"].sum().reset_index()

# merge
merged = geo.merge(region_sum, left_on="sido", right_on="지역", how="left")

# 지도 생성
m = folium.Map(location=[36.5, 127.8], zoom_start=7)

folium.Choropleth(
    geo_data=merged,
    data=merged,
    columns=["sido", "대출권수"],
    key_on="feature.properties.sido",
    fill_color="YlOrRd",
    fill_opacity=0.8,
    line_opacity=0.6,
    nan_fill_color="lightgray",
    legend_name="대출권수"
).add_to(m)

st_folium(m, width=900, height=550)

st.markdown("---")

# -----------------------------------------------------
# 2️⃣ 연도별 대출 추이 (Line + Marker)
# -----------------------------------------------------
st.subheader("📈 연도별 대출권수 추이")

year_df = filtered.groupby("연도")["대출권수"].sum().reset_index()

fig1 = px.line(
    year_df,
    x="연도",
    y="대출권수",
    markers=True,
    title="연도별 대출권수 변화"
)
st.plotly_chart(fig1, use_container_width=True)

# -----------------------------------------------------
# 3️⃣ 주제별 비중 (Donut Chart)
# -----------------------------------------------------
st.subheader("🍩 주제별 대출 비중")

subj = filtered.groupby("주제")["대출권수"].sum().reset_index()

fig2 = px.pie(
    subj,
    values="대출권수",
    names="주제",
    hole=0.4,
    title="주제별 대출 비중"
)
st.plotly_chart(fig2, use_container_width=True)

# -----------------------------------------------------
# 4️⃣ 연령대별 대출량 (Horizontal Bar)
# -----------------------------------------------------
st.subheader("🧑‍🧒 연령대별 대출권수")

age_df = filtered.groupby("연령대")["대출권수"].sum().reset_index()

fig3 = px.bar(
    age_df,
    x="대출권수",
    y="연령대",
    orientation="h",
    title="연령대별 대출량"
)
st.plotly_chart(fig3, use_container_width=True)

# -----------------------------------------------------
# 5️⃣ 자료유형별 연도 추이 (Stacked Area)
# -----------------------------------------------------
st.subheader("📚 자료유형별 연도 변화")

mat = filtered.groupby(["연도", "자료유형"])["대출권수"].sum().reset_index()

fig4 = px.area(
    mat,
    x="연도",
    y="대출권수",
    color="자료유형",
    title="자료유형별 대출량 추이"
)
st.plotly_chart(fig4, use_container_width=True)
