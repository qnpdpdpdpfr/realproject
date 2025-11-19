import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json 
import re 
from io import BytesIO

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------
# 페이지 설정: Wide 모드로 설정하여 대시보드 공간 확보
st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")

st.title("📚 공공도서관 대출 데이터 심층 분석")
st.markdown("### 5개년(2020~2024) 대출 현황 인터랙티브 대시보드")
st.markdown("---")

# 단위 설정: 10만 권 (100,000)
UNIT_DIVISOR = 100000
UNIT_LABEL = '10만 권'

# 2020~2024년 지역별 인구수 (단위: 만 명, 통계청 자료 기반 추정치)
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

# -----------------------------------------------------------------------------
# 2. GeoJSON 데이터 로드 
# -----------------------------------------------------------------------------
# 사용자가 업로드한 'TL_SCCO_CTPRVN.json' 파일을 로드합니다.
KOREA_GEOJSON = None
FEATURE_ID_KEY = "properties.CTPRVN_CD" 

try:
    with open("TL_SCCO_CTPRVN.json", 'r', encoding='utf-8') as f:
        KOREA_GEOJSON = json.load(f)
except FileNotFoundError:
    st.warning("GeoJSON 파일 'TL_SCCO_CTPRVN.json'을 찾을 수 없습니다. 지도 시각화는 작동하지 않을 수 있습니다.")
except Exception as e:
    st.error(f"GeoJSON 로드 중 오류 발생: {e}")
    pass


# -----------------------------------------------------------------------------
# 3. 데이터 로드 및 전처리 함수 
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 파일 목록 (실제 환경에서는 해당 경로에 엑셀 파일이 있어야 합니다.)
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx"}
    ]
    
    # -------------------------------------------------------------------
    # 데이터 파일이 없으므로, 시각화 구조 테스트를 위한 더미 데이터를 생성합니다.
    # -------------------------------------------------------------------
    
    # 지역 코드: GeoJSON 매칭 및 인구 계산을 위해 사용
    dummy_region_codes = ['11', '26', '41', '36', '47'] 
    
    dummy_data = {
        'Year': [y for y in range(2020, 2025) for _ in range(50)],
        'Region': dummy_region_codes * 10 * 2, 
        'Material': ['인쇄자료', '전자자료'] * 25 * 2,
        'Subject': ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사'] * 5 * 2,
        'Age': ['성인', '어린이', '청소년', '성인', '어린이', '청소년', '성인', '어린이', '청소년', '성인'] * 5 * 2,
        'Count': [1000000 + i * 50000 for i in range(250)] + [1500000 + i * 30000 for i in range(250)] 
    }
    final_df = pd.DataFrame(dummy_data)
    
    # 지역 코드-지역 이름 역 매핑 (인구 계산용)
    region_code_map = {
        '서울': '11', '부산': '26', '대구': '27', 
        '인천': '28', '광주': '29', '대전': '30', 
        '울산': '31', '세종': '36', '경기': '41', 
        '강원': '51', '충북': '43', '충남': '44', 
        '전북': '53', '전남': '46', '경북': '47', 
        '경남': '48', '제주': '50'
    }
    short_region_name_map = {v: k for k, v in region_code_map.items()}

    
    # -------------------------------------------------------------
    # 공통 데이터 처리
    # -------------------------------------------------------------
    
    final_df['Count_Unit'] = final_df['Count'] / UNIT_DIVISOR 
    
    # 인구당 대출 권수 계산
    def calculate_per_capita(row):
        # 인구 계산 시에는 코드(Region)를 짧은 지역명으로 역변환하여 사용
        short_region_name = short_region_name_map.get(row['Region'], None)
        if not short_region_name: return 0 
        
        year = row['Year']
        count = row['Count']
        # 인구수는 '만 명' 단위이므로 10000을 곱하여 '명' 단위로 변환
        population = REGION_POPULATION.get(short_region_name, {}).get(year, 1) * 10000 
        # 인구 10만 명당 대출 권수
        return count / population * 100000 if population > 0 else 0
        
    final_df['Count_Per_Capita'] = final_df.apply(calculate_per_capita, axis=1)
    
    return final_df

# -----------------------------------------------------------------------------
# 4. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner(f'⏳ 5개년 데이터 분석 및 통합 중 (단위: {UNIT_LABEL} 적용)...'):
    df = load_and_process_data()


# -----------------------------------------------------------------------------
# 5. 시각화 시작
# -----------------------------------------------------------------------------
if df.empty:
    st.error("😭 데이터를 추출하지 못했습니다. (데이터 부재)")
    st.stop() 

base_df = df.copy()

# 주제 분야 순서 정의
all_subjects = base_df['Subject'].unique()
subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
sorted_subjects = [s for s in subject_order if s in all_subjects]

# GeoJSON 코드(Region)를 실제 지역 이름으로 변환하는 맵
region_name_map = {
    '11': '서울특별시', '26': '부산광역시', '27': '대구광역시', 
    '28': '인천광역시', '29': '광주광역시', '30': '대전광역시', 
    '31': '울산광역시', '36': '세종특별자치시', '41': '경기도', 
    '51': '강원특별자치도', '43': '충청북도', '44': '충청남도', 
    '53': '전북특별자치도', '46': '전라남도', '47': '경상북도', 
    '48': '경상남도', '50': '제주특별자치도'
}


st.header("📊 대출 현황 분석")
st.subheader("1. 연도별 대출 추세 분석")
st.markdown("---") 

# -------------------------------------------------------------
# 5-1. 지역별 연간 대출 현황 (코로플레스 맵 및 라인 차트)
# -------------------------------------------------------------
st.markdown("### 🗺️ 지역별 대출 현황 분석")

# 지도 시각화 (GeoJSON이 로드된 경우에만 표시)
if KOREA_GEOJSON is None:
    st.warning(f"GeoJSON 파일을 로드하지 못하여 지도 시각화는 표시할 수 없습니다.")
    st.markdown("---")
else:
    # 5-1-A. 코로플레스 맵 (지도)
    st.caption(f"✅ **지도 시각화 기준:** **선택 연도의 지역별 총 대출 권수**를 **단일 청색 계열의 농도**로 표현합니다.")
    
    # 지도 표시 기준 연도 선택
    map_year = st.selectbox(
        "📅 **지도 표시 기준 연도** 선택",
        options=sorted(base_df['Year'].unique(), reverse=True),
        index=0,
        key='map_year_selector'
    )
    
    map_data = base_df[base_df['Year'] == map_year].groupby('Region')['Count_Unit'].sum().reset_index()
    
    fig_map = px.choropleth(
        map_data,
        geojson=KOREA_GEOJSON,
        locations='Region', 
        color='Count_Unit', 
        featureidkey=FEATURE_ID_KEY,
        color_continuous_scale="Blues", 
        projection="mercator",
        title=f"**{map_year}년 지역별 대출 권수 분포 ({UNIT_LABEL} 단위)**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})'},
        hover_name=map_data['Region'].map(region_name_map).fillna(map_data['Region']),
        height=600
    )
    
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(coloraxis_colorbar=dict(tickformat=',.0f'))

    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("---") 

# 5-1-B. Line Chart (추세 분석용)
st.markdown("### 지역별 연간 대출 추세 (라인 차트)")
st.caption("✅ **추세 분석:** 선택 지역 간 연도별 변화 추이를 확인합니다.")

# 라인 차트에서는 지역 코드를 다시 지역 이름으로 표시
line_df = base_df.copy()
line_df['Region_Name'] = line_df['Region'].map(region_name_map).fillna(line_df['Region'])


all_regions_name = sorted(line_df['Region_Name'].unique().tolist()) 
# 더미 데이터의 지역 이름 4개만 기본 선택
default_regions = [r for r in all_regions_name if r in ['서울특별시', '부산광역시', '경기도', '세종특별자치시']] 

selected_region_5_1_line = st.multiselect(
    "📍 **비교 대상 지역**을 선택하세요",
    all_regions_name,
    default=default_regions, 
    key='filter_region_5_1_line' 
)

line_filtered_df = line_df[line_df['Region_Name'].isin(selected_region_5_1_line)]

if line_filtered_df.empty:
    st.warning("선택한 지역의 데이터가 없어 라인 차트를 표시할 수 없습니다. 필터를 조정해 주세요.")
else:
    region_line_data = line_filtered_df.groupby(['Year', 'Region_Name'])['Count_Unit'].sum().reset_index()

    fig_region_line = px.line(
        region_line_data,
        x='Year',
        y='Count_Unit',
        color='Region_Name', 
        markers=True,
        title=f"**선택 지역별 연간 대출 권수 변화 추이**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도', 'Region_Name': '지역'},
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_region_line.update_xaxes(type='category')
    fig_region_line.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_region_line, use_container_width=True)

st.markdown("---") 
    
# -------------------------------------------------------------
# 5-2. 자료유형별 연간 추세 (Stacked Bar Chart 고정)
# -------------------------------------------------------------
st.markdown("### 자료유형별 연간 대출 추세")
st.caption("✅ **필터 적용 기준:** **자료 유형**")

all_materials = sorted(base_df['Material'].unique())
selected_material_5_2 = st.multiselect(
    "📚 **자료 유형**을 선택하세요 (선택된 유형만 표시)",
    all_materials,
    default=all_materials,
    key='filter_material_5_2'
)

# 5-2 필터링 적용
filtered_df_5_2 = base_df[base_df['Material'].isin(selected_material_5_2)]

if filtered_df_5_2.empty:
    st.warning("선택한 자료 유형의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    material_data = filtered_df_5_2.groupby(['Year', 'Material'])['Count_Unit'].sum().reset_index()
    
    fig_mat = px.bar(
        material_data,
        x='Year',
        y='Count_Unit',
        color='Material',
        barmode='stack',
        title=f"**자료유형별 연간 대출 총량 및 비율 변화**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도'},
        color_discrete_sequence=px.colors.qualitative.T10 
    )

    fig_mat.update_xaxes(type='category')
    fig_mat.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_mat, use_container_width=True)
        
st.markdown("---") 


# -------------------------------------------------------------
# 5-3. 연령별 연간 추세 (Grouped Bar Chart)
# -------------------------------------------------------------
st.markdown("### 연령별 연간 대출 추세 (Grouped Bar Chart)")
st.caption("✅ **필터 적용 기준:** **연령대**")

all_ages = sorted(base_df['Age'].unique())
selected_ages_5_3 = st.multiselect(
    "👶 **연령대**를 선택하세요 (선택된 연령만 표시)",
    all_ages,
    default=all_ages,
    key='filter_ages_5_3'
)

# 5-3 필터링 적용
filtered_df_5_3 = base_df[base_df['Age'].isin(selected_ages_5_3)]

if filtered_df_5_3.empty:
    st.warning("선택한 연령대의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    age_bar_data = filtered_df_5_3.groupby(['Year', 'Age'])['Count_Unit'].sum().reset_index()

    fig_age_bar = px.bar(
        age_bar_data,
        x='Year',
        y='Count_Unit',
        color='Age',
        barmode='group', 
        title=f"**연령별 연간 대출 권수 비교**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도'},
        category_orders={"Age": ['어린이', '청소년', '성인']},
        color_discrete_sequence=px.colors.qualitative.Vivid
    )
    fig_age_bar.update_xaxes(type='category')
    fig_age_bar.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_age_bar, use_container_width=True)
st.markdown("---") 


# -------------------------------------------------------------
# 5-4. 주제별 연간 추세 (Line Chart)
# -------------------------------------------------------------
st.markdown("### 주제별 연간 대출 추세 (Line Chart)")
st.caption("✅ **필터 적용 기준:** **주제 분야**")

selected_subjects_5_4 = st.multiselect(
    "📖 **주제 분야**를 선택하세요 (선택된 주제만 표시)", 
    sorted_subjects, 
    default=sorted_subjects,
    key='filter_subject_5_4'
)

# 5-4 필터링 적용
filtered_df_5_4 = base_df[base_df['Subject'].isin(selected_subjects_5_4)]

if filtered_df_5_4.empty:
    st.warning("선택한 주제 분야의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    subject_line_data = filtered_df_5_4.groupby(['Year', 'Subject'])['Count_Unit'].sum().reset_index()
    
    fig_subject_line = px.line(
        subject_line_data,
        x='Year',
        y='Count_Unit',
        color='Subject',
        markers=True,
        title=f"**주제별 연간 대출 권수 변화**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도'},
        color_discrete_sequence=px.colors.qualitative.Dark24 
    )
    fig_subject_line.update_xaxes(type='category')
    fig_subject_line.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_subject_line, use_container_width=True)
st.markdown("---") 


# -------------------------------------------------------------
# 6. 상세 분포 분석 (특정 연도)
# -------------------------------------------------------------
st.subheader("2. 상세 분포 분석 (특정 연도)")

# 6. 공통 연도 로컬 필터링 컨트롤러
col_year_header, col_year_metric = st.columns([1, 4])
with col_year_header:
    st.header("기준 연도")
with col_year_metric:
    target_year = st.slider(
        "분석 대상 연도 선택", 
        2020, 2024, 2024, 
        key='detail_year_select_6',
        label_visibility="collapsed" 
    )
    st.metric(label="선택된 연도", value=f"{target_year}년") 

st.markdown("---") 

detail_data = base_df[base_df['Year'] == target_year]

if not detail_data.empty:
    
    # --- 6-A. 지역별 순위 --- (인구 10만 명당 순위)
    st.markdown(f"### {target_year}년 지역별 대출 순위 (인구 10만 명당)")
    st.caption("✅ **의미 강화:** 절대 권수가 아닌 **인구 10만 명당 대출 권수**를 기준으로 순위를 매겨 지역별 비교의 의미를 높였습니다.")
    
    regional_data_per_capita = detail_data.groupby('Region')['Count_Per_Capita'].sum().reset_index()
    
    # 바 차트의 Region은 코드이므로, Region_Name으로 다시 변환하여 사용
    regional_data_per_capita['Region_Name'] = regional_data_per_capita['Region'].map(region_name_map).fillna(regional_data_per_capita['Region'])

    fig_bar_regional = px.bar(
        regional_data_per_capita.sort_values('Count_Per_Capita', ascending=False), 
        x='Region_Name', 
        y='Count_Per_Capita', 
        color='Region_Name',
        title=f"지역별 인구 10만 명당 총 대출 권수 순위 ({target_year}년)",
        labels={'Count_Per_Capita': '인구 10만 명당 대출 권수', 'Region_Name': '지역'},
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_bar_regional.update_yaxes(tickformat=',.0f')
    st.plotly_chart(fig_bar_regional, use_container_width=True)
    st.markdown("---") 

    # --- 6-B. 주제/연령/자료유형 대출 비교 (트리맵 차트) ⭐️ 새로운 차트 ⭐️
    st.markdown(f"### 🎯 {target_year}년 주제별/연령별 상세 분포 (트리맵)")
    
    col_material_filter_6b, col_spacer_6b = st.columns([1, 4])
    with col_material_filter_6b:
        # 자료 유형 필터: 인쇄 또는 전자 중 하나 또는 전체 합산
        material_for_treemap = st.radio( 
            "자료 유형 선택",
            ('인쇄자료', '전자자료', '전체 합산'),
            key='treemap_material_select', 
            horizontal=True
        )

    # 필터링 적용 및 제목 설정
    if material_for_treemap != '전체 합산':
        treemap_data_filtered = detail_data[detail_data['Material'] == material_for_treemap]
        chart_title = f"{target_year}년 주제별/연령별 {material_for_treemap} 대출 비율"
        st.caption(f"✅ **분석 기준:** **상위 레벨(주제)**, **하위 레벨(연령)**, **크기/색상 농도(대출 권수)**. 현재 **{material_for_treemap}** 데이터만 표시됩니다.")
    else:
        treemap_data_filtered = detail_data
        chart_title = f"{target_year}년 주제별/연령별 전체 자료 합산 대출 비율"
        st.caption(f"✅ **분석 기준:** **상위 레벨(주제)**, **하위 레벨(연령)**, **크기/색상 농도(대출 권수)**. 현재 **인쇄+전자 자료**가 합산되어 표시됩니다.")


    # 그룹화 (Subject, Age)
    treemap_data = treemap_data_filtered.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()

    fig_treemap = px.treemap(
        treemap_data,
        path=[px.Constant("전체 대출"), 'Subject', 'Age'], # 계층 구조 설정
        values='Count_Unit',
        color='Count_Unit', 
        title=chart_title,
        labels={
            'Count_Unit': f'총 대출 권수 ({UNIT_LABEL})', 
            'Subject': '주제', 
            'Age': '연령대',
            'labels': '분류'
        },
        color_continuous_scale='Turbo', 
        height=700
    )

    fig_treemap.update_layout(margin = dict(t=50, l=25, r=25, b=25)) 
    fig_treemap.data[0].textinfo = 'label+value' 
    
    st.plotly_chart(fig_treemap, use_container_width=True)
    st.markdown("---") 

    # --- 6-C. Pie Chart ---
    with st.container():
        st.markdown(f"### {target_year}년 대출 비율 분석 (Pie Chart)")
        st.caption("✅ **기준:** 상단의 연도 슬라이더에 따라 비율이 변경됩니다.")
        
        # 6-C 로컬 필터링 컨트롤러: 기준 선택 
        pie_type = st.radio(
            "비율 분석 기준 선택",
            ('자료 유형 (인쇄/전자)', '연령대'),
            key='pie_chart_criteria_6_C',
            horizontal=True
        )

        if pie_type == '자료 유형 (인쇄/전자)':
            pie_data = detail_data.groupby('Material')['Count_Unit'].sum().reset_index()
            names_col = 'Material'
            title = f"{target_year}년 자료 유형 (인쇄 vs 전자) 비율"
            colors = px.colors.sequential.RdBu
        else:
            pie_data = detail_data.groupby('Age')['Count_Unit'].sum().reset_index()
            names_col = 'Age'
            title = f"{target_year}년 연령대별 대출 권수 비율"
            colors = px.colors.qualitative.Vivid

        fig_pie = px.pie(
            pie_data,
            values='Count_Unit',
            names=names_col,
            title=title,
            hole=.3, 
            labels={'Count_Unit': '대출 권수 비율'},
            height=500,
            color_discrete_sequence=colors
        )
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
        
# 6-1. 데이터 테이블
with st.expander("원본 추출 데이터 테이블 확인"):
    st.dataframe(base_df.sort_values(by=['Year', 'Region', 'Subject']), use_container_width=True)
