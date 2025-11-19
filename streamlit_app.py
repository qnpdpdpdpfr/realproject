import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")

st.title("📚 도서관 데이터 심층 분석 (주제/연령/자료유형)")
st.markdown("""
2행 헤더, 5행 데이터 시작, D열 지역 기준, **주제+연령+자료유형**이 명시된 열만 정밀 추출하여 시각화합니다.
""")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수 (사용자 정의 규칙 적용)
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 파일 목록
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx"}
    ]
    
    data_dir = "data" 
    all_data = []

    # 추출 기준 정의
    target_subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    target_ages = ['어린이', '청소년', '성인']

    for item in files:
        file_path = os.path.join(data_dir, item['file'])
        
        if not os.path.exists(file_path):
            st.warning(f"⚠️ 파일을 찾을 수 없습니다: {item['file']}")
            continue

        try:
            # [규칙 1] 2행이 열 이름(header=1, 0부터 시작하므로 index 1이 2행)
            # engine='openpyxl'은 엑셀 읽기에 필수
            df = pd.read_excel(file_path, engine='openpyxl', header=1)
            
            # [규칙 2] 3행(단위), 4행(총합계) 제외하고 5행부터 데이터 사용
            # 현재 df의 0번 행은 엑셀의 3행, 1번 행은 엑셀의 4행임. 따라서 2번 행부터 슬라이싱
            df = df.iloc[2:].reset_index(drop=True)

            # [규칙 3] D열이 지역 데이터 (0,1,2,3 -> 4번째 열)
            # D열을 'Region'이라는 이름으로 별도 저장
            region_col_name = df.columns[3] # D열의 헤더 이름 가져오기
            df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            
            # 데이터가 없는 행(지역명이 nan인 경우) 제거
            df = df[df['Region_Fixed'] != 'nan']

        except Exception as e:
            st.error(f"{item['file']} 처리 중 오류 발생: {e}")
            continue
        
        # -------------------------------------------------------------------------
        # 컬럼 추출 및 데이터 변환 (Melt)
        # -------------------------------------------------------------------------
        
        extracted_rows = []

        # 전체 컬럼을 순회하며 조건에 맞는 열만 찾음
        for col in df.columns:
            col_str = str(col)

            # 1. 자료유형 분류
            mat_type = ""
            if '전자자료' in col_str:
                mat_type = "전자자료"
            elif '인쇄자료' in col_str:
                mat_type = "인쇄자료"
            else:
                continue # 전자도 인쇄도 아니면 스킵

            # 2. 주제 분류
            subject = ""
            for s in target_subjects:
                if s in col_str:
                    subject = s
                    break
            
            # 주제가 없으면 스킵 (단, 합계가 포함된 열은 명시적으로 제외하라고 했으므로)
            if subject == "":
                if '합계' in col_str:
                    continue # 주제 없는 합계 열 제외
                continue # 주제가 아예 없어도 제외

            # 3. 연령 분류
            age = ""
            for a in target_ages:
                if a in col_str:
                    age = a
                    break
            
            if age == "":
                continue # 연령 정보 없으면 제외

            # 조건에 맞는 컬럼 발견! -> 데이터 추출
            # 해당 컬럼을 숫자로 변환 (오류 발생 시 0으로 처리)
            numeric_values = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 지역별로 그룹화하여 합계 계산
            # (이미 df는 지역별로 정렬되어 있지 않을 수 있으므로 groupby 사용)
            grouped_series = df.groupby('Region_Fixed')[col].sum(numeric_only=False) # 위에서 숫자로 변환한 시리즈를 쓸 것이므로 여기선 맵핑만

            # 좀 더 효율적인 방식: 미리 숫자로 바꾼 df를 지역별로 groupby
            # 여기서는 루프 안이라 복잡해 보이지만, 로직 명확성을 위해 지역별 합계를 직접 구해서 리스트에 추가
            
            # 현재 컬럼(col)의 데이터를 지역(Region_Fixed)별로 합침
            # 1. 임시 데이터프레임 생성
            temp_df = pd.DataFrame({
                'Region': df['Region_Fixed'],
                'Value': numeric_values
            })
            
            # 2. 지역별 합계
            region_sums = temp_df.groupby('Region')['Value'].sum()

            # 3. 결과 리스트에 추가
            for region_name, val in region_sums.items():
                if val > 0: # 0인 데이터는 굳이 쌓지 않음 (데이터량 최적화)
                    extracted_rows.append({
                        'Year': item['year'],
                        'Region': region_name,
                        'Material': mat_type,
                        'Subject': subject,
                        'Age': age,
                        'Count': val
                    })

        # 연도별 처리가 끝나면 DataFrame으로 변환하여 리스트에 추가
        if extracted_rows:
            year_df = pd.DataFrame(extracted_rows)
            all_data.append(year_df)

    if not all_data:
        return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    return final_df

# -----------------------------------------------------------------------------
# 3. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner('엑셀 파일 정밀 분석 중... (2행 헤더, 5행 데이터, 주제/연령/유형 추출)'):
    df = load_and_process_data()

# -----------------------------------------------------------------------------
# 4. 대시보드 UI
# -----------------------------------------------------------------------------
if df.empty:
    st.error("조건에 맞는 데이터를 추출하지 못했습니다. 열 이름 형식을 다시 확인해주세요.")
    st.stop()

# 사이드바 필터
st.sidebar.header("🔎 데이터 필터링")

# 지역 선택
all_regions = sorted(df['Region'].unique())
selected_regions = st.sidebar.multiselect(
    "지역 선택",
    all_regions,
    default=all_regions[:5] if len(all_regions) > 0 else []
)

# 자료유형 선택
all_materials = sorted(df['Material'].unique())
selected_material = st.sidebar.multiselect("자료유형", all_materials, default=all_materials)

# 연령 선택
all_ages = sorted(df['Age'].unique())
selected_ages = st.sidebar.multiselect("연령", all_ages, default=all_ages)

# 주제 선택
all_subjects = df['Subject'].unique()
# 주제 순서 고정 (십진분류 순)
subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
sorted_subjects = [s for s in subject_order if s in all_subjects]
selected_subjects = st.sidebar.multiselect("주제", sorted_subjects, default=sorted_subjects)

# 필터링 적용
filtered_df = df[
    (df['Region'].isin(selected_regions)) &
    (df['Material'].isin(selected_material)) &
    (df['Age'].isin(selected_ages)) &
    (df['Subject'].isin(selected_subjects))
]

if filtered_df.empty:
    st.info("선택한 조건의 데이터가 없습니다.")
else:
    # 4-1. 연도별 추세선 (Line Chart)
    st.subheader(f"📈 연도별 대출 변화")
    
    # 사용자가 무엇을 기준으로 색상을 나눌지 선택
    color_by = st.radio("그래프 색상 기준", ['Region', 'Subject', 'Age', 'Material'], horizontal=True)
    
    # 데이터 집계 (연도 + 색상기준)
    line_data = filtered_df.groupby(['Year', color_by])['Count'].sum().reset_index()
    
    fig_line = px.line(
        line_data,
        x='Year',
        y='Count',
        color=color_by,
        markers=True,
        title=f"연도별 대출 권수 ({color_by}별)",
        labels={'Count': '대출 권수', 'Year': '연도'}
    )
    fig_line.update_xaxes(type='category')
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 4-2. 상세 비교 (Bar Chart - Sunburst 대체 가능하지만 막대가 직관적)
    st.subheader("📊 상세 데이터 비교 (2024년 기준)")
    
    target_year = st.slider("연도 선택", 2020, 2024, 2024)
    bar_data = filtered_df[filtered_df['Year'] == target_year]
    
    if not bar_data.empty:
        # 복잡한 데이터를 보여주기 위해 Treemap이나 Bar chart 활용
        # 여기서는 x축: 지역, y축: 대출수, 색상: 주제, 스택: 연령 등 조합 가능
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**지역별 주제 분포**")
            fig_bar1 = px.bar(
                bar_data, x='Region', y='Count', color='Subject',
                title=f"{target_year}년 지역별/주제별 대출",
                barmode='stack'
            )
            st.plotly_chart(fig_bar1, use_container_width=True)
            
        with col2:
            st.markdown("**지역별 연령 분포**")
            fig_bar2 = px.bar(
                bar_data, x='Region', y='Count', color='Age',
                title=f"{target_year}년 지역별/연령별 대출",
                barmode='group'
            )
            st.plotly_chart(fig_bar2, use_container_width=True)

    # 4-3. 로우 데이터 보기
    with st.expander("추출된 원본 데이터 확인"):
        st.dataframe(filtered_df)
