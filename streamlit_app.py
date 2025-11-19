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
st.markdown("### 5개년(2020~2024) 대출 현황 인터랙티브 대시보드 (단위: 만 권)")
st.markdown("---")

# Plotly 그래프에서 사용할 한글 기준 매핑 딕셔너리 정의 (전역 변수로 유지)
criteria_mapping = {
    'Region': '지역',
    'Subject': '주제',
    'Age': '연령',
    'Material': '자료유형'
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
            if item['year'] >= 2023:
                df = pd.read_excel(file_path, engine='openpyxl', header=1) 
                df = df.iloc[2:].reset_index(drop=True)
            else:
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True)

            region_col_name = df.columns[3]
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
    final_df['Count_Man'] = final_df['Count'] / 10000 
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
# 5. 시각화 (개선된 UI: 100% 가로 폭, 그래프별 개별 필터)
# -----------------------------------------------------------------------------
if filtered_df.empty:
    st.warning("선택한 조건의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    st.header("📊 대출 현황 분석")
    st.subheader("1. 연도별 대출 추세 분석 (기준별 개별 시각화)")

    # -------------------------------------------------------------
    # Line Chart 생성 함수 (개별 필터를 포함하도록 수정)
    # -------------------------------------------------------------
    def create_individual_trend_chart(df_data, criteria_eng, unique_key):
        criteria_kor = criteria_mapping[criteria_eng]
        
        # 1. 그래프 위에 기준 필터 배치
        st.markdown(f"#### {criteria_kor}별 대출 추세")
        
        # 해당 기준의 모든 고유 값 목록 생성
        all_options = sorted(df_data[criteria_eng].unique())
        
        # 해당 기준을 필터링하는 멀티셀렉트 생성 (Key를 사용하여 독립성 보장)
        # 기본값은 전체를 선택하거나, 너무 많으면 상위 10개만 선택
        default_selection = all_options if len(all_options) < 10 else all_options[:10]
        
        selected_options = st.multiselect(
            f"📈 {criteria_kor} 그룹 선택 (표시할 항목)",
            all_options,
            default=default_selection,
            key=f"{unique_key}_filter"
        )
        
        # 필터링된 데이터 준비
        df_filtered_by_criteria = df_data[df_data[criteria_eng].isin(selected_options)]
        
        # 데이터 집계
        line_data = df_filtered_by_criteria.groupby(['Year', criteria_eng])['Count_Man'].sum().reset_index()
        
        if line_data.empty:
            st.info(f"{criteria_kor}에 선택된 항목이 없어 그래프를 표시할 수 없습니다.")
            return

        # 2. Plotly 그래프 생성 (가로 100% 사용)
        fig = px.line(
            line_data,
            x='Year',
            y='Count_Man', 
            color=criteria_eng,
            markers=True,
            title=f"**{criteria_kor}별 연간 대출 권수 변화**",
            labels={'Count_Man': '대출 권수 (만 권)', 'Year': '연도'},
            hover_name=criteria_eng
        )
        fig.update_xaxes(type='category')
        fig.update_yaxes(tickformat='.1f') 
        
        # [수정] st.columns(2)를 사용하지 않고 바로 출력하여 가로 꽉 채움
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("---") # 그래프 간 구분선 추가

    # -------------------------------------------------------------
    # 4개 기준별 추세선 그래프 생성 (세로 배치)
    # -------------------------------------------------------------
    
    # 1. 지역별
    create_individual_trend_chart(filtered_df, 'Region', 'region_chart')

    # 2. 자료유형별
    create_individual_trend_chart(filtered_df, 'Material', 'material_chart')
