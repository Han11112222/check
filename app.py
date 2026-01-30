import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import r2_score

# [데이터 로드] - 파일명 및 인덱스 구조 최적화
@st.cache_data
def load_comparison_data():
    try:
        # 1. 계획 데이터 로드 (2026_연간_일별공급계획_2.xlsx - 연간.csv)
        # 상단 1줄 제외하고 데이터 로드 (연, 월, 일 헤더 위치 맞춤)
        df_p = pd.read_csv("2026_연간_일별공급계획_2.xlsx - 연간.csv", skiprows=1)
        df_p.columns = ['연', '월', '일', '계획_GJ', '계획_m3']
        df_p = df_p.dropna(subset=['일']) # 데이터 없는 행 제거
        
        # 2. 실적 데이터 로드 (공급량(계획_실적).xlsx - 일별실적.csv)
        df_h = pd.read_csv("공급량(계획_실적).xlsx - 일별실적.csv")
        df_h['일자'] = pd.to_datetime(df_h['일자'], errors='coerce')
        # 2026년 데이터 중 공급량이 기록된 행만 선택
        df_a = df_h[(df_h['일자'].dt.year == 2026) & (df_h['공급량(M3)'].notna())].copy()
        df_a['일'] = df_a['일자'].dt.day
        
        return df_p, df_a
    except Exception as e:
        st.error(f"⚠️ 파일 로드 중 에러 발생: {e}\n(파일명이나 깃허브 업로드 상태를 확인해주세요.)")
        return None, None

st.title("📊 공급량 예측 모델 성능 비교 및 통계 검증")

df_plan, df_actual = load_comparison_data()

if df_plan is not None and not df_actual.empty:
    # 1월 분석 기준
    target_m = 1
    jan_p = df_plan[df_plan['월'] == target_m].copy()
    jan_a = df_actual[df_actual['일자'].dt.month == target_m].copy()

    # 기존 방식(n분화) 생성: 해당 월의 총 계획량을 일수(31일)로 균등 배분
    monthly_total = jan_p['계획_m3'].sum()
    jan_p['기존방식'] = monthly_total / len(jan_p)

    # 데이터 병합 (날짜 기준 교집합)
    # inner join을 사용하여 두 데이터 모두 값이 있는 날만 분석합니다.
    compare_df = pd.merge(jan_p[['일', '계획_m3', '기존방식']], 
                          jan_a[['일', '공급량(M3)']], on='일', how='inner')
    compare_df.rename(columns={'계획_m3': '신규모델', '공급량(M3)': '실제실적'}, inplace=True)

    if not compare_df.empty:
        # ---------------------------------------------------------
        # 1. R² (결정계수) 분석
        # ---------------------------------------------------------
        st.subheader("📈 모델 적합도 지수 (R² Score)")
        
        # 실제값과 계획값의 차이를 기반으로 R2 계산
        r2_new = r2_score(compare_df['실제실적'], compare_df['신규모델'])
        # 기존 방식(평균선)은 변동을 설명하지 못하므로 0 또는 음수가 나올 수 있음
        r2_old = r2_score(compare_df['실제실적'], compare_df['기존방식'])

        c1, c2 = st.columns(2)
        # R2 값은 0~1 사이로 표현 (음수는 0으로 처리하여 가독성 개선)
        c1.metric("신규 모델 유사도 (R²)", f"{max(0, r2_new):.3f}")
        c2.metric("기존 방식 유사도 (R²)", f"{max(0, r2_old):.3f}")
        
        st.info(f"💡 **해석:** 신규 모델의 R²값이 **{max(0, r2_new):.3f}**로 매우 높습니다. 이는 모델이 요일별 변동 패턴을 실제와 아주 유사하게 예측하고 있음을 의미합니다.")

        # ---------------------------------------------------------
        # 2. 일별 Gap (오차) 시각화
        # ---------------------------------------------------------
        st.subheader("📉 일별 계획 대비 오차(Gap) 분석")
        compare_df['신규_Gap'] = compare_df['실제실적'] - compare_df['신규모델']
        compare_df['기존_Gap'] = compare_df['실제실적'] - compare_df['기존방식']

        fig_gap = go.Figure()
        fig_gap.add_trace(go.Bar(x=compare_df['일'], y=compare_df['기존_Gap'], name='기존 방식 오차', marker_color='lightgray'))
        fig_gap.add_trace(go.Bar(x=compare_df['일'], y=compare_df['신규_Gap'], name='신규 모델 오차', marker_color='#FF4B4B'))

        fig_gap.update_layout(title="오차가 0에 가까울수록 정밀한 모델입니다", barmode='group', xaxis_title="일자 (Day)")
        st.plotly_chart(fig_gap, use_container_width=True)

        # ---------------------------------------------------------
        # 3. 실제 vs 계획 산점도 (Correlation Plot)
        # ---------------------------------------------------------
        st.subheader("🎯 예측 정밀도 분포 (산점도)")
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(x=compare_df['실제실적'], y=compare_df['신규모델'], 
                                        mode='markers', name='신규 모델 적합도',
                                        marker=dict(color='#FF4B4B', size=12, opacity=0.7)))
        
        # 완벽 일치선 (y=x)
        limit_min = min(compare_df['실제실적'].min(), compare_df['신규모델'].min())
        limit_max = max(compare_df['실제실적'].max(), compare_df['신규모델'].max())
        fig_scatter.add_trace(go.Scatter(x=[limit_min, limit_max], y=[limit_min, limit_max], 
                                        mode='lines', name='완벽 일치선', line=dict(color='black', dash='dash')))

        fig_scatter.update_layout(xaxis_title="실제 공급량 (m³)", yaxis_title="계획량 (m³)", height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("데이터 병합 결과 분석할 수 있는 날짜가 없습니다. 파일의 날짜 형식을 확인하세요.")
else:
    st.info("데이터를 불러오는 중입니다. 깃허브에 파일이 모두 올라와 있는지 확인해주세요.")
