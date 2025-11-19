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
st.markdown("### 5개년(2020~2024) 공공도서관 대출 현황 인터랙티브 대시보드")
st.markdown("---")

# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수 (연도별 헤더 조건문 추가됨)
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
            st.warning(f"⚠️ 파일을 찾을 수 없어 {item['year']}년도 데이터는 건너뜁니다: {item['file']}")
            continue

        try:
            # [수정된 부분] 연도별 조건문: 헤더 행 구조가 다름
            if item['year'] >= 2023:
                # 2023년 이후 (가정): 2행이 헤더, 5행부터 데이터 (R2=header, R3/R4=skip)
                df = pd.read_excel(file_path, engine='openpyxl', header=1) 
                df = df.iloc[2:].reset_index(drop=True)
            else:
                # 2022년 이전 (가정): 1행이 헤더, 2행부터 데이터 (R1=header, R2=data start)
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True) # R2(index 1)부터 데이터 시작 가정

            # 지역 컬럼 (D열 = 인덱스 3)
            region_col_name = df.columns[3]
            df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            df = df[df['Region_Fixed'] != 'nan']

        except Exception as e:
            st.error(f"❌ {item['year']}년 파일 처리 중 치명적 오류 발생: {e}")
            continue
        
        # -------------------------------------------------------------------------
        # 컬럼 추출 및 데이터 변환
        # -------------------------------------------------------------------------
        
        extracted_rows = []

        for col in df.columns:
            col_str = str(col)

            # 1. 자료유형 분류
            mat_type = ""
            if '전자자료' in col_str:
                mat_type = "전자자료"
            elif '인쇄자료' in col_str:
                mat_type = "인쇄자료"
            else:
                continue 

            # 2. 주제 분류
            subject = next((s for s in target_subjects if s in col_str), None)
            
            # 3. 연령 분류
            age = next((a for a in target_ages if a in col_str), None)

            # 4. 최종 검증 및 제외 로직
            # [필수]: Subject, Age, Type이 모두 분류되었는가?
            if subject and age and mat_type:
                # [제외]: 주제가 있지만 '합계'가 붙은 열은 제외 (주제별 합계가 아닌 경우)
                if subject and '합계' in col_str and not age: continue # 주제 합계 제외
                
                # 데이터 추출
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

    if not all_data:
        return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    return final_df

# -----------------------------------------------------------------------------
# 3. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner('⏳ 5개년 엑셀 파일 정밀 분석 및 데이터 통합 중...'):
    df = load_and_process_data()

# -----------------------------------------------------------------------------
# 4. 대시보드 UI (필터 중앙 배치)
# -----------------------------------------------------------------------------
if df.empty:
    st.error("😭 데이터를 추출하지 못했습니다. 파일 경로와 헤더 구조(1행/2행)를 다시 확인해 주세요.")
    st.stop()

# 4-1. 필터 섹션
st.header("⚙️ 분석 조건 설정")

# [핵심] 지역 필터는 가장 중요하므로 넓게 배치
all_regions = sorted(df['Region'].unique())
selected_regions = st.multiselect(
    "📍 **분석 대상 지역을 선택하세요** (다중 선택 가능)",
    all_regions,
    default=all_regions[:5] if len(all_regions) > 0 else []
)

# 나머지 필터는 컬럼으로 분할하여 중앙에 배치
st.subheader("세부 분류 기준 선택")
col_mat, col_age, col_subj = st.columns(3)

# 📚 자료 유형 필터
with col_mat:
    all_materials = sorted(df['Material'].unique())
    selected_material = st.multiselect("📚 **자료 유형**", all_materials, default=all_materials)

# 👶 연령대 필터
with col_age:
    all_ages = sorted(df['Age'].unique())
    selected_ages = st.multiselect("👶 **연령대**", all_ages, default=all_ages)

# 📖 주제 분야 필터
with col_subj:
    all_subjects = df['Subject'].unique()
    # 십진분류 순으로 정렬 (UI 개선)
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
# 5. 시각화 (개선된 UI)
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.warning("선택한 조건의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    # 5-1. 연도별 추세선 (Line Chart)
    st.header("📊 대출 현황 분석")
    
    # 추세선 기준 선택
    st.subheader("1. 연도별 대출 추세 (시간 흐름 분석)")
    color_by = st.radio("기준 선택", ['지역', '주제', '연령', '자료유형'], index=0, horizontal=True)
    
    line_data = filtered_df.groupby(['Year', color_by])['Count'].sum().reset_index()
    
    fig_line = px.line(
        line_data,
        x='Year',
        y='Count',
        color=color_by,
        markers=True,
        title=f"{color_by}별 연간 대출 권수 변화",
        labels={'Count': '대출 권수 (합계)', 'Year': '연도'},
        hover_name=color_by
    )
    fig_line.update_xaxes(type='category')
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # 5-2. 상세 비교 (Bar Chart & Treemap)
    st.subheader("2. 주제, 연령, 자료유형 상세 비교 (최신 연도 기준)")
    
    # 사용자가 비교할 연도 선택
    target_year = st.slider("비교할 대상 연도", 2020, 2024, 2024)
    bar_data = filtered_df[filtered_df['Year'] == target_year]

    if not bar_data.empty:
        col_bar, col_tree = st.columns([1.5, 1])

        with col_bar:
            st.markdown(f"**{target_year}년 지역별/주제별 대출 현황**")
            # Bar Chart: 지역별 & 주제별 스택
            fig_bar = px.bar(
                bar_data, x='Region', y='Count', color='Subject',
                title=f"지역별 대출 분포",
                barmode='stack',
                labels={'Count': '대출 권수', 'Region': '지역'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_tree:
            st.markdown(f"**{target_year}년 전체 대출 구성 비율**")
            # Treemap: 비율 분석에 유용
            fig_tree = px.treemap(
                bar_data, 
                path=['Material', 'Subject', 'Age'], 
                values='Count',
                title='자료유형 > 주제 > 연령별 비율'
            )
            fig_tree.update_layout(margin = dict(t=50, l=25, r=25, b=25))
            st.plotly_chart(fig_tree, use_container_width=True)
            

    # 5-3. 데이터 테이블
    with st.expander("원본 추출 데이터 테이블 확인 (필터 적용됨)"):
        st.dataframe(filtered_df.sort_values(by=['Year', 'Region', 'Subject']), use_container_width=True)
