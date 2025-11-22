import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import openpyxl

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------

st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")

# [변경 1: 제목에 이모지 추가]
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

# 지역별 좌표 (Scatter Geo Map 사용을 위해 필요, 대한민국 중심 좌표 기준)
REGION_COORDINATES = {
    '서울': (37.5665, 126.9780), '부산': (35.1796, 129.0756), '대구': (35.8722, 128.6014),
    '인천': (37.4563, 126.7052), '광주': (35.1595, 126.8526), '대전': (36.3504, 127.3845),
    '울산': (35.5384, 129.3114), '세종': (36.4802, 127.2890), '경기': (37.2750, 127.0090),
    '강원': (37.8853, 127.7346), '충북': (36.6358, 127.4913), '충남': (36.5184, 126.8856),
    '전북': (35.8200, 127.1080), '전남': (34.8679, 126.9910), '경북': (36.5760, 128.5050),
    '경남': (35.2383, 128.6925), '제주': (33.4996, 126.5312)
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

            # Material, Subject, Age가 모두 포함된 컬럼만 대출 데이터로 간주하고 추출
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
    
    # 지도 시각화를 위한 위도/경도 컬럼 추가
    final_df['Latitude'] = final_df['Region'].map(lambda x: REGION_COORDINATES.get(x, (None, None))[0])
    final_df['Longitude'] = final_df['Region'].map(lambda x: REGION_COORDINATES.get(x, (None, None))[1])


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

# [변경 4: '대출 현황 분석' 헤더 제거]

# [변경 5: 폰트 크기 키움]
st.header("1. 연도별 대출 추세 분석")
    
st.markdown("---")

# -------------------------------------------------------------
# 5-1. 지역별 연간 대출 추세 (라인 차트) - 지역 필터 적용
# -------------------------------------------------------------
st.markdown("### 지역별 연간 대출 추세")
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
# [변경 6: 차트 유형 정보 제거]
st.markdown("### 연령별 연간 대출 추세")
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
# [변경 6: 차트 유형 정보 제거]
st.markdown("### 주제별 연간 대출 추세")
st.caption("필터 적용 기준: **주제 분야**")

# 5-4 로컬 필터링 컨트롤러: 주제 분야 및 순서 정의 (6-A, 6-B에서 재사용)
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
# [변경 5: 폰트 크기 키움]
st.header("2. 상세 분포 분석 (특정 연도)")

# 6. 공통 연도 로컬 필터링 컨트롤러 (슬라이더 크기 개선)
col_year_header, col_year_metric = st.columns([1, 4])
with col_year_header:
    # [변경 7: 폰트 크기 줄임]
    st.subheader("기준 연도")
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
    
    # -------------------------------------------------------------
    # [변경 3: 지도 시각화를 2번 섹션의 가장 위로 이동]
    # -------------------------------------------------------------
    st.markdown(f"### {target_year}년 지역별 대출 권수 지도 시각화")

    # 7-1. 데이터 준비 (지역별 총 대출 권수 합산)
    map_data = base_df[base_df['Year'] == target_year].groupby('Region').agg({
        'Count_Unit': 'sum',
        'Latitude': 'first',
        'Longitude': 'first'
    }).reset_index()

    if map_data.empty or map_data['Latitude'].isnull().any():
        st.warning("지도 시각화를 위한 지역별 데이터 또는 좌표가 부족합니다.")
    else:
        # 7-2. Scatter Geo Plot (버블 맵) 생성
        fig_map = px.scatter_geo(
            map_data,
            lat='Latitude',
            lon='Longitude',
            hover_name='Region',
            size='Count_Unit',
            color='Count_Unit',
            projection='natural earth',
            title=f'{target_year}년 지역별 총 대출 권수 분포',
            labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})'},
            color_continuous_scale=px.colors.sequential.Sunsetdark, 
            scope='asia'
        )

        # 지도 레이아웃 설정: 대한민국 주변에 집중하고 마커 크기를 키움
        fig_map.update_geos(
            fitbounds='locations', # 데이터가 있는 위치에 맞게 지도 범위 조정
            visible=False,
            showland=True,
            landcolor="lightgray",
            showcountries=True,
            countrycolor="gray"
        )
        
        # 지도 중앙점 설정 (서울 기준)
        fig_map.update_layout(
            geo=dict(
                lataxis_range=[33, 39],
                lonaxis_range=[124, 132],
                center=dict(lat=36.3, lon=127.8),
                projection_scale=8 # 지도 배율을 키워 대한민국을 확대
            ),
            height=700
        )
        
        # 마커 크기 조정: size_max를 크게 설정하여 잘 보이도록 함 (요청 반영)
        fig_map.update_traces(
            marker=dict(sizemode='area', sizeref=2 * map_data['Count_Unit'].max() / (80**2), sizemin=5), 
            selector=dict(mode='markers')
        )

        st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("---") # 지도 시각화 끝
    
    
    # --- 6-A. 지역별 주제 선호도 분석 (막대 차트 - 권수 기반으로 수정됨) --- 
    st.markdown(f"### {target_year}년 지역별 주제 선호도 분석")
    st.caption("선택된 주제별로 각 지역의 **대출 권수**를 비교하여 지역별 선호 주제의 절대량을 파악합니다. (단위: 10만 권)")
    
    # [변경 1: 지역 선택 필터 추가]
    selected_regions_6a = st.multiselect(
        "**분석할 지역**을 선택하세요",
        all_regions,
        default=['서울', '경기', '부산'],
        key='filter_region_6a'
    )
    
    # 주제 선택 인터랙티브 요소 (5-4의 순서와 동일하게 사용)
    selected_subjects_6a = st.multiselect(
        "**분석할 주제 분야**를 선택하세요",
        sorted_subjects,
        default=['문학', '사회과학', '기술과학'],
        key='filter_subject_6a'
    )
    
    # [변경 1: 필터링 조건 업데이트]
    if not selected_subjects_6a or not selected_regions_6a:
        st.warning("분석할 지역과 주제를 하나 이상 선택해 주세요.")
    else:
        # --- 1. 선택된 주제 및 연도의 데이터만 필터링 ---
        subject_loan_data = detail_data[
            (detail_data['Subject'].isin(selected_subjects_6a)) &
            (detail_data['Region'].isin(selected_regions_6a))
        ]
        
        # --- 2. 지역 및 주제별 대출 권수 합계 계산 ---
        # (단위: Count_Unit, 10만 권)
        count_data = subject_loan_data.groupby(['Region', 'Subject'])['Count_Unit'].sum().reset_index()

        fig_bar_preference = px.bar(
            count_data,
            x='Region',
            y='Count_Unit', # 변경: 비율(%) 대신 대출 권수 (10만 권 단위) 사용
            color='Subject',
            barmode='group',
            title=f"지역별 선택 주제 분야 대출 권수 비교 ({target_year}년)",
            labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Region': '지역', 'Subject': '주제'}, # 레이블 수정
            category_orders={"Subject": selected_subjects_6a},
            color_discrete_sequence=px.colors.qualitative.Set3 # 다채로운 팔레트 사용
        )
        # Y축 포맷 변경: 비율(%)에서 권수(쉼표 포맷)로 변경
        fig_bar_preference.update_yaxes(tickformat=',.0f') 
        fig_bar_preference.update_layout(height=500, xaxis_title='지역', yaxis_title=f'대출 권수 ({UNIT_LABEL})')
        st.plotly_chart(fig_bar_preference, use_container_width=True)
    st.markdown("---")


    # -------------------------------------------------------------------------
    # 6-B. 다차원 산점도(Multi-dimensional Scatter Plot) - 점 크기 아주 키움 요청 반영
    # -------------------------------------------------------------------------
    st.markdown(f"### {target_year}년 주제별/연령별 상세 분포 - **연령대 기준**")
    
        
    # 그룹화: Subject와 Age 기준으로만 그룹화합니다. (Material 제외)
    scatter_data = detail_data.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()
    
    
    # 다차원 산점도 (Scatter Plot) 생성
    fig_multi_scatter = px.scatter(
        scatter_data,
        x='Subject', # X축: 주제
        y='Count_Unit', # Y축: 대출 권수
        color='Age', # 색상: 연령대 (어린이/청소년/성인)
        size='Count_Unit', # 크기: 대출 권수 (양을 시각적으로 강조)
        size_max=100, # <<<<< [요청 반영] 산점도 점의 최대 크기를 100으로 아주 크게 증가
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
        color_discrete_map={ # 연령대별 색상 지정 (다채롭게 요청 반영)
            '어린이': 'rgb(255, 100, 100)',  # 밝은 빨강 계열
            '청소년': 'rgb(50, 200, 255)',   # 시원한 파랑 계열
            '성인': 'rgb(100, 255, 100)'      # 밝은 녹색 계열
        }
    )

    # 축 레이블 회전 및 레이아웃 조정
    fig_multi_scatter.update_xaxes(tickangle=45, categoryorder='array', categoryarray=subject_order)
    fig_multi_scatter.update_yaxes(tickformat=',.0f')
    fig_multi_scatter.update_layout(height=600, legend_title_text='범례')
    
    # 마커 스타일 조정 (sizemin=10으로 작은 점도 잘 보이도록 설정)
    fig_multi_scatter.update_traces(
        marker=dict(line=dict(width=1, color='DarkSlateGrey'), symbol='circle', sizemin=10), 
        opacity=0.8
    )

    st.plotly_chart(fig_multi_scatter, use_container_width=True)
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 6-C. Pie Chart (연령별 자료 유형 선호도 분석) - 다채로운 팔레트 요청 반영
    # -------------------------------------------------------------------------
    with st.container():
        st.markdown(f"### {target_year}년 연령별 자료 유형 선호도 분석")
        st.caption("")
        
        # 분석 대상 연령대 정의
        age_groups_6c = ['어린이', '청소년', '성인']
        
        # 각 연령대별 차트의 팔레트 정의 (다채롭게 요청 반영)
        palette_map = {
            '어린이': px.colors.sequential.Sunset, # 따뜻한 계열
            '청소년': px.colors.sequential.Teal,   # 시원한 계열
            '성인': px.colors.sequential.Purp   # 중립적 계열
        }
        
        # 세 개의 파이 차트를 나란히 표시하기 위해 컬럼 생성
        cols_pie = st.columns(len(age_groups_6c))

        for i, age in enumerate(age_groups_6c):
            with cols_pie[i]:
                # 해당 연령대의 데이터 필터링
                age_pie_data = detail_data[detail_data['Age'] == age]

                if age_pie_data.empty:
                    st.warning(f"{age} 데이터가 없습니다.")
                    continue

                # Material 유형별 대출 권수 합산
                material_pie_data = age_pie_data.groupby('Material')['Count_Unit'].sum().reset_index()
                
                # 비율이 0인 경우 차트 생성이 안되므로 필터링
                material_pie_data = material_pie_data[material_pie_data['Count_Unit'] > 0]

                if material_pie_data.empty:
                    st.warning(f"{age}의 유효한 대출 데이터가 없습니다.")
                    continue


                # 파이 차트 생성
                fig_pie_age = px.pie(
                    material_pie_data,
                    values='Count_Unit',
                    names='Material',
                    title=f"**{age}** ({target_year}년)",
                    hole=.4, # 도넛 형태로 표시
                    labels={'Count_Unit': '대출 권수 비율'},
                    height=450,
                    color_discrete_sequence=palette_map[age] # 연령대별로 다른 팔레트 적용
                )
                
                # 텍스트 정보에 비율과 라벨 표시
                fig_pie_age.update_traces(textinfo='percent+label', marker=dict(line=dict(color='#000000', width=1)))
                
                # 레이아웃 조정 (제목 공간 확보)
                fig_pie_age.update_layout(
                    margin=dict(t=50, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )

                st.plotly_chart(fig_pie_age, use_container_width=True)

# -------------------------------------------------------------
# 7. 지역별 대출 권수 지도 시각화 (기존 코드는 섹션 6으로 이동됨)
# -------------------------------------------------------------

st.markdown("---")
