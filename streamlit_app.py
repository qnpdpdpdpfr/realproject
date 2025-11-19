import streamlit as st
import pandas as pd
import plotly.express as px
import os

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공공도서관 대출 데이터 대시보드", layout="wide")

st.title("📚 최근 5년 공공도서관 대출 데이터 분석")
st.markdown("""
이 대시보드는 2020년부터 2024년까지의 공공도서관 통계 데이터를 기반으로 
**지역별, 주제별, 연령별 대출 권수 변화**를 시각화합니다.
""")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 파일명과 해당 데이터의 실제 연도 매핑
    # (주의: data 폴더 안에 csv 파일들이 있어야 합니다)
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx - 22('20년) 통계결과표.csv"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx - 입력데이터.csv"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx - 입력데이터.csv"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx - 원자료_분석용.csv"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx - 원자료_분석용.csv"}
    ]
    
    data_dir = "data" # 데이터 파일이 있는 폴더명
    all_data = []

    # 추출할 키워드 정의
    subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    ages = ['어린이', '청소년', '성인']

    for item in files:
        file_path = os.path.join(data_dir, item['file'])
        if not os.path.exists(file_path):
            st.warning(f"파일을 찾을 수 없습니다: {item['file']}")
            continue

        try:
            # CSV 읽기 (한글 인코딩 처리)
            df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding='cp949', low_memory=False)
        
        # 컬럼명 공백 제거
        df.columns = [str(c).replace(' ', '').strip() for c in df.columns]
        
        # '지역' 컬럼 찾기
        region_cols = [c for c in df.columns if '지역' in c and '봉사' not in c]
        if not region_cols:
            continue
        region_col = region_cols[0]

        # 해당 연도 데이터 처리
        # 각 도서관별로 행이 있으므로, 지역별로 묶기 전에 필요한 숫자 컬럼만 식별
        
        # 1. 주제별 대출 (인쇄자료)
        for subj in subjects:
            # '대출' 또는 '이용' 이라는 단어와 '주제명'이 함께 있는 컬럼 찾기
            # 예: '대출권수_철학', '도서(대출)_철학' 등
            cols = [c for c in df.columns if subj in c and ('대출' in c or '이용' in c) and '전자' not in c]
            
            # 데이터가 없으면 건너뜀 (일부 연도는 컬럼명이 다를 수 있음)
            if cols:
                # 수치형 변환 후 합계
                temp_sum = df.groupby(region_col)[cols].sum(numeric_only=True).sum(axis=1).reset_index()
                temp_sum.columns = ['Region', 'Count']
                temp_sum['Year'] = item['year']
                temp_sum['Type'] = '주제별(인쇄)'
                temp_sum['Category'] = subj
                all_data.append(temp_sum)

        # 2. 연령별 대출
        for age in ages:
            cols = [c for c in df.columns if age in c and ('대출' in c or '이용' in c) and '전자' not in c]
            if cols:
                temp_sum = df.groupby(region_col)[cols].sum(numeric_only=True).sum(axis=1).reset_index()
                temp_sum.columns = ['Region', 'Count']
                temp_sum['Year'] = item['year']
                temp_sum['Type'] = '연령별'
                temp_sum['Category'] = age
                all_data.append(temp_sum)

        # 3. 전자자료 대출
        # '전자' 또는 'E-book'이 포함되고 '대출/이용'이 포함된 컬럼
        ebook_cols = [c for c in df.columns if ('전자' in c or 'E-book' in c) and ('대출' in c or '이용' in c)]
        if ebook_cols:
            temp_sum = df.groupby(region_col)[ebook_cols].sum(numeric_only=True).sum(axis=1).reset_index()
            temp_sum.columns = ['Region', 'Count']
            temp_sum['Year'] = item['year']
            temp_sum['Type'] = '자료유형'
            temp_sum['Category'] = '전자자료'
            all_data.append(temp_sum)

    if not all_data:
        return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    return final_df

# 데이터 로딩 실행
df = load_and_process_data()

# -----------------------------------------------------------------------------
# 3. 사이드바 컨트롤 (사용자 입력)
# -----------------------------------------------------------------------------
st.sidebar.header("📊 데이터 필터링")

if df.empty:
    st.error("데이터를 불러오지 못했습니다. 'data' 폴더에 CSV 파일이 있는지 확인해주세요.")
    st.stop()

# A. 지역 선택
all_regions = sorted(df['Region'].unique())
selected_regions = st.sidebar.multiselect(
    "지역 선택 (다중 선택 가능)",
    all_regions,
    default=all_regions[:5] # 기본값으로 앞의 5개 지역 선택
)

# B. 분석 기준 선택 (주제별 vs 연령별 vs 자료유형)
view_type = st.sidebar.radio(
    "분석 기준 선택",
    ('주제별(인쇄)', '연령별', '자료유형')
)

# C. 세부 카테고리 선택 (선택한 기준에 따라 옵션 변경)
available_cats = df[df['Type'] == view_type]['Category'].unique()
selected_cats = st.sidebar.multiselect(
    "세부 카테고리 선택",
    available_cats,
    default=available_cats
)

# -----------------------------------------------------------------------------
# 4. 데이터 시각화
# -----------------------------------------------------------------------------

# 데이터 필터링
filtered_df = df[
    (df['Region'].isin(selected_regions)) &
    (df['Type'] == view_type) &
    (df['Category'].isin(selected_cats))
]

if filtered_df.empty:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    # 4-1. 라인 차트 (연도별 변화)
    st.subheader(f"📈 연도별 변화 추이 ({view_type})")
    
    # 데이터를 연도/지역/카테고리 별로 집계
    line_chart_df = filtered_df.groupby(['Year', 'Region', 'Category'])['Count'].sum().reset_index()
    
    fig_line = px.line(
        line_chart_df, 
        x='Year', 
        y='Count', 
        color='Category', 
        line_group='Region',
        symbol='Region',
        markers=True,
        title=f"연도별 대출 권수 변화 ({view_type})",
        labels={'Count': '대출 권수', 'Year': '연도', 'Category': '구분', 'Region': '지역'}
    )
    fig_line.update_xaxes(type='category') # 연도를 정수로 표시하지 않고 카테고리로 표시
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

    # 4-2. 바 차트 (특정 연도 비교)
    st.subheader("📊 연도별 상세 비교")
    target_year = st.slider("비교할 연도를 선택하세요", 2020, 2024, 2024)
    
    bar_df = filtered_df[filtered_df['Year'] == target_year]
    
    if not bar_df.empty:
        fig_bar = px.bar(
            bar_df,
            x='Region',
            y='Count',
            color='Category',
            barmode='group',
            title=f"{target_year}년 지역별 대출 현황 비교",
            labels={'Count': '대출 권수', 'Region': '지역'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.write(f"{target_year}년 데이터가 없습니다.")

    # 4-3. 원본 데이터 보기 (옵션)
    with st.expander("데이터 테이블 보기"):
        st.dataframe(filtered_df)
