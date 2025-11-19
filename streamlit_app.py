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

    # ... (데이터 로드 및 지역/연도/카운트 추출 로직은 이전과 동일하게 유지) ...
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
    
    # 🚨 인구당 대출 권수 계산 (지역 순위의 의미를 부여)
    def calculate_per_capita(row):
        year = row['Year']
        region = row['Region']
        count = row['Count']
        # 인구수 (단위: 만 명)
        population = REGION_POPULATION.get(region, {}).get(year, 1) * 10000 
        # 인구 10만 명당 대출 권수 (Count / Population * 100,000)
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
    st.error("😭 데이터를 추출하지 못했습니다. 파일 경로를 확인해 주세요.")
    st.stop() 

base_df = df.copy()

st.header("📊 대출 현황 분석")
st.subheader("1. 연도별 대출 추세 분석")
    
st.markdown("---") 

# -------------------------------------------------------------
# 5-1. 지역별 연간 대출 추세 (지도 -> 라인 차트로 변경) - 지역 필터 적용
# -------------------------------------------------------------
st.markdown("### 지역별 연간 대출 추세 (라인 차트)")
st.caption("✅ **필터 적용 기준:** **지역** (지도 시각화의 가독성 문제로 대체되었습니다)")

# 5-1 로컬 필터링 컨트롤러: 지역
all_regions = sorted(base_df['Region'].unique())
selected_region_5_1 = st.multiselect(
    "📍 **비교 대상 지역**을 선택하세요",
    all_regions,
    default=['서울', '부산', '경기', '세종'], # 주요 지역을 기본값으로 설정하여 비교의 의미를 높임
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
st.caption("✅ **필터 적용 기준:** **자료 유형** (차트 유형 선택은 제거되었습니다)")

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
    # Stacked Bar Chart로 고정
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

# 5-4 로컬 필터링 컨트롤러: 주제 분야
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
with st.container():
    st.markdown("#### 📅 분석 기준 연도 선택")
    target_year = st.slider(
        "분석 대상 연도 선택", 
        2020, 2024, 2024, 
        key='detail_year_select_6',
        label_visibility="collapsed" # 레이블을 숨겨 크기를 확보합니다.
    )
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

    # --- 6-B. 주제/연령대 대출 비교 (버블 차트 전환 대기) ---
    st.markdown(f"### {target_year}년 다기준 상세 분석 (버블 차트 전환 대기 중)")
    st.warning("⚠️ **버블 차트 설정 대기 중:** 원하시는 **X축, Y축, 색상, 크기** 기준을 말씀해주시면 4가지 기준을 반영하여 **버블 차트**로 전환하겠습니다. (예시: X축-주제, Y축-연령, 색상-자료, 크기-대출권수)")
    
    subject_age_data = detail_data.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()
    
    fig_grouped_bar = px.bar(
        subject_age_data,
        x='Subject',
        y='Count_Unit',
        color='Age',
        barmode='group', 
        title="주제별 연령대별 대출 권수 비교 (임시)",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Subject': '주제', 'Age': '연령대'},
        category_orders={"Age": ['어린이', '청소년', '성인']}, 
        color_discrete_sequence=px.colors.sequential.Sunset
    )
    fig_grouped_bar.update_yaxes(tickformat=',.0f')
    st.plotly_chart(fig_grouped_bar, use_container_width=True)
    st.markdown("---") 

    # --- 6-C. Pie Chart ---
    with st.container():
        st.markdown(f"### {target_year}년 자료 유형 비율 (Pie Chart)")
        st.caption("✅ **강화:** 상단의 연도 슬라이더에 따라 비율이 변경됩니다.")
        
        # 6-C 로컬 필터링 컨트롤러: 기준 선택 (기존 유지)
        pie_type = st.radio(
            "분석 기준 선택",
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
