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

# 지도시각화를 위한 지역별 중심 좌표
REGION_COORDS = {
    '서울': (37.5665, 126.9780), '부산': (35.1796, 129.0756), '대구': (35.8722, 128.6025), 
    '인천': (37.4563, 126.7052), '광주': (35.1595, 126.8526), '대전': (36.3504, 127.3845), 
    '울산': (35.5384, 129.3114), '세종': (36.4800, 127.2890), '경기': (37.2750, 127.0090), 
    '강원': (37.8853, 127.7298), '충북': (36.6356, 127.4913), '충남': (36.5184, 126.8837), 
    '전북': (35.8200, 127.1080), '전남': (34.8168, 126.4628), '경북': (36.5760, 128.5050), 
    '경남': (35.2383, 128.6925), '제주': (33.4996, 126.5312)
}

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수 
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 파일 목록 (이전과 동일)
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
            # 헤더/시작 행 처리
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
        
        # 컬럼 매칭 로직 (이전과 동일)
        for col in df.columns:
            col_str = str(col)
            mat_type = ""
            if '전자자료' in col_str: mat_type = "전자자료"
            elif '인쇄자료' in col_str: mat_type = "인쇄자료"
            else: continue 

            subject = next((s for s in target_subjects if s in col_str), None)
            age = next((a for a in target_ages if a in col_str), None)

            if subject and age and mat_type:
                if subject and '합계' in col_str and not age: continue 
                
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
    
    # 지도시각화를 위한 위도/경도 정보 추가 (이전과 동일)
    final_df['Lat'] = final_df['Region'].apply(lambda x: REGION_COORDS.get(x, (36.3, 127.8))[0])
    final_df['Lon'] = final_df['Region'].apply(lambda x: REGION_COORDS.get(x, (36.3, 127.8))[1])
    
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

# 기본 데이터 변수 설정 (필터링 전 원본)
base_df = df.copy()

st.header("📊 대출 현황 분석")
st.subheader("1. 연도별 대출 추세 분석")
    
st.markdown("---") 

# -------------------------------------------------------------
# 5-1. 지역별 대출 추세 (Mapbox - Scatter Mapbox) - NO FILTER
# -------------------------------------------------------------
st.markdown("### 지역별 연간 대출 추세 (지도 시각화 - 전체 현황)")
st.info("💡 **지도 사용법:** 하단 슬라이더를 움직여 연도별 전체 변화를 확인하세요. 이 차트에는 로컬 필터가 적용되지 않습니다.")

# 필터링 없이 전체 데이터 사용
map_data = base_df.groupby(['Year', 'Region', 'Lat', 'Lon'])['Count_Unit'].sum().reset_index()

fig_map = px.scatter_mapbox(
    map_data, 
    lat="Lat", 
    lon="Lon", 
    hover_name="Region", 
    size="Count_Unit",                          
    color="Count_Unit",                 
    color_continuous_scale=px.colors.sequential.Blues, 
    animation_frame="Year",             
    zoom=6.5,                           
    height=600,
    size_max=50, # Plotly 오류 방지를 위해 유효한 위치에 유지
    title=f"**연도별 지역 대출 권수 분포** (크기 및 색상 진하기: {UNIT_LABEL})",
)

fig_map.update_layout(
    mapbox_style="carto-positron",
    mapbox_center={"lat": 36.3, "lon": 127.8},
    margin={"r":0,"t":50,"l":0,"b":0},
    coloraxis_colorbar=dict(
        title=f"대출 권수<br>(단위: {UNIT_LABEL})",
        tickformat=',.0f' 
    )
)
st.plotly_chart(fig_map, use_container_width=True)
    
st.markdown("---") 
    
# -------------------------------------------------------------
# 5-2. 자료유형별 연간 추세 (Bar Chart) - 지역 필터 적용
# -------------------------------------------------------------
st.markdown("### 자료유형별 연간 대출 추세")
st.caption("✅ **필터 적용 기준:** **지역**")

# 5-2 로컬 필터링 컨트롤러: 지역
all_regions = sorted(base_df['Region'].unique())
selected_region_5_2 = st.multiselect(
    "📍 **분석 대상 지역**을 선택하세요",
    all_regions,
    default=all_regions,
    key='filter_region_5_2'
)

# 5-2 필터링 적용
filtered_df_5_2 = base_df[base_df['Region'].isin(selected_region_5_2)]

if filtered_df_5_2.empty:
    st.warning("선택한 지역의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    # 차트 유형 로컬 컨트롤러
    chart_type = st.radio(
        "차트 유형 선택",
        ('Stacked Bar (총량+비율)', 'Grouped Bar (개별 비교)'),
        key='material_chart_type_5_2', 
        horizontal=True
    )

    material_data = filtered_df_5_2.groupby(['Year', 'Material'])['Count_Unit'].sum().reset_index()
    
    if chart_type == 'Stacked Bar (총량+비율)':
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
    else: 
        fig_mat = px.bar(
            material_data,
            x='Year',
            y='Count_Unit',
            color='Material',
            barmode='group',
            title=f"**자료유형별 연간 대출 권수 개별 비교**",
            labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도'},
            color_discrete_sequence=px.colors.qualitative.T10 
        )

    fig_mat.update_xaxes(type='category')
    fig_mat.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_mat, use_container_width=True)
        
st.markdown("---") 


# -------------------------------------------------------------
# 5-3. 연령별 연간 추세 (Grouped Bar Chart) - 자료 유형 필터 적용
# -------------------------------------------------------------
st.markdown("### 연령별 연간 대출 추세 (Grouped Bar Chart)")
st.caption("✅ **필터 적용 기준:** **자료 유형**")

# 5-3 로컬 필터링 컨트롤러: 자료 유형
all_materials = sorted(base_df['Material'].unique())
selected_material_5_3 = st.multiselect(
    "📚 **자료 유형**을 선택하세요",
    all_materials,
    default=all_materials,
    key='filter_material_5_3'
)

# 5-3 필터링 적용
filtered_df_5_3 = base_df[base_df['Material'].isin(selected_material_5_3)]

if filtered_df_5_3.empty:
    st.warning("선택한 자료 유형의 데이터가 없습니다. 필터를 조정해 주세요.")
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
# 5-4. 주제별 연간 추세 (Line Chart) - 연령대 필터 적용
# -------------------------------------------------------------
st.markdown("### 주제별 연간 대출 추세 (Line Chart)")
st.caption("✅ **필터 적용 기준:** **연령대**")

# 5-4 로컬 필터링 컨트롤러: 연령대
all_ages = sorted(base_df['Age'].unique())
selected_ages_5_4 = st.multiselect(
    "👶 **연령대**를 선택하세요",
    all_ages,
    default=all_ages,
    key='filter_ages_5_4'
)

# 5-4 필터링 적용
filtered_df_5_4 = base_df[base_df['Age'].isin(selected_ages_5_4)]

if filtered_df_5_4.empty:
    st.warning("선택한 연령대의 데이터가 없습니다. 필터를 조정해 주세요.")
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

# 6. 로컬 필터링 컨트롤러: 연도 (Year)
target_year = st.slider(
    "분석 대상 연도 선택", 
    2020, 2024, 2024, 
    key='detail_year_select_6' 
)
detail_data = base_df[base_df['Year'] == target_year]

if not detail_data.empty:
    
    # --- 6-A. 지역별 순위 --- 주제 필터 적용
    st.markdown(f"### {target_year}년 지역별 대출 순위 (Bar Chart)")
    st.caption("✅ **필터 적용 기준:** **주제 분야**")
    
    # 6-A 로컬 필터링 컨트롤러: 주제 분야
    all_subjects = base_df['Subject'].unique()
    subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    sorted_subjects = [s for s in subject_order if s in all_subjects]
    selected_subjects_6_A = st.multiselect(
        "📖 **주제 분야**를 선택하세요", 
        sorted_subjects, 
        default=sorted_subjects,
        key='filter_subject_6_A'
    )
    
    # 6-A 필터링 적용
    filtered_df_6_A = detail_data[detail_data['Subject'].isin(selected_subjects_6_A)]
    
    if filtered_df_6_A.empty:
        st.warning("선택한 주제 분야의 데이터가 없습니다. 필터를 조정해 주세요.")
    else:
        regional_data = filtered_df_6_A.groupby('Region')['Count_Unit'].sum().reset_index()
        
        fig_bar_regional = px.bar(
            regional_data.sort_values('Count_Unit', ascending=False), 
            x='Region', 
            y='Count_Unit', 
            color='Region',
            title="지역별 총 대출 권수 순위",
            labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Region': '지역'},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_bar_regional.update_yaxes(tickformat=',.0f')
        st.plotly_chart(fig_bar_regional, use_container_width=True)
        st.markdown("---") 

    # --- 6-B. 주제/연령대 대출 비교 (Grouped Bar Chart - 버블 차트 전환 대기) ---
    st.markdown(f"### {target_year}년 다기준 상세 분석 (버블 차트 전환 대기 중)")
    st.warning("⚠️ **버블 차트 설정 대기 중:** 원하시는 **X축, Y축, 색상, 크기** 기준을 말씀해주시면 4가지 기준을 반영하여 **버블 차트**로 전환하겠습니다.")
    
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
        
        # 6-C 로컬 필터링 컨트롤러
        pie_type = st.radio(
            "분석 기준 선택",
            ('자료 유형 (인쇄/전자)', '연령대'),
            key='pie_chart_criteria_6_C',
            horizontal=True
        )

        if pie_type == '자료 유형 (인쇄/전자)':
            pie_data = detail_data.groupby('Material')['Count_Unit'].sum().reset_index()
            names_col = 'Material'
            title = "자료 유형 (인쇄 vs 전자) 비율"
            colors = px.colors.sequential.RdBu
        else:
            pie_data = detail_data.groupby('Age')['Count_Unit'].sum().reset_index()
            names_col = 'Age'
            title = "연령대별 대출 권수 비율"
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
