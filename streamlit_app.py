import streamlit as st
import pandas as pd
import plotly.express as px
import os
import geopandas as gpd

# --------------------------------------------------------------------------
# 1. 설정 및 제목
# --------------------------------------------------------------------------
st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")
st.title("📚 공공도서관 대출 데이터 심층 분석")
st.markdown("### 5개년(2020~2024) 대출 현황 인터랙티브 대시보드")
st.markdown("---")

UNIT_DIVISOR = 100000
UNIT_LABEL = '10만 권'

REGION_POPULATION = {
    '서울': {2020: 980, 2021: 960, 2022: 950, 2023: 940, 2024: 935},
    '부산': {2020: 335, 2021: 330, 2022: 325, 2023: 320, 2024: 315},
    '대구': {2020: 242, 2021: 240, 2022: 238, 2023: 235, 2024: 233},
    '인천': {2020: 295, 2021: 300, 2022: 305, 2023: 310, 2024: 315},
    '광주': {2020: 147, 2021: 146, 2022: 145, 2023: 144, 2024: 143},
    '대전': {2020: 148, 2021: 147, 2022: 146, 2023: 145, 2024: 144},
    '울산': {2020: 114, 2021: 113, 2022: 112, 2023: 111, 2024: 110},
    '세종': {2020: 35, 2021: 36, 2022: 38, 2023: 40, 2024: 41},
    '경기': {2020: 1340, 2021: 1355, 2022: 1370, 2023: 1390, 2024: 1410},
    '강원': {2020: 154, 2021: 154, 2022: 154, 2023: 154, 2024: 154},
    '충북': {2020: 160, 2021: 161, 2022: 162, 2023: 163, 2024: 164},
    '충남': {2020: 212, 2021: 213, 2022: 214, 2023: 215, 2024: 216},
    '전북': {2020: 179, 2021: 178, 2022: 177, 2023: 176, 2024: 175},
    '전남': {2020: 184, 2021: 183, 2022: 182, 2023: 181, 2024: 180},
    '경북': {2020: 265, 2021: 264, 2022: 263, 2023: 262, 2024: 261},
    '경남': {2020: 335, 2021: 332, 2022: 330, 2023: 328, 2024: 325},
    '제주': {2020: 67, 2021: 67, 2022: 67, 2023: 67, 2024: 67}
}

# --------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수 (원본 코드 그대로)
# --------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx"}
    ]
    data_dir = "data"
    all_data = []
    target_subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    target_ages = ['어린이', '청소년', '성인']

    for item in files:
        file_path = os.path.join(data_dir, item['file'])
        if not os.path.exists(file_path): continue

        try:
            if item['year'] >= 2023:
                df = pd.read_excel(file_path, engine='openpyxl', header=1)
                df = df.iloc[2:].reset_index(drop=True)
            else:
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True)

            df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            df = df[df['Region_Fixed'] != 'nan']
        except Exception: continue

        extracted_rows = []
        for col in df.columns:
            col_str = str(col)
            mat_type = ""
            if '전자자료' in col_str: mat_type = "전자자료"
            elif '인쇄자료' in col_str: mat_type = "인쇄자료"
            else: continue

            subject = next((s for s in target_subjects if s in col_str), None)
            age = next((a for a in target_ages if a in col_str), None)

            if subject and age and mat_type:
                numeric_values = pd.to_numeric(df[col], errors='coerce').fillna(0)
                temp_df = pd.DataFrame({'Region': df['Region_Fixed'], 'Value': numeric_values})
                region_sums = temp_df.groupby('Region')['Value'].sum()

                for region_name, val in region_sums.items():
                    if val > 0:
                        extracted_rows.append({
                            'Year': item['year'],
                            'Region': region_name,
                            'Material': mat_type,
                            'Subject': subject,
                            'Age': age,
                            'Count': val
                        })

        if extracted_rows:
            year_df = pd.DataFrame(extracted_rows)
            all_data.append(year_df)

    if not all_data: return pd.DataFrame()

    final_df = pd.concat(all_data, ignore_index=True)
    final_df['Count_Unit'] = final_df['Count'] / UNIT_DIVISOR

    def calculate_per_capita(row):
        year = row['Year']
        region = row['Region']
        count = row['Count']
        population = REGION_POPULATION.get(region, {}).get(year, 1) * 10000
        return count / population * 100000 if population > 0 else 0

    final_df['Count_Per_Capita'] = final_df.apply(calculate_per_capita, axis=1)
    return final_df

with st.spinner(f'⏳ 5개년 엑셀 파일 정밀 분석 및 데이터 통합 중 (단위: {UNIT_LABEL} 적용)...'):
    df = load_and_process_data()

if df.empty:
    st.error("😭 데이터를 추출하지 못했습니다. 파일 경로를 확인해 주세요.")
    st.stop()

base_df = df.copy()

# --------------------------------------------------------------------------
# 3. 첫 번째 시각화 → 지도(Choropleth)
# --------------------------------------------------------------------------
st.header("📍 지역별 대출 현황 지도")
map_year = st.slider("지도에 표시할 연도 선택", 2020, 2024, 2024)
map_data = base_df[base_df['Year']==map_year].groupby('Region')['Count_Unit'].sum().reset_index()

# GeoJSON 준비 필요
geo_path = "data/korea_regions.geojson"
gdf = gpd.read_file(geo_path)
gdf = gdf.merge(map_data, left_on='name', right_on='Region', how='left')
gdf['Count_Unit'] = gdf['Count_Unit'].fillna(0)

fig_map = px.choropleth_mapbox(
    gdf,
    geojson=gdf.geometry,
    locations=gdf.index,
    color='Count_Unit',
    hover_name='Region',
    hover_data={'Count_Unit': True},
    color_continuous_scale="Viridis",
    mapbox_style="carto-positron",
    zoom=5,
    center={"lat": 36, "lon": 127},
    opacity=0.7,
    title=f"{map_year}년 지역별 대출 권수 지도"
)
st.plotly_chart(fig_map, use_container_width=True)

# --------------------------------------------------------------------------
# 4. 상세 분포 분석 → Treemap
# --------------------------------------------------------------------------
target_year = st.slider("상세 분석 연도 선택", 2020, 2024, 2024)
detail_data = base_df[base_df['Year']==target_year]

if not detail_data.empty:
    material_for_tree = st.radio("자료 유형 선택", ('인쇄자료', '전자자료', '전체 합산'), horizontal=True)
    tree_data = detail_data.copy()
    if material_for_tree != '전체 합산':
        tree_data = tree_data[tree_data['Material']==material_for_tree]
    tree_data_grouped = tree_data.groupby(['Subject','Age','Material'])['Count_Unit'].sum().reset_index()
    
    fig_tree = px.treemap(
        tree_data_grouped,
        path=['Subject','Age','Material'],
        values='Count_Unit',
        color='Count_Unit',
        color_continuous_scale='Plasma',
        title=f"{target_year}년 {material_for_tree} 대출 상세 분포 (Treemap)"
    )
    st.plotly_chart(fig_tree, use_container_width=True)

# --------------------------------------------------------------------------
# 5. 기타 그래프 (연령별, 자료유형별, 주제별)
# --------------------------------------------------------------------------
# 연령별 Line Chart
age_line_data = base_df.groupby(['Year','Age'])['Count_Unit'].sum().reset_index()
fig_age_line = px.line(
    age_line_data, x='Year', y='Count_Unit', color='Age', markers=True,
    title="연령별 연간 대출 권수 추세",
    labels={'Count_Unit':f'대출 권수 ({UNIT_LABEL})','Year':'연도'},
    color_discrete_sequence=px.colors.qualitative.Set2
)
st.plotly_chart(fig_age_line, use_container_width=True)

# 자료유형별 Stacked Bar
material_bar_data = base_df.groupby(['Year','Material'])['Count_Unit'].sum().reset_index()
fig_material_bar = px.bar(
    material_bar_data, x='Year', y='Count_Unit', color='Material', barmode='stack',
    title="자료 유형별 연간 대출 추세",
    color_discrete_sequence=px.colors.qualitative.Pastel1
)
st.plotly_chart(fig_material_bar, use_container_width=True)
