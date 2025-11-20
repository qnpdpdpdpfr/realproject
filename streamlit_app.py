import pandas as pd
import os
import re
import sys
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. 설정 및 상수 (원본 코드와 동일)
# -----------------------------------------------------------------------------

# 단위 설정: 10만 권 (100,000)
UNIT_DIVISOR = 100000

# 2020~2024년 지역별 인구수 (단위: 만 명, 통계청 자료 기반 추정치) - 원본과 동일
REGION_POPULATION = {
    '서울': {2020: 980, 2021: 960, 2022: 950, 2023: 940, 2024: 935},
    '부산': {2020: 335, 2021: 330, 2022: 325, 2023: 320, 2024: 315},
    # ... 나머지 지역 데이터 생략 ...
    '제주': {2020: 67, 2021: 67, 2022: 67, 2023: 67, 2024: 67}
}


# -----------------------------------------------------------------------------
# 2. 데이터 로드 및 전처리 함수 (디버깅 로그 추가)
# -----------------------------------------------------------------------------

def load_and_process_data():
    """
    엑셀 파일을 로드하고 전처리하는 함수. 디버깅을 위해 진행 상태를 출력합니다.
    """
    # 원본 코드의 파일 목록을 그대로 사용
    files = [
        {'year': 2020, 'file': "2021('20년실적)도서관별통계입력데이터_공공도서관_(최종)_23.12.07..xlsx"},
        {'year': 2021, 'file': "2022년('21년 실적) 공공도서관 통계데이터 최종_23.12.06..xlsx"},
        {'year': 2022, 'file': "2023년('22년 실적) 공공도서관 입력데이터_최종.xlsx"},
        {'year': 2023, 'file': "2024년('23년 실적) 공공도서관 통계데이터_업로드용(2024.08.06).xlsx"},
        {'year': 2024, 'file': "2025년(_24년 실적) 공공도서관 통계조사 결과(250729).xlsx"}
    ]
    data_dir = "data" # 파일이 저장된 폴더 (Streamlit 앱과 동일해야 함)
    all_data = []
    target_subjects = ['총류', '철학', '종교', '사회과학', '순수과학', '기술과학', '예술', '언어', '문학', '역사']
    target_ages = ['어린이', '청소년', '성인']

    print("--- 데이터 로딩 디버깅 시작 ---")
    
    for item in files:
        year = item['year']
        file_name = item['file']
        file_path = os.path.join(data_dir, file_name)
        
        print(f"\n[DEBUG] {datetime.now().strftime('%H:%M:%S')} - {year}년 파일 로드 시도: {file_path}")
        
        # 1. 파일 존재 여부 확인
        if not os.path.exists(file_path):
            print(f"[ERROR] 파일이 존재하지 않아 건너뜁니다: {file_path}")
            continue

        try:
            # 2. 엑셀 파일 로드 및 초기 필터링 (원본 로직)
            if year >= 2023:
                # 2023년 이후 파일은 헤더 구조가 다름
                print(f"[INFO] {year}년 파일: 헤더(1) 설정 및 첫 2행 건너뛰기 (index 0, 1) 적용")
                df = pd.read_excel(file_path, engine='openpyxl', header=1)
                df = df.iloc[2:].reset_index(drop=True)
            else:
                print(f"[INFO] {year}년 파일: 헤더(0) 설정 및 첫 1행 건너뛰기 (index 0) 적용")
                df = pd.read_excel(file_path, engine='openpyxl', header=0)
                df = df.iloc[1:].reset_index(drop=True)

            print(f"[INFO] {year}년 파일 로드 성공. 초기 데이터 크기: {df.shape}. 컬럼 수: {len(df.columns)}")
            
            # 지역명 추출 (4번째 컬럼 가정 - 인덱스 3)
            # 파일 구조 변경의 주된 원인이 될 수 있는 부분!
            df['Region_Fixed'] = df.iloc[:, 3].astype(str).str.strip()
            df = df[df['Region_Fixed'] != 'nan']
            print(f"[INFO] {year}년 유효 지역 데이터 필터링 후 크기: {df.shape}")
            
        except Exception as e:
            # 3. 파일 로드 또는 초기 데이터프레임 처리 중 오류 발생
            print(f"\n[FATAL ERROR] {year}년 파일 ({file_name}) 로드/초기 처리 중 치명적인 오류 발생:")
            print(f"    오류 내용: {type(e).__name__}: {e}")
            print("    -> 이 파일을 건너뛰고 다음 파일로 진행합니다.")
            continue # 이 파일은 건너뜀

        # 4. 데이터 추출 및 집계 로직 (원본 로직)
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
                # 데이터 변환 및 그룹화
                numeric_values = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
                # 'Region' 컬럼이 없는 경우 오류 방지 (df['Region_Fixed']는 위에서 생성됨)
                if 'Region_Fixed' not in df.columns:
                    print(f"[FATAL ERROR] {year}년 - 'Region_Fixed' 컬럼이 없어 추출 중단.")
                    break 

                temp_df = pd.DataFrame({'Region': df['Region_Fixed'], 'Value': numeric_values})
                region_sums = temp_df.groupby('Region')['Value'].sum()

                for region_name, val in region_sums.items():
                    if val > 0:
                        extracted_rows.append({
                            'Year': year,
                            'Region': region_name,
                            'Material': mat_type,
                            'Subject': subject,
                            'Age': age,
                            'Count': val
                        })
        
        # 5. 연도별 데이터프레임 통합
        if extracted_rows:
            year_df = pd.DataFrame(extracted_rows)
            all_data.append(year_df)
            print(f"[SUCCESS] {year}년 데이터 추출 및 전처리 완료. 추출된 총 대출 건수: {year_df['Count'].sum():,.0f} 권")
        else:
            print(f"[WARNING] {year}년 파일에서 최종 추출된 유효한 행이 0개입니다. (컬럼 매칭 실패 가능성 높음)")


    if not all_data: 
        print("\n[최종 실패] 모든 파일에서 데이터 로드 실패. 빈 데이터프레임 반환.")
        return pd.DataFrame()
        
    final_df = pd.concat(all_data, ignore_index=True)
    
    # 6. 최종 계산 (단위 변환 및 인구당 계산)
    final_df['Count_Unit'] = final_df['Count'] / UNIT_DIVISOR
    
    def calculate_per_capita(row):
        year = row['Year']
        region = row['Region']
        count = row['Count']
        
        population_in_10k = REGION_POPULATION.get(region, {}).get(year, 0)
        
        # 인구수 (만 명 단위) * 10000 = 실제 인구수
        population = population_in_10k * 10000
        
        # 인구 10만 명당 대출 권수 = (총 대출 권수 / 실제 인구수) * 100,000
        return count / population * 100000 if population > 0 else 0
        
    final_df['Count_Per_Capita'] = final_df.apply(calculate_per_capita, axis=1)

    print("\n--- 데이터 로딩 디버깅 종료 (성공적으로 일부/전체 데이터 로드) ---")
    return final_df


# -----------------------------------------------------------------------------
# 3. 메인 실행 블록
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    
    print("\n==================================================")
    print("      Streamlit 데이터 로드 디버거 (Load Only)     ")
    print("==================================================")
    print("1. 'data' 폴더와 엑셀 파일이 현재 실행 위치에 있는지 확인하세요.")
    print("2. 로그를 확인하여 어떤 파일에서 오류가 발생하는지 추적하세요.")
    print("3. 'FATAL ERROR'가 발생했다면 해당 파일의 구조(헤더, 4번째 컬럼)를 확인해야 합니다.")
    print("==================================================")

    try:
        df_result = load_and_process_data()

        if df_result.empty:
            print("\n[최종 결과] 최종 데이터프레임이 비어있습니다. 데이터를 로드하지 못했습니다.")
        else:
            print("\n[최종 결과] 데이터 로드 및 전처리 성공:")
            print(f"  총 데이터 크기: {df_result.shape}")
            print(f"  통합된 연도: {sorted(df_result['Year'].unique())}")
            print("  데이터프레임 미리보기 (Head):")
            # 디버깅 용도로 전체 컬럼 출력 옵션 일시 설정
            with pd.option_context('display.max_rows', None, 'display.max_columns', None):
                print(df_result.head(10))
            
    except Exception as final_e:
        print(f"\n[최상위 실패] 디버거 실행 중 예상치 못한 최상위 오류가 발생했습니다.")
        print(f"    오류 내용: {type(final_e).__name__}: {final_e}", file=sys.stderr)
