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

# [수정] 단위 설정: 다시 10만 권 (100,000)으로 복구
UNIT_DIVISOR = 100000 
UNIT_LABEL = '10만 권'

# 지도시각화를 위한 지역별 중심 좌표 (대표적인 시/도 중심 좌표)
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
            # 헤더/시작 행 처리 (연도별 파일 구조 차이 반영)
            if item['year'] == 2020:
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True)
                # 2020년 파일은 4번째 컬럼이 지역
                df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            elif item['year'] >= 2023:
                df = pd.read_excel(file_path, engine='openpyxl', header=1) 
                df = df.iloc[2:].reset_index(drop=True)
                # 2023년 이후 파일은 4번째 컬럼이 지역 (인덱스 3)
                df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            else:
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True)
                # 2021~2022년 파일은 4번째 컬럼이 지역
                df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()


            df = df[df['Region_Fixed'].isin(REGION_COORDS.keys())] # 유효한 지역만 필터링

        except Exception as e: 
            st.error(f"Error processing {item['year']} data: {e}")
            continue
        
        extracted_rows = []
        
        # [수정] 정확한 컬럼 이름 패턴을 사용하여 중복 합산 방지 및 데이터 추출
        for col in df.columns:
            col_str = str(col).strip()
            
            # 자료 유형 및 연령 추출
            mat_type = ""
            if '대출현황(연령별/주제별)_인쇄자료' in col_str or '대출/이용 수_인쇄자료' in col_str or '대출_인쇄자료' in col_str:
                mat_type = "인쇄자료"
            elif '대출현황(연령별/주제별)_전자자료' in col_str or '대출/이용 수_전자자료' in col_str or '대출_전자자료' in col_str:
                mat_type = "전자자료"
            else:
                continue

            age_match = next((a for a in target_ages if a in col_str), None)
            subject_match = next((s for s in target_subjects if s in col_str), None)

            # 세 기준이 모두 포함된 컬럼만 추출 (합계 컬럼 제외)
            if mat_type and age_match and subject_match:
                if '합계' in col_str: continue # 합계 컬럼 제외 (중복 방지)
                
                # 데이터 추출 및 지역별 합산
                numeric_values = pd.to_numeric(df[col], errors='coerce').fillna(0)
                temp_df = pd.DataFrame({'Region': df['Region_Fixed'], 'Value': numeric_values})
                region_sums = temp_df.groupby('Region')['Value'].sum()

                for region_name, val in region_sums.items():
                    if val > 0:
                        extracted_rows.append({
                            'Year': item['year'],
                            'Region': region_name,
                            'Material': mat_type,
                            'Subject': subject_match,
                            'Age': age_match,
                            'Count': val # 원본 권수
                        })

        if extracted_rows:
            year_df = pd.DataFrame(extracted_rows)
            all_data.append(year_df)

    if not all_data: return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    # [수정] 10만 권 단위 변수 복구
    final_df['Count_Unit'] = final_df['Count'] / UNIT_DIVISOR 
    
    # 지도시각화를 위해 위도/경도 정보 추가
    final_df['Lat'] = final_df['Region'].apply(lambda x: REGION_COORDS.get(x, (36.3, 127.8))[0])
    final_df['Lon'] = final_df['Region'].apply(lambda x: REGION_COORDS.get(x, (36.3, 127.8))[1])
    
    return final_df

# -----------------------------------------------------------------------------
# 3. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner(f'⏳ 5개년 엑셀 파일 정밀 분석 및 데이터 통합 중 (단위: {UNIT_LABEL} 적용)...'):
    df = load_and_process_data()

# -----------------------------------------------------------------------------
# 4. 대시보드 UI (필터 중앙 배치)
# -----------------------------------------------------------------------------
if df.empty:
    st.error("😭 데이터를 추출하지 못했습니다. 필터링 조건을 조정하거나 파일 경로를 확인해 주세요.")
    st.stop()

# 4-1. 필터 섹션
st.header("⚙️ 분석 조건 설정")

all_regions = sorted(df['Region'].unique())
selected_regions = st.multiselect(
    "📍 **분석 대상 지역을 선택하세요** (다중 선택 가능)",
    all_regions,
    default=all_regions[:5] if len(all_regions) > 0 else []
)

st.subheader("세부 분류 기준 선택")
col_mat, col_age, col_subj = st.columns(3)

with col_mat:
    all_materials = sorted(df['Material'].unique())
    selected_material = st.multiselect("📚 **자료 유형**", all_materials, default=all_materials)

with col_age:
    all_ages = sorted(df['Age'].unique())
    selected_ages = st.multiselect("👶 **연령대**", all_ages, default=all_ages)

with col_subj:
    all_subjects = df['Subject'].unique()
    subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    sorted_subjects = [s for s in subject_order if s in all_subjects]
    selected_subjects = st.multiselect("📖 **주제 분야**", sorted_subjects, default=sorted_subjects)

st.markdown("---")

# 필터링 적용
filtered_df = df[
    (df['Region'].isin(selected_regions)) &
    (df['Material'].isin(selected_material)) &
    (df['Age'].isin(selected_ages)) &
    (df['Subject'].isin(selected_subjects))
]

# -----------------------------------------------------------------------------
# 5. 시각화 
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.warning("선택한 조건의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    st.header("📊 대출 현황 분석")
    st.subheader("1. 연도별 대출 추세 분석")
    
    st.markdown("---") 

    # -------------------------------------------------------------
    # 5-1. 지역별 대출 추세 (Mapbox - 인터랙티브 애니메이션 복구)
    # -------------------------------------------------------------
    st.markdown("### 지역별 연간 대출 추세 (지도 시각화 - 색상 진하기 + 연도별 애니메이션)")
    
    st.info("💡 **지도 사용법:** 하단 슬라이더를 움직이거나 재생 버튼을 눌러 연도별 대출 권수의 변화를 확인하세요. 색상 진하기가 대출 권수를 나타냅니다.")

    # 지역별 연도별 집계
    map_data = filtered_df.groupby(['Year', 'Region', 'Lat', 'Lon'])['Count_Unit'].sum().reset_index()

    fig_map = px.scatter_mapbox(
        map_data, 
        lat="Lat", 
        lon="Lon", 
        hover_name="Region", 
        size=[30] * len(map_data),          # 점 크기 고정 (가시성 확보)
        color="Count_Unit",                 # 색상을 대출 권수로 사용
        color_continuous_scale=px.colors.sequential.Plasma,
        # [복구] 인터랙티브 애니메이션
        animation_frame="Year",             
        zoom=6.5,                           # 줌 레벨 조정
        height=600,
        title=f"**연도별 지역 대출 권수 분포** (색상 진하기: {UNIT_LABEL})",
        
    )
    
    fig_map.update_layout(
        mapbox_style="carto-positron",
        mapbox_center={"lat": 36.3, "lon": 127.8},
        margin={"r":0,"t":50,"l":0,"b":0},
        coloraxis_colorbar=dict(
            title=f"대출 권수<br>(단위: {UNIT_LABEL})",
            tickformat=',.0f' # 10만 단위로 표시
        )
    )
    fig_map.update_traces(marker=dict(sizemin=5))

    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("---") 
    
    
    # -------------------------------------------------------------
    # 5-2. 자료유형별 연간 추세 (비율-추세 Bar Chart)
    # -------------------------------------------------------------
    st.markdown("### 자료유형별 연간 대출 추세 (비율 강조 Bar Chart)")
    
    col_mat_chart, col_mat_type = st.columns([3, 1])

    with col_mat_type:
        chart_type = st.radio(
            "차트 유형 선택",
            ('Stacked Bar (총량+비율)', 'Grouped Bar (개별 비교)'),
            key='material_chart_type'
        )

    material_data = filtered_df.groupby(['Year', 'Material'])['Count_Unit'].sum().reset_index()

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

    with col_mat_chart:
        fig_mat.update_xaxes(type='category')
        fig_mat.update_yaxes(tickformat=',.0f') 
        st.plotly_chart(fig_mat, use_container_width=True)
        
    st.markdown("---") 
    
    
    # -------------------------------------------------------------
    # 5-3. 연령별 연간 추세 (Grouped Bar Chart)
    # -------------------------------------------------------------
    st.markdown("### 연령별 연간 대출 추세 (Grouped Bar Chart)")
    
    age_bar_data = filtered_df.groupby(['Year', 'Age'])['Count_Unit'].sum().reset_index()

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
    
    subject_line_data = filtered_df.groupby(['Year', 'Subject'])['Count_Unit'].sum().reset_index()
    
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
    # 6. 상세 분포 분석 (버블차트 재구성을 위해 Grouped Bar Chart로 임시 복귀)
    # -------------------------------------------------------------
    st.subheader("2. 주제, 연령, 자료유형별 상세 분포 분석")
    
    target_year = st.slider("분석 대상 연도 선택", 2020, 2024, 2024, key='detail_year_select')
    detail_data = filtered_df[filtered_df['Year'] == target_year]

    if not detail_data.empty:
        
        # --- 2-A. 지역별 순위 ---
        st.markdown(f"### {target_year}년 지역별 대출 순위 (Bar Chart)")
        
        regional_data = detail_data.groupby('Region')['Count_Unit'].sum().reset_index()
        
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

        # --- 2-B. 주제/연령대 대출 비교 (Grouped Bar Chart - 임시 복귀) ---
        st.markdown(f"### {target_year}년 주제별 연령대 대출 비교 (Grouped Bar Chart - 임시)")
        st.warning("⚠️ **잠시 안내:** 이전 요청하신 **다기준 버블 차트**를 재구성하기 위해 잠시 **Grouped Bar Chart**로 복귀했습니다. 버블 차트에 사용하실 **X축, Y축, 색상, 크기** 기준을 다시 말씀해주시면 반영하겠습니다.")
        
        subject_age_data = detail_data.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()
        
        fig_grouped_bar = px.bar(
            subject_age_data,
            x='Subject',
            y='Count_Unit',
            color='Age',
            barmode='group', 
            title="주제별 연령대별 대출 권수 비교",
            labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Subject': '주제', 'Age': '연령대'},
            category_orders={"Age": ['어린이', '청소년', '성인']}, 
            color_discrete_sequence=px.colors.sequential.Sunset
        )
        fig_grouped_bar.update_yaxes(tickformat=',.0f')
        st.plotly_chart(fig_grouped_bar, use_container_width=True)
        st.markdown("---") 

        # **Pie Chart (자료 유형 비율)**
        with st.container():
            st.markdown(f"### {target_year}년 자료 유형 비율 (Pie Chart)")
            material_data_pie = detail_data.groupby('Material')['Count_Unit'].sum().reset_index()
            
            fig_pie = px.pie(
                material_data_pie,
                values='Count_Unit',
                names='Material',
                title="자료 유형 (인쇄 vs 전자) 비율",
                hole=.3, 
                labels={'Count_Unit': '대출 권수 비율', 'Material': '자료유형'},
                height=500,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            fig_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
            

    # 5-3. 데이터 테이블
    with st.expander("원본 추출 데이터 테이블 확인 (필터 적용됨)"):
        st.dataframe(filtered_df.sort_values(by=['Year', 'Region', 'Subject']), use_container_width=True)
