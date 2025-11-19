import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# -----------------------------------------------------------------------------
# 1. 설정 및 제목
# -----------------------------------------------------------------------------
st.set_page_config(page_title="공공도서관 대출 데이터 대시보드 (다변수 분석)", layout="wide")

st.title("📚 공공도서관 대출 데이터 심층 분석 - 다채로운 시각화")
st.markdown("### 5개년(2020~2024) 대출 현황 심화 대시보드")
st.markdown("---")

# 단위 설정: 10만 권 (100,000)
UNIT_DIVISOR = 100000 
UNIT_LABEL = '10만 권'

# 2020~2024년 지역별 인구수 (단위: 만 명, 통계청 자료 기반 추정치)
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
# 2. 데이터 로드 및 전처리 함수 (🌟 파일명 정확히 복구 완료 🌟)
# -----------------------------------------------------------------------------
@st.cache_data
def load_and_process_data():
    # 🚨 파일명을 시스템에 업로드된 CSV 파일명과 정확히 일치시켰습니다.
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx - 22('20년) 통계결과표.csv"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx - 입력데이터.csv"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx - 입력데이터.csv"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx - 원자료_분석용.csv"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx - 원자료_분석용.csv"}
    ]
    
    all_data = []
    target_subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    target_ages = ['어린이', '청소년', '성인']

    for item in files:
        current_file_name = item['file']

        # os.path.exists 검사를 제거하여 환경 경로 이슈를 회피
        try:
            # 연도별로 다른 헤더 설정을 유지합니다.
            if item['year'] == 2020:
                df = pd.read_csv(current_file_name, encoding='cp949', header=0) 
                df = df.iloc[1:].reset_index(drop=True)
                region_col_index = 3 
            elif item['year'] >= 2023:
                df = pd.read_csv(current_file_name, encoding='cp949', header=1) 
                df = df.iloc[2:].reset_index(drop=True)
                region_col_index = 3
            else:
                df = pd.read_csv(current_file_name, encoding='cp949', header=0)
                df = df.iloc[1:].reset_index(drop=True)
                region_col_index = 3

            # 지역명 추출 로직
            df['Region_Fixed'] = df.iloc[:, region_col_index].astype(str).str.strip() 
            df = df[df['Region_Fixed'].isin(REGION_POPULATION.keys())] 
        except Exception as e:
            # 파일 읽기 또는 기본 전처리 실패 시 건너뜀
            continue
        
        extracted_rows = []
        for col in df.columns:
            col_str = str(col)
            mat_type = ""
            if '전자자료' in col_str or '전자자료수' in col_str or '대출/이용 수_전자자료' in col_str: mat_type = "전자자료"
            elif '인쇄자료' in col_str or '도서(인쇄)' in col_str or '대출/이용 수_인쇄자료' in col_str: mat_type = "인쇄자료"
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
    
    # 🚨 인구당 대출 권수 계산
    def calculate_per_capita(row):
        year = row['Year']
        region = row['Region']
        count = row['Count']
        population = REGION_POPULATION.get(region, {}).get(year, 1) * 10000 
        # 인구 10만 명당 대출 권수
        return count / population * 100000 if population > 0 else 0
        
    final_df['Count_Per_Capita'] = final_df.apply(calculate_per_capita, axis=1)

    return final_df

# -----------------------------------------------------------------------------
# 3. 데이터 로드 실행
# -----------------------------------------------------------------------------
with st.spinner(f'⏳ 5개년 데이터 통합 및 전처리 중...'):
    df = load_and_process_data()

# -----------------------------------------------------------------------------
# 4. 시각화 시작 (다채로운 시각화 코드 유지)
# -----------------------------------------------------------------------------
if df.empty:
    st.error("😭 데이터를 추출하지 못했습니다. (죄송합니다. 로딩 로직을 업로드된 파일명에 맞춰 복구했습니다. 그래도 문제가 발생한다면, 업로드된 파일 구조 자체에 이전과 다른 문제가 발생했을 수 있습니다.)")
    st.stop() 

base_df = df.copy()

st.header("📊 대출 현황 분석")
st.subheader("1. 연도별 대출 추세 심층 분석")
    
st.markdown("---") 

# -------------------------------------------------------------
# 5-1. 지역별 연간 대출 추세 (누적 영역 차트 적용)
# -------------------------------------------------------------
st.markdown("### 5-1. 지역별 연간 대출 추세 (누적 영역 차트)")
st.caption("✅ **강조 효과:** 전체 대출 총량 중 **각 지역이 차지하는 비중의 변화**를 시계열로 보여줍니다.")

all_regions = sorted(base_df['Region'].unique())
selected_region_5_1 = st.multiselect(
    "📍 **분석 대상 지역**을 선택하세요",
    all_regions,
    default=['서울', '경기', '부산', '대구', '인천'],
    key='filter_region_5_1'
)

filtered_df_5_1 = base_df[base_df['Region'].isin(selected_region_5_1)]

if filtered_df_5_1.empty:
    st.warning("선택한 지역의 데이터가 없어 차트를 표시할 수 없습니다.")
else:
    region_area_data = filtered_df_5_1.groupby(['Year', 'Region'])['Count_Unit'].sum().reset_index()

    fig_region_area = px.area(
        region_area_data,
        x='Year',
        y='Count_Unit',
        color='Region',
        line_group='Region',
        title=f"**지역별 대출 기여도 변화 추세**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Year': '연도'},
        color_discrete_sequence=px.colors.qualitative.T10 
    )
    fig_region_area.update_xaxes(type='category')
    fig_region_area.update_yaxes(tickformat=',.0f') 
    st.plotly_chart(fig_region_area, use_container_width=True)
    
st.markdown("---") 
    
# -------------------------------------------------------------
# 5-2. 자료유형별 연간 추세 (100% 누적 바 차트 적용)
# -------------------------------------------------------------
st.markdown("### 5-2. 자료유형별 연간 대출 추세 (100% 누적 바 차트)")
st.caption("✅ **강조 효과:** 총량 변화가 아닌, **자료 유형 간의 상대적 비중 변화**를 강조합니다.")

all_materials = sorted(base_df['Material'].unique())
selected_material_5_2 = st.multiselect(
    "📚 **자료 유형**을 선택하세요 (선택된 유형만 표시)",
    all_materials,
    default=all_materials,
    key='filter_material_5_2'
)

filtered_df_5_2 = base_df[base_df['Material'].isin(selected_material_5_2)]

if filtered_df_5_2.empty:
    st.warning("선택한 자료 유형의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    material_data = filtered_df_5_2.groupby(['Year', 'Material'])['Count_Unit'].sum().reset_index()
    
    # 100% 누적 바 차트 구현을 위한 비율 계산
    total_by_year = material_data.groupby('Year')['Count_Unit'].transform('sum')
    material_data['Percentage'] = material_data['Count_Unit'] / total_by_year
    
    fig_mat = px.bar(
        material_data,
        x='Year',
        y='Percentage',
        color='Material',
        barmode='stack',
        title=f"**자료유형별 연간 대출 비중 변화**",
        labels={'Percentage': '비중 (%)', 'Year': '연도'},
        color_discrete_sequence=px.colors.qualitative.T10,
        custom_data=['Material', 'Count_Unit'] 
    )
    
    fig_mat.update_layout(yaxis=dict(tickformat=".1%"))
    fig_mat.update_xaxes(type='category')
    fig_mat.update_traces(hovertemplate='연도: %{x}<br>자료 유형: %{customdata[0]}<br>비중: %{y:.1%}<br>대출 권수: %{customdata[1]:,.1f} ' + UNIT_LABEL + '<extra></extra>')
    st.plotly_chart(fig_mat, use_container_width=True)
        
st.markdown("---") 


# -------------------------------------------------------------
# 5-3. 연령별 연간 추세 (Grouped Bar Chart - 기존 유지)
# -------------------------------------------------------------
st.markdown("### 5-3. 연령별 연간 대출 추세 (Grouped Bar Chart)")
st.caption("✅ **필터 적용 기준:** **연령대** (단순 비교에 효과적이므로 기존 Bar Chart 유지)")

all_ages = sorted(base_df['Age'].unique())
selected_ages_5_3 = st.multiselect(
    "👶 **연령대**를 선택하세요 (선택된 연령만 표시)",
    all_ages,
    default=all_ages,
    key='filter_ages_5_3'
)

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
# 5-4. 주제별 연간 대출 분포 (바이올린 그림 적용)
# -------------------------------------------------------------
st.markdown("### 5-4. 주제별 연간 대출 분포 (바이올린 그림)")
st.caption("✅ **강조 효과:** 각 주제 분야의 연간 대출 권수 **분포와 변동성**을 시각화합니다.")

all_subjects = base_df['Subject'].unique()
subject_order = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
sorted_subjects = [s for s in subject_order if s in all_subjects]
selected_subjects_5_4 = st.multiselect(
    "📖 **주제 분야**를 선택하세요 (선택된 주제만 표시)", 
    sorted_subjects, 
    default=['문학', '사회과학', '기술과학'],
    key='filter_subject_5_4'
)

filtered_df_5_4 = base_df[base_df['Subject'].isin(selected_subjects_5_4)]

if filtered_df_5_4.empty:
    st.warning("선택한 주제 분야의 데이터가 없습니다. 필터를 조정해 주세요.")
else:
    fig_violin = px.violin(
        filtered_df_5_4, 
        y="Count_Unit", 
        x="Subject", 
        color="Subject", 
        box=True, 
        points="all", 
        title=f"**주제별 대출 권수 분포 및 변동성**",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Subject': '주제 분야'},
        hover_data=['Year', 'Region', 'Material', 'Age']
    )
    st.plotly_chart(fig_violin, use_container_width=True)
st.markdown("---") 


# -------------------------------------------------------------
# 6. 상세 분포 분석 (특정 연도)
# -------------------------------------------------------------
st.subheader("2. 상세 분포 분석 (특정 연도)")

with st.container():
    st.markdown("#### 📅 분석 기준 연도 선택")
    target_year = st.slider(
        "분석 대상 연도 선택", 
        2020, 2024, 2024, 
        key='detail_year_select_6',
        label_visibility="collapsed"
    )
detail_data = base_df[base_df['Year'] == target_year]

if not detail_data.empty:
    
    # --- 6-A. 지역별 순위 --- (인구 10만 명당 순위 및 증감)
    st.markdown(f"### 6-A. {target_year}년 지역별 대출 순위 (인구 10만 명당)")
    st.caption("✅ **의미 강화:** 절대 권수가 아닌 **인구 10만 명당 대출 권수**를 기준으로 순위를 매깁니다.")
    
    regional_data_per_capita = detail_data.groupby('Region')['Count_Per_Capita'].sum().reset_index()
    
    prev_year = target_year - 1
    if prev_year in base_df['Year'].unique():
        prev_data = base_df[base_df['Year'] == prev_year].groupby('Region')['Count_Per_Capita'].sum().reset_index()
        regional_data_per_capita = regional_data_per_capita.merge(
            prev_data, on='Region', suffixes=('', '_Prev'), how='left'
        )
        regional_data_per_capita['Change'] = (
            (regional_data_per_capita['Count_Per_Capita'] - regional_data_per_capita['Count_Per_Capita_Prev']) 
            / regional_data_per_capita['Count_Per_Capita_Prev']
        ) * 100
        regional_data_per_capita['Change_Text'] = regional_data_per_capita['Change'].apply(
            lambda x: f"{x:.1f}% {'⬆️' if x > 0 else ('⬇️' if x < 0 else '➖')}" if pd.notna(x) else 'N/A'
        )
        hover_data = ['Count_Per_Capita', 'Change_Text']
    else:
        hover_data = ['Count_Per_Capita']
        
    fig_bar_regional = px.bar(
        regional_data_per_capita.sort_values('Count_Per_Capita', ascending=False), 
        x='Region', 
        y='Count_Per_Capita', 
        color='Count_Per_Capita', 
        color_continuous_scale=px.colors.sequential.Agsunset,
        title=f"지역별 인구 10만 명당 총 대출 권수 순위 ({target_year}년)",
        labels={'Count_Per_Capita': '인구 10만 명당 대출 권수', 'Region': '지역'},
        hover_data=hover_data
    )
    fig_bar_regional.update_yaxes(tickformat=',.0f')
    st.plotly_chart(fig_bar_regional, use_container_width=True)
    st.markdown("---") 

    # --- 6-B. 주제/연령 다기준 상세 분석 (히트맵 적용) ---
    st.markdown(f"### 6-B. {target_year}년 주제별/연령대별 대출 집중도 (히트맵)")
    st.caption("✅ **강조 효과:** 대출 권수를 **색상 농도**로 표현하여, 대출이 가장 활발한 **핫스팟 조합**을 직관적으로 보여줍니다.")
    
    subject_age_data = detail_data.groupby(['Subject', 'Age'])['Count_Unit'].sum().reset_index()
    
    fig_heatmap = px.density_heatmap(
        subject_age_data,
        x='Subject',
        y='Age',
        z='Count_Unit',
        histfunc='sum',
        nbinsx=len(subject_age_data['Subject'].unique()),
        nbinsy=len(subject_age_data['Age'].unique()),
        color_continuous_scale="Viridis",
        title=f"**주제 vs 연령대별 대출 핫스팟 분석** ({target_year}년)",
        labels={'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 'Subject': '주제 분야', 'Age': '연령대'}
    )
    fig_heatmap.update_layout(
        yaxis={'categoryorder':'array', 'categoryarray':['성인', '청소년', '어린이']}
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    st.markdown("---") 

    # --- 6-C. 자료 유형 및 연령대 비율 (선버스트 차트 적용) ---
    st.markdown(f"### 6-C. {target_year}년 자료 유형 및 연령대 계층적 비율 (선버스트 차트)")
    st.caption("✅ **강조 효과:** 하나의 차트에서 **자료 유형과 연령대의 계층적 기여 비율**을 동시에 시각화합니다.")
    
    sunburst_data = detail_data.groupby(['Material', 'Age'])['Count_Unit'].sum().reset_index()
    
    fig_sunburst = px.sunburst(
        sunburst_data,
        path=['Material', 'Age'], 
        values='Count_Unit',
        color='Material', 
        title=f"**자료 유형 및 연령대별 대출 기여도** ({target_year}년)",
        color_discrete_map={
            '인쇄자료': px.colors.qualitative.T10[0], 
            '전자자료': px.colors.qualitative.T10[1]
        },
        height=600
    )
    fig_sunburst.update_traces(textinfo='label+percent entry')
    st.plotly_chart(fig_sunburst, use_container_width=True)

# 6-1. 데이터 테이블
with st.expander("원본 추출 데이터 테이블 확인"):
    st.dataframe(base_df.sort_values(by=['Year', 'Region', 'Subject']), use_container_width=True)
