import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import r2_score

# [데이터 로드] - 파일 헤더 및 구조 최적화
@st.cache_data
def load_and_clean_data():
    try:
        # 1. 계획 데이터 로드 (2026_연간_일별공급계획_2.xlsx)
        # 로컬 환경이나 스트림릿 클라우드에서 파일명을 정확히 매칭해야 합니다.
        df_p = pd.read_csv("2026_연간_일별공급계획_2.xlsx - 연간.csv", skiprows=1)
        df_p.columns = ['연', '월', '일', '계획_GJ', '계획_m3']
        df_p = df_p.dropna(subset=['일']) # 빈 줄 제거
        
        # 2. 실적 데이터 로드 (공급량(계획_실적).xlsx)
        df_h = pd.read_csv("공급량(계획_실적).xlsx - 일별실적.csv")
        df_h['일자'] = pd.to_datetime(df_h['일자'], errors='coerce')
        # 2026년 데이터 중 실적이 있는 날만 추출
        df_a = df_h[(df_h['일자'].dt.year == 2026) & (df_h['공급량(M3)'].notna())].copy()
        df_a['일'] = df_a['일자'].dt.day
        
        return df_p, df_a
    except Exception as e:
        st.error(f"데이터 파일 확인 필요: {e}")
        return None, None

st.title("📊 공급량 예측 모델 성능 및 통계 검증")

df_plan, df_actual = load_and_clean_data()

if df_plan is not None and not df_actual.empty:
    target_m = 1 # 분석 기준월 (1월)
    jan_p = df_plan[df_plan['월'] == target_m].copy()
    jan_a = df_actual[df_actual['일자'].dt.month == target_m].copy()

    # 기존 방식(n분화) 가상 생성: 한 달 총 계획을 일수로 균등 배분
    total_plan = jan_p['계획_m3'].sum()
    jan_p['기존방식'] = total_plan / len(jan_p)

    # 데이터 병합 (일자 기준)
    compare_df = pd.merge(jan_p[['일', '계획_m3', '기존방식']], 
                          jan_a[['일', '공급량(M3)']], on='일', how='inner')
    compare_df.rename(columns={'계획_m3': '신규모델', '공급량(M3)': '실제실적'}, inplace=True)

    if not compare_df.empty:
        # ---------------------------------------------------------
        # 1. R² (결정계수) 분석
        # ---------------------------------------------------------
        st.subheader("📈 모델 적합도 지수 (R² Score)")
        
        # 신규 모델과 기존 방식의 R2 계산
        # r2_score는 (실제값, 예측값) 순서로 넣습니다.
        r2_new = r2_score(compare_df['실제실적'], compare_df['신규모델'])
        r2_old = r2_score(compare_df['실제실적'], compare_df['기존방식'])

        c1, c2 = st.columns(2)
        c1.metric("신규 모델 유사도 (R²)", f"{max(0, r2_new):.3f}", help="1에 가까울수록 실제와 유사")
        c2.metric("기존 방식 유사도 (R²)", f"{max(0, r2_old):.3f}")
        
        st.info(f"💡 **통계적 의미:** 신규 모델의 R²값이 **{r2_new:.3f}**로 도출되었습니다. 이는 요일/주차별 가중치 로직이 실제 수요 변화의 약 **{r2_new*100:.1f}%**를 정확히 설명하고 있음을 뜻합니다.")

        # ---------------------------------------------------------
        # 2. 일별 Gap (오차) 분석
        # ---------------------------------------------------------
        st.subheader("📉 일별 계획 대비 오차(Gap) 비교")
        compare_df['신규_Gap'] = compare_df['실제실적'] - compare_df['신규모델']
        compare_df['기존_Gap'] = compare_df['실제실적'] - compare_df['기존방식']

        fig_gap = go.Figure()
        fig_gap.add_trace(go.Bar(x=compare_df['일'], y=compare_df['기존_Gap'], name='기존 방식 오차', marker_color='lightgray'))
        fig_gap.add_trace(go.Bar(x=compare_df['일'], y=compare_df['신규_Gap'], name='신규 모델 오차', marker_color='#FF4B4B'))

        fig_gap.update_layout(title="오차가 0에 가까울수록 정밀한 모델입니다 (실제-계획)", barmode='group', xaxis_title="일자")
        st.plotly_chart(fig_gap, use_container_width=True)

        # ---------------------------------------------------------
        # 3. 산점도 (실제 vs 예측)
        # ---------------------------------------------------------
        st.subheader("🎯 예측 정밀도 분포 (산점도)")
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(x=compare_df['실제실적'], y=compare_df['신규모델'], 
                                        mode='markers', name='신규 모델', marker=dict(color='#FF4B4B', size=10)))
        
        # 완벽 일치선 (y=x)
        limit_val = [compare_df[['실제실적', '신규모델']].min().min(), compare_df[['실제실적', '신규모델']].max().max()]
        fig_scatter.add_trace(go.Scatter(x=limit_val, y=limit_val, mode='lines', name='완벽 일치', line=dict(color='black', dash='dash')))

        fig_scatter.update_layout(title="점들이 점선에 모여있을수록 정확도가 높습니다", xaxis_title="실제 공급량", yaxis_title="계획량")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("비교 분석을 위한 실적 데이터가 부족합니다.")
else:
    st.info("데이터 로드 중입니다. 엑셀 파일명(CSV 변환 여부 등)을 확인해주세요.")
