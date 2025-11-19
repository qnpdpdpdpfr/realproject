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
# 2. 데이터 로드 및 전처리 함수 (엑셀 버전)
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # [중요] 여기에 실제 data 폴더에 넣은 엑셀 파일명을 정확히 적어주세요.
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx"}
    ]
    
    data_dir = "data" 
    all_data = []

    subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    ages = ['어린이', '청소년', '성인']

    for item in files:
        file_path = os.path.join(data_dir, item['file'])
        
        if not os.path.exists(file_path):
            st.warning(f"⚠️ 파일을 찾을 수 없습니다: {item['file']}")
            continue

        try:
            # 엑셀 파일 읽기 (engine='openpyxl' 필수)
            # sheet_name=0은 첫 번째 시트를 읽는다는 의미입니다.
            df = pd.read_excel(file_path, engine='openpyxl', sheet_name=0)
            
        except Exception as e:
            st.error(f"{item['file']} 읽기 실패: {e}")
            continue
        
        # 컬럼명 공백 제거 및 문자열 변환
        df.columns = [str(c).replace(' ', '').replace('\n', '').strip() for c in df.columns]
        
        # '지역' 컬럼 찾기
        region_cols = [c for c in df.columns if '지역' in c and '봉사' not in c]
        if not region_cols:
            continue
        region_col = region_cols[0]

        # 데이터 추출 로직
        # 1. 주제별 대출 (인쇄자료)
        for subj in subjects:
            cols = [c for c in df.columns if subj in c and ('대출' in c or '이용' in c) and '전자' not in c]
            if cols:
                # 엑셀 데이터가 숫자 대신 문자열(-)이나 공백일 수 있어 errors='coerce'로 처리
                for c in cols:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                    
                temp_sum = df.groupby(region_col)[cols].sum().sum(axis=1).reset_index()
                temp_sum.columns = ['Region', 'Count']
                temp_sum['Year'] = item['year']
                temp_sum['Type'] = '주제별(인쇄)'
                temp_sum['Category'] = subj
                all_data.append(temp_sum)

        # 2. 연령별 대출
        for age in ages:
            cols = [c for c in df.columns if age in c and ('대출' in c or '이용' in c) and '전자' not in c]
            if cols:
                for c in cols:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

                temp_sum = df.groupby(region_col)[cols].sum().sum(axis=1).reset_index()
                temp_sum.columns = ['Region', 'Count']
                temp_sum['Year'] = item['year']
                temp_sum['Type'] = '연령별'
                temp_sum['Category'] = age
                all_data.append(temp_sum)

        # 3. 전자자료 대출
        ebook_cols = [c for c in df.columns if ('전자' in c or 'E-book' in c) and ('대출' in c or '이용' in c)]
        if ebook_cols:
            for c in ebook_cols:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
                
            temp_sum = df.groupby(region_col)[ebook_cols].sum().sum(axis=1).reset_index()
            temp_sum.columns = ['Region', 'Count']
            temp_sum['Year'] = item['year']
            temp_sum['Type'] = '자료유형'
            temp_sum['Category'] = '전자자료'
            all_data.append(temp_sum)

    if not all_data:
        return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    return final_df

# -----------------------------------------------------------------------------
# 메인 실행 로직
# -----------------------------------------------------------------------------
with st.spinner('대용량 엑셀 파일을 읽고 있습니다... 잠시만 기다려주세요 (약 1~2분 소요)'):
    df = load_and_process_data()

# (이하 필터링 및 시각화 코드는 이전과 동일합니다)
# -----------------------------------------------------------------------------
# 3. 사이드바 컨트롤
# -----------------------------------------------------------------------------
st.sidebar.header("📊 데이터 필터링")

if df.empty:
    st.error("데이터를 처리하지 못했습니다. 파일명과 경로를 확인해주세요.")
    st.stop()

all_regions = sorted(df['Region'].unique())
selected_regions = st.sidebar.multiselect(
    "지역 선택 (다중 선택 가능)",
    all_regions,
    default=all_regions[:5] 
)

view_type = st.sidebar.radio(
    "분석 기준 선택",
    ('주제별(인쇄)', '연령별', '자료유형')
)

available_cats = df[df['Type'] == view_type]['Category'].unique()
selected_cats = st.sidebar.multiselect(
    "세부 카테고리 선택",
    available_cats,
    default=available_cats
)

# -----------------------------------------------------------------------------
# 4. 데이터 시각화
# -----------------------------------------------------------------------------
filtered_df = df[
    (df['Region'].isin(selected_regions)) &
    (df['Type'] == view_type) &
    (df['Category'].isin(selected_cats))
]

if filtered_df.empty:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")
else:
    st.subheader(f"📈 연도별 변화 추이 ({view_type})")
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
        labels={'Count': '대출 권수', 'Year': '연도'}
    )
    fig_line.update_xaxes(type='category')
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

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

    with st.expander("데이터 테이블 보기"):
        st.dataframe(filtered_df)
