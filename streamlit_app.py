import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")

st.title("📚 공공도서관 대출 데이터 심층 분석")
st.markdown("### 5개년(2020~2024) 대출 현황 인터랙티브 대시보드")
st.markdown("---")

# 단위 설정: 10만 권 (100,000)
UNIT_DIVISOR = 100000
UNIT_LABEL = '10만 권'

# 2020~2024년 지역별 인구수 (단위: 만 명, 통계청 자료 기반 추정치) - 이전과 동일
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
# 2. 데이터 로드 및 전처리 함수 (이전과 동일)
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 이 부분은 데이터 디렉토리와 파일명이 Streamlit 환경에 맞게 존재한다고 가정합니다.
    # 해당 파일들은 사용자가 제공한 파일 목록에는 없으므로, 로드 실패 시 빈 DataFrame이 반환될 수 있습니다.
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
        # Streamlit 환경에서 파일 존재 여부를 확인하는 코드이므로 주석 처리 (실행 환경 고려)
        # if not os.path.exists(file_path): continue

        try:
            # 2023년 이후 파일은 헤더가 1행에 있고, 실제 데이터는 3행부터 시작
            if item['year'] >= 2023:
                df = pd.read_excel(file_path, engine='openpyxl', header=1)
                df = df.iloc[2:].reset_index(drop=True)
            # 2022년 이전 파일은 헤더가 0행에 있고, 실제 데이터는 2행부터 시작
            else:
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True)

            # 지역명 정리 (네 번째 컬럼을 지역명으로 가정)
            df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            df = df[df['Region_Fixed'] != 'nan']
        except Exception: 
            # 파일이 없거나 로드 오류 발생 시 해당 연도 스킵
            continue
        
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
    
    # 🚨 인구당 대출 권수 계산
    def calculate_per_capita(row):
        year = row['Year']
        region = row['Region']
        count = row['Count']
        # 인구수 (단위: 만 명) * 10000 = 실제 인구수
        population = REGION_POPULATION.get(region, {}).get(year, 1) * 10000 
        # (총 대출 수 / 실제 인구수) * 100000 = 인구 10만 명당 대출 수
        return count / population * 100000 if population > 0 else 0
        
    final_df['Count_Per_Capita'] = final_df.apply(calculate_per_capita, axis=1)

    return final_df

# -----------------------------------------------------------------------------
# 3. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner(f'⏳ 5개년 엑셀 파일 정밀 분석 및 데이터 통합 중 (단위: {UNIT_LABEL} 적용)...'):
    df = load_and_process_data()

# -----------------------------------------------------------------------------
# 4. 시각화 시작
# -----------------------------------------------------------------------------
if df.empty:
    # 파일을 찾지 못했을 경우 Mock 데이터 사용 (Streamlit 실행 환경 고려)
    st.warning("😭 데이터를 추출하지 못했습니다. Mock 데이터를 사용하여 대시보드를 표시합니다. 실제 파일 경로를 확인해 주세요.")
    
    # Mock Data for Visualization
    mock_data = {
        'Year': [2024, 2024, 2024, 2024, 2024, 2024, 2024, 2024, 2023, 2023],
        'Region': ['서울', '서울', '경기', '경기', '부산', '부산', '세종', '세종', '서울', '경기'],
        'Material': ['인쇄자료', '전자자료', '인쇄자료', '전자자료', '인쇄자료', '전자자료', '인쇄자료', '전자자료', '인쇄자료', '전자자료'],
        'Subject': ['문학', 'IT/컴퓨터', '문학', 'IT/컴퓨터', '역사', '사회과학', '문학', '사회과학', '문학', 'IT/컴퓨터'],
        'Age': ['성인', '성인', '어린이', '청소년', '성인', '성인', '어린이', '어린이', '성인', '청소년'],
        'Count': [500000, 200000, 400000, 150000, 100000, 50000, 80000, 30000, 450000, 120000]
    }
    df = pd.DataFrame(mock_data)
    df['Count_Unit'] = df['Count'] / UNIT_DIVISOR
    
    def calculate_per_capita_mock(row):
        return row['Count'] / (REGION_POPULATION.get(row['Region'], {}).get(row['Year'], 1) * 10000) * 100000
        
    df['Count_Per_Capita'] = df.apply(calculate_per_capita_mock, axis=1)
    
    # st.stop() # Mock 데이터 사용 시 st.stop() 주석 처리

base_df = df.copy()

st.header("📊 대출 현황 분석")
st.subheader("1. 연도별 대출 추세 분석")
    
st.markdown("---") 

# -------------------------------------------------------------
# 5-1. 지역별 연간 대출 추세 (라인 차트) - 지역 필터 적용
# -------------------------------------------------------------
st.markdown("### 지역별 연간 대출 추세 (라인 차트)")
st.caption("✅ **필터 적용 기준:** **지역**")

# 5-1 로컬 필터링 컨트롤러: 지역
all_regions = sorted(base_df['Region'].unique())
selected_region_5_1 = st.multiselect(
    "📍 **비교 대상 지역**을 선택하세요",
    all_regions,
    default=all_regions[:4] if len(all_regions) >= 4 else all_regions, # 기본값 수정
    key='filter_region_5_1'
)

map_filtered_df = base_df[base_df['Region'].isin(selected_region_5_1)]

if map_filtered_df.empty:
    st.warning("선택한 지역의 데이터가 없어 라인 차트를 표시할 수 없습니다. 필터를 조정해 주세요.")
else:
    region_line_data = map_filtered_df.groupby(['Year', 'Region'])['Count_Unit'].sum().reset_index()

    fig_region_line = px.line(
        region_line_data,
        x='Year',
        y='Count_Unit',
        color='Region',
        markers=True,
        title=f"**선택 지역별 연간 대출 권수 변화**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도'},
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_region_line.update_xaxes(type='category')
    fig_region_line.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_region_line, use_container_width=True)
    
st.markdown("---") 
    
# -------------------------------------------------------------
# 5-2. 자료유형별 연간 추세 (Stacked Bar Chart 고정) - 자료 유형 필터 적용
# -------------------------------------------------------------
st.markdown("### 자료유형별 연간 대출 추세")
st.caption("✅ **필터 적용 기준:** **자료 유형**")

# 5-2 로컬 필터링 컨트롤러: 자료 유형
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
# 5-3. 연령별 연간 추세 (Grouped Bar Chart) - 연령대 필터 적용
# -------------------------------------------------------------
st.markdown("### 연령별 연간 대출 추세 (Grouped Bar Chart)")
st.caption("✅ **필터 적용 기준:** **연령대**")

# 5-3 로컬 필터링 컨트롤러: 연령대
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
# 5-4. 주제별 연간 추세 (Line Chart) - 주제 분야 필터 적용
# -------------------------------------------------------------
st.markdown("### 주제별 연간 대출 추세 (Line Chart)")
st.caption("✅ **필터 적용 기준:** **주제 분야**")

# 5-4 로컬 필터링 컨트롤러: 주제 분야 및 순서 정의 (6-B에서 재사용)
all_subjects = base_df['Subject'].unique()
subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
sorted_subjects = [s for s in subject_order if s in all_subjects]
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

# 6. 공통 연도 로컬 필터링 컨트롤러 (슬라이더 크기 개선)
col_year_header, col_year_metric = st.columns([1, 4])
with col_year_header:
    st.header("기준 연도")
with col_year_metric:
    # 연도 슬라이더
    all_years = sorted(base_df['Year'].unique())
    target_year = st.slider(
        "분석 대상 연도 선택", 
        min(all_years), max(all_years), max(all_years), 
        key='detail_year_select_6',
        label_visibility="collapsed" # 레이블을 숨깁니다.
    )
    # 선택된 연도를 Metric으로 강조하여 시각적으로 크게 보입니다.
    st.metric(label="선택된 연도", value=f"{target_year}년") 

st.markdown("---") # 시각적 분리

detail_data = base_df[base_df['Year'] == target_year]

if not detail_data.empty:
    
    # --- 6-A. 지역별 순위 --- (인구 10만 명당 순위)
    st.markdown(f"### {target_year}년 지역별 대출 순위 (인구 10만 명당)")
    st.caption("✅ **의미 강화:** 절대 권수가 아닌 **인구 10만 명당 대출 권수**를 기준으로 순위를 매겨 지역별 비교의 의미를 높였습니다.")
    
    regional_data_per_capita = detail_data.groupby('Region')['Count_Per_Capita'].sum().reset_index()
    
    fig_bar_regional = px.bar(
        regional_data_per_capita.sort_values('Count_Per_Capita', ascending=False), 
        x='Region', 
        y='Count_Per_Capita', 
        color='Region',
        title=f"지역별 인구 10만 명당 총 대출 권수 순위 ({target_year}년)",
        labels={'Count_Per_Capita': '인구 10만 명당 대출 권수', 'Region': '지역'},
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_bar_regional.update_yaxes(tickformat=',.0f')
    st.plotly_chart(fig_bar_regional, use_container_width=True)
    st.markdown("---") 

    # --- 6-B. 주제/연령대/자료유형 대출 비교 (선버스트 차트 전환) ---
    st.markdown(f"### 🎯 {target_year}년 주제별/연령별/자료유형별 상세 분포 (선버스트 차트)")
    
    col_material_filter, col_spacer = st.columns([1, 4])
    with col_material_filter:
        # 선버스트용 자료유형 필터
        material_for_sunburst = st.radio(
            "자료 유형 선택",
            ('인쇄자료', '전자자료', '전체 합산'),
            key='sunburst_material_select',
            horizontal=True
        )

    # 필터링 적용
    if material_for_sunburst != '전체 합산':
        sunburst_data_filtered = detail_data[detail_data['Material'] == material_for_sunburst]
        chart_title = f"{target_year}년 {material_for_sunburst} 대출 상세 분포 (선버스트 차트)"
    else:
        sunburst_data_filtered = detail_data
        chart_title = f"{target_year}년 전체 자료 대출 상세 분포 (선버스트 차트)"

    # 그룹화 (Subject vs Age) - Sunburst를 위한 준비
    sunburst_data = sunburst_data_filtered.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()
    
    st.caption("✅ **분석 기준:** **Subject**를 내부 원, **Age**를 외부 원 계층으로 구성하여 **대출 권수**의 계층적 비율을 분석합니다. 중심을 클릭하면 세부 연령대 분포를 확인할 수 있습니다.")
    
    # Treemap -> Sunburst 변경
    fig_sunburst = px.sunburst(
        sunburst_data,
        path=['Subject', 'Age'], # 계층 구조 정의
        values='Count_Unit', # 면적 크기
        color='Count_Unit', # 색상 기준 (선택 사항)
        title=chart_title,
        labels={
            'Count_Unit': f'총 대출 권수 ({UNIT_LABEL})', 
            'Subject': '주제', 
            'Age': '연령대'
        },
        color_continuous_scale=px.colors.sequential.Inferno, # 색상 팔레트
    )

    # Sunburst 레이아웃 조정
    fig_sunburst.update_layout(height=600, margin=dict(t=50, l=0, r=0, b=0)) 
    # 툴팁 개선: 값과 단위를 함께 표시
    fig_sunburst.update_traces(hovertemplate='<b>%{label}</b><br>대출: %{value:,.1f} ' + UNIT_LABEL + '<extra></extra>') 
    fig_sunburst.update_traces(sort=True)

    st.plotly_chart(fig_sunburst, use_container_width=True)
    st.markdown("---") 

    # --- 6-C. Pie Chart ---
    with st.container():
        st.markdown(f"### {target_year}년 대출 비율 분석 (Pie Chart)")
        st.caption("✅ **기준:** 상단의 연도 슬라이더에 따라 비율이 변경됩니다.")
        
        # 6-C 로컬 필터링 컨트롤러: 기준 선택 (기존 유지)
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
