# -------------------------------------------------------------
# 6. 상세 분포 분석 (특정 연도)
# -------------------------------------------------------------
st.subheader("2. 상세 분포 분석 (특정 연도)")

# 6. 공통 연도 로컬 필터링 컨트롤러 (슬라이더 크기 개선)
with st.container():
    st.markdown("#### 📅 분석 기준 연도 선택")
    target_year = st.slider(
        "분석 대상 연도 선택", 
        2020, 2024, 2024, 
        key='detail_year_select_6',
        label_visibility="collapsed" # 레이블을 숨겨 크기를 확보합니다.
    )
detail_data = base_df[base_df['Year'] == target_year]

if not detail_data.empty:
    
    # --- 6-A. 지역별 순위 --- (인구 10만 명당 순위)
    st.markdown(f"### {target_year}년 지역별 대출 순위 (인구 10만 명당)")
    st.caption("✅ **의미 강화:** 절대 권수가 아닌 **인구 10만 명당 대출 권수**를 기준으로 순위를 매겨 지역별 비교의 의미를 높였습니다.")
    
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

    # --- 6-B. 주제/연령대/자료유형 대출 비교 (버블 차트 전환) ---
    st.markdown(f"### 🎯 {target_year}년 주제별/연령별/자료유형별 상세 분포 (버블 차트)")
    st.caption("✅ **분석 기준:** **X축(주제)**, **Y축(연령)**, **색상(자료유형)**, **크기(대출 권수)**")
    
    # 4가지 변수 기준으로 그룹화
    bubble_data = detail_data.groupby(['Subject', 'Age', 'Material'])['Count_Unit'].sum().reset_index()
    
    # 크기 변수 (Count_Unit)의 스케일을 조정 (버블 크기 조절을 위함)
    # Plotly에서 'size'를 지정할 때 크기 차이를 더 명확히 하기 위해 size_max를 사용하거나 값을 조정할 수 있습니다.
    bubble_data['Size_Scaled'] = (bubble_data['Count_Unit'] + 1) # 로그 스케일 등을 고려할 수 있으나, 일단 +1하여 0값을 회피
    
    fig_bubble = px.scatter(
        bubble_data,
        x='Subject',
        y='Age',
        size='Count_Unit', # 대출 권수를 버블 크기로
        color='Material', # 자료 유형을 색상으로
        hover_name='Subject',
        hover_data={'Count_Unit': True, 'Age': True, 'Material': True, 'Size_Scaled': False},
        title=f"{target_year}년 주제, 연령, 자료유형별 대출 상세 분포",
        labels={
            'Count_Unit': f'대출 권수 ({UNIT_LABEL})', 
            'Subject': '주제', 
            'Age': '연령대', 
            'Material': '자료 유형'
        },
        category_orders={
            "Age": ['어린이', '청소년', '성인'], 
            "Subject": subject_order
        },
        size_max=60, # 버블 최대 크기 설정
        color_discrete_sequence=px.colors.qualitative.Safe # 색상 팔레트 변경
    )

    # 마커 투명도 및 선 두께 설정
    fig_bubble.update_traces(mode='markers', marker=dict(opacity=0.8, line=dict(width=1, color='DarkSlateGrey')))
    fig_bubble.update_layout(height=600)

    st.plotly_chart(fig_bubble, use_container_width=True)
    st.markdown("---") 

    # --- 6-C. Pie Chart ---
    with st.container():
        st.markdown(f"### {target_year}년 자료 유형 비율 (Pie Chart)")
        st.caption("✅ **강화:** 상단의 연도 슬라이더에 따라 비율이 변경됩니다.")
        
        # 6-C 로컬 필터링 컨트롤러: 기준 선택 (기존 유지)
        pie_type = st.radio(
            "분석 기준 선택",
            ('자료 유형 (인쇄/전자)', '연령대'),
            key='pie_chart_criteria_6_C',
            horizontal=True
        )

        if pie_type == '자료 유형 (인쇄/전자)':
            pie_data = detail_data.groupby('Material')['Count_Unit'].sum().reset_index()
            names_col = 'Material'
            title = f"{target_year}년 자료 유형 (인쇄 vs 전자) 비율"
            colors = px.colors.sequential.RdBu
        else:
            pie_data = detail_data.groupby('Age')['Count_Unit'].sum().reset_index()
            names_col = 'Age'
            title = f"{target_year}년 연령대별 대출 권수 비율"
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
