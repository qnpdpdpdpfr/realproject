import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from pathlib import Path
import openpyxl

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------

st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")

st.title("공공도서관 대출 데이터 심층 분석")
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
# 2. 데이터 로드 및 전처리 함수 (파일 경로 및 오류 처리 강화)
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 파일 목록 정의 (파일 이름은 기존 코드와 동일하게 유지)
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx"}
    ]
    
    # data 폴더와 현재 폴더를 모두 탐색합니다.
    data_dir = Path("data")
    all_data = []
    target_subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    target_ages = ['어린이', '청소년', '성인']

    for item in files:
        file_name = item['file']
        
        # 1. data/ 경로 확인
        file_path_data = data_dir / file_name
        # 2. 현재 실행 경로 확인
        file_path_current = Path(file_name)
        
        file_to_use = None
        if file_path_data.exists():
            file_to_use = file_path_data
        elif file_path_current.exists():
            file_to_use = file_path_current

        if not file_to_use:
            st.warning(f"**[파일 누락 경고]** {item['year']}년 데이터 파일 '{file_name}'을(를) 'data/' 또는 현재 폴더에서 찾을 수 없습니다. 이 연도의 데이터는 분석에서 제외됩니다.")
            continue

        try:
            # 엑셀 파일 로드 (header=0, 1은 엑셀 파일의 구조에 따라 다름)
            if item['year'] >= 2023:
                # 엑셀의 두 번째 행(index 1)을 헤더로 사용
                df = pd.read_excel(file_to_use, engine='openpyxl', header=1)
                # 헤더 설정 후, 첫 번째 데이터 행(원래 엑셀의 3번째 행)부터 시작하도록 iloc[1:]로 수정
                df = df.iloc[1:].reset_index(drop=True)
            else:
                # 엑셀의 첫 번째 행(index 0)을 헤더로 사용
                df = pd.read_excel(file_to_use, engine='openpyxl', header=0)
                # 헤더 설정 후, 첫 번째 데이터 행(원래 엑셀의 2번째 행)부터 시작하도록 iloc[1:]로 수정
                df = df.iloc[1:].reset_index(drop=True)

            # 지역명 추출 (4번째 컬럼 가정, index 3)
            # 컬럼 이름이 달라도 인덱스로 접근하여 '지역'을 확보합니다.
            region_col_index = 3 
            if df.shape[1] > region_col_index:
                df['Region_Fixed'] = df.iloc[:, region_col_index].astype(str).str.strip()
                df = df[df['Region_Fixed'] != 'nan']
                
                # --- [CRITICAL FIX] 총계/합계 행 필터링 (이중 합산 방지) ---
                summary_keywords = ['총계', '합계', '전체']
                # Region_Fixed 컬럼에 '총계', '합계', '전체' 등의 키워드가 포함된 행을 제거
                summary_filter = ~df['Region_Fixed'].str.contains('|'.join(summary_keywords), case=False, na=False)
                df = df[summary_filter].reset_index(drop=True)
                # -------------------------------------------------------------
            else:
                st.error(f"**[처리 오류]** {item['year']}년 파일 '{file_name}'의 4번째 컬럼(index 3)에서 지역 데이터를 찾을 수 없습니다. 파일 구조를 확인해 주세요.")
                continue

        except Exception as e:
            st.error(f"**[파일 로드 오류]** {item['year']}년 파일 '{file_name}'을(를) 로드하거나 처리하는 중 예외가 발생했습니다: {e}")
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

            # NOTE: 이전 코드에서 Material, Subject, Age가 모두 있을 때만 데이터를 추출했으나,
            # 이번 요청에서는 Material을 사용하지 않는 산점도를 위해, 데이터 추출은 기존 로직을 따릅니다.
            # 데이터프레임에는 Material 컬럼이 유지되어야 다른 차트가 정상 작동합니다.
            if subject and age and mat_type:
                # pandas.to_numeric을 사용하여 숫자로 변환하고, 오류 발생 시 0으로 대체합니다.
                numeric_values = pd.to_numeric(df[col], errors='coerce').fillna(0)
                temp_df = pd.DataFrame({'Region': df['Region_Fixed'], 'Value': numeric_values})
                region_sums = temp_df.groupby('Region')['Value'].sum()

                for region_name, val in region_sums.items():
                    # 정의된 REGION_POPULATION에 있는 지역만 포함
                    if val > 0 and region_name in REGION_POPULATION.keys(): 
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
        else:
             st.warning(f"**[데이터 추출 경고]** {item['year']}년 파일 '{file_name}'에서 유효한 대출 데이터를 추출하지 못했습니다. 컬럼 이름을 확인해 주세요.")


    if not all_data: return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    final_df['Count_Unit'] = final_df['Count'] / UNIT_DIVISOR
    
    # 인구당 대출 권수 계산
    def calculate_per_capita(row):
        year = row['Year']
        region = row['Region']
        count = row['Count']
        # 인구수 (만 명 단위) * 10000 = 실제 인구수
        population = REGION_POPULATION.get(region, {}).get(year, 1) * 10000
        # 인구 10만 명당 대출 권수 = (총 대출 권수 / 실제 인구수) * 100,000
        return count / population * 100000 if population > 0 else 0
        
    final_df['Count_Per_Capita'] = final_df.apply(calculate_per_capita, axis=1)

    return final_df

# -----------------------------------------------------------------------------
# 3. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner(f'5개년 엑셀 파일 정밀 분석 및 데이터 통합 중 (단위: {UNIT_LABEL} 적용)...'):
    df = load_and_process_data()

# -----------------------------------------------------------------------------
# 4. 시각화 시작
# -----------------------------------------------------------------------------
if df.empty:
    st.error("데이터를 추출하지 못했습니다. 위쪽의 **[파일 누락 경고]** 또는 **[파일 로드 오류]** 메시지를 확인하여 파일 경로와 구조를 점검해 주세요.")
    st.stop()

base_df = df.copy()

st.header("대출 현황 분석")
st.subheader("1. 연도별 대출 추세 분석")
    
st.markdown("---")

# -------------------------------------------------------------
# 5-1. 지역별 연간 대출 추세 (라인 차트) - 지역 필터 적용
# -------------------------------------------------------------
st.markdown("### 지역별 연간 대출 추세 (라인 차트)")
st.caption("필터 적용 기준: **지역**")

# 5-1 로컬 필터링 컨트롤러: 지역
all_regions = sorted(base_df['Region'].unique())
selected_region_5_1 = st.multiselect(
    "**비교 대상 지역**을 선택하세요",
    all_regions,
    default=['서울', '부산', '경기', '세종'],
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
st.caption("필터 적용 기준: **자료 유형**")

# 5-2 로컬 필터링 컨트롤러: 자료 유형
all_materials = sorted(base_df['Material'].unique())
selected_material_5_2 = st.multiselect(
    "**자료 유형**을 선택하세요 (선택된 유형만 표시)",
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
st.caption("필터 적용 기준: **연령대**")

# 5-3 로컬 필터링 컨트롤러: 연령대
all_ages = sorted(base_df['Age'].unique())
selected_ages_5_3 = st.multiselect(
    "**연령대**를 선택하세요 (선택된 연령만 표시)",
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
st.caption("필터 적용 기준: **주제 분야**")

# 5-4 로컬 필터링 컨트롤러: 주제 분야 및 순서 정의 (6-B에서 재사용)
all_subjects = base_df['Subject'].unique()
subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
sorted_subjects = [s for s in subject_order if s in all_subjects]
selected_subjects_5_4 = st.multiselect(
    "**주제 분야**를 선택하세요 (선택된 주제만 표시)",
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
    target_year = st.slider(
        "분석 대상 연도 선택",
        2020, 2024, 2024,
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
    st.caption("의미 강화: 절대 권수가 아닌 **인구 10만 명당 대출 권수**를 기준으로 순위를 매겨 지역별 비교의 의미를 높였습니다.")
    
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

    # -------------------------------------------------------------------------
    # 6-B. 다차원 산점도(Multi-dimensional Scatter Plot) - 요청에 따라 수정됨
    # (점 크기 확대)
    # -------------------------------------------------------------------------
    st.markdown(f"### {target_year}년 주제별/연령별 상세 분포 (다차원 산점도) - **연령대 기준**")
    
    col_filter, col_spacer = st.columns([1, 4])
    with col_filter:
        st.caption("시각화 기준: X(주제), Y(대출량), 크기(대출량), 색상(연령대), 모양(원형 통일)")
    
    # 그룹화: Subject와 Age 기준으로만 그룹화합니다. (Material 제외)
    scatter_data = detail_data.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()
    
    st.caption("분석: 점의 크기와 Y축이 클수록 대출량이 많음을 의미하며, 색상으로 연령대를 구분합니다.")
    
    # 다차원 산점도 (Scatter Plot) 생성
    fig_multi_scatter = px.scatter(
        scatter_data,
        x='Subject', # X축: 주제
        y='Count_Unit', # Y축: 대출 권수
        color='Age', # 색상: 연령대 (어린이/청소년/성인)
        size='Count_Unit', # 크기: 대출 권수 (양을 시각적으로 강조)
        hover_data=['Count_Unit'],
        title=f"{target_year}년 대출 상세 분포 (주제 x 대출량 x 연령대)",
        labels={
            'Count_Unit': f'총 대출 권수 ({UNIT_LABEL})',
            'Subject': '주제',
            'Age': '연령대'
        },
        category_orders={
            "Age": ['어린이', '청소년', '성인'], # 연령대 순서 고정
            "Subject": subject_order # 주제 순서 고정
        },
        color_discrete_sequence=px.colors.qualitative.Vivid # 연령대 시각화에 적합한 색상 팔레트 사용
    )

    # 산점도 점 크기 확대 및 스타일 조정
    if not scatter_data.empty:
        # 데이터의 최대 크기에 비례하여 sizeref 조정 (점의 최대 크기를 제어)
        # 나누는 값(예: 4)을 작게 할수록 점이 커집니다. (기존 10 -> 4로 변경하여 크기 대폭 확대)
        max_size = scatter_data['Count_Unit'].max()
        sizeref_val = max_size / 4 if max_size > 0 else 1
    else:
        sizeref_val = 1
        
    fig_multi_scatter.update_traces(
        marker=dict(
            line=dict(width=1, color='DarkSlateGrey'), 
            symbol='circle',
            sizemode='area', # 영역 기준으로 크기 조정
            sizeref=sizeref_val, # 크기 확대 (시각적 크기 기준점 낮춤)
            sizemin=10 # 최소 크기 설정 (작은 값도 보이게, 기존 8 -> 10으로 변경)
        ), 
        opacity=0.8
    )

    # 축 레이블 회전 및 레이아웃 조정
    fig_multi_scatter.update_xaxes(tickangle=45, categoryorder='array', categoryarray=subject_order)
    fig_multi_scatter.update_yaxes(tickformat=',.0f')
    fig_multi_scatter.update_layout(height=600, legend_title_text='범례')
    
    st.plotly_chart(fig_multi_scatter, use_container_width=True)
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 6-C. Pie Chart (요청에 따라 3개 연령대별 자료 유형 비율로 변경)
    # -------------------------------------------------------------------------
    with st.container():
        st.markdown(f"### {target_year}년 연령대별 자료 유형 비율 분석 (3개 Pie Charts)")
        st.caption("분석 기준: 각 연령대 내에서 **인쇄 자료**와 **전자 자료**의 대출 비율을 비교합니다.")
        
        ages_for_pie = ['어린이', '청소년', '성인']
        cols_pie = st.columns(3) # 3개의 컬럼에 차트를 나란히 배치

        color_sequences = {
            '어린이': px.colors.sequential.RdBu,
            '청소년': px.colors.sequential.Agsunset,
            '성인': px.colors.sequential.Plasma
        }

        for i, age in enumerate(ages_for_pie):
            with cols_pie[i]:
                # 특정 연령대 데이터 필터링
                age_data = detail_data[detail_data['Age'] == age]

                if age_data.empty:
                    st.warning(f"{age} 데이터 없음")
                    continue

                # Material (자료 유형: 인쇄 vs 전자) 기준으로 그룹화 및 합산
                pie_data = age_data.groupby('Material')['Count_Unit'].sum().reset_index()
                
                # 해당 연령대에 대한 파이 차트 생성
                fig_pie = px.pie(
                    pie_data,
                    values='Count_Unit',
                    names='Material',
                    title=f"**{age}** 대출 유형 비율",
                    hole=.3,
                    labels={'Count_Unit': '대출 권수 비율'},
                    height=350, # 나란히 배치하기 위해 높이 조정
                    color_discrete_sequence=color_sequences[age]
                )
                fig_pie.update_traces(textinfo='percent+label')
                # 여백 조정
                fig_pie.update_layout(margin=dict(t=50, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
