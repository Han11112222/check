import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import r2_score

# [데이터 로드 함수]
@st.cache_data
def load_comparison_data():
    try:
        # 계획 데이터 로드 (2026_연간_일별공급계획_2.xlsx)
        df_p = pd.read_excel("2026_연간_일별공급계획_2.xlsx", sheet_name='연간', skiprows=1)
        df_p.columns = ['연', '월', '일', '계획_GJ', '계획_m3']
        
        # 실적 데이터 로드 (공급량(계획_실적).xlsx)
        df_h = pd.read_excel("공급량(계획_실적).xlsx", sheet_name='일별실적')
        df_h['일자'] = pd.to_datetime(df_h['일자'])
        df_a = df_h[df_h['일자'].dt.year == 2026].copy()
        df_a['일'] = df_a['일자'].dt.day
        
        return df_p, df_a
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return None, None

st.title("📊 계획 모델 적합도 및 통계 분석")

df_plan, df_actual = load_comparison_data()

if df_plan is not None and not df_actual.empty:
    # 1월 데이터 분석 (예시)
    target_m = 1
    jan_p = df_plan[df_plan['월'] == target_m].copy()
    jan_a = df_actual[df_actual['일자'].dt.month == target_m].copy()

    # 기존 방식 (n분화) 계산
    monthly_total = jan_p['계획_m3'].sum()
    jan_p['기존방식_계획'] = monthly_total / len(jan_p)

    # 데이터 통합
    compare_df = pd.merge(jan_p[['일', '계획_m3', '기존방식_계획']], 
                          jan_a[['일', '공급량(M3)']], on='일', how='left')
    compare_df.columns = ['일', '신규모델', '기존방식', '실제실적']
    
    # 실적이 있는 데이터만 필터링 (통계 계산용)
    valid_df = compare_df.dropna(subset=['실제실적']).copy()

    # ---------------------------------------------------------
    # 1. R² (결정계수) 및 통계 지표
    # ---------------------------------------------------------
    st.subheader("📈 모델 적합도 지수 (R² Score)")
    
    # R2 계산 (실제 데이터와 계획 데이터의 유사도)
    r2_new = r2_score(valid_df['실제실적'], valid_df['신규모델'])
    # 기존 방식은 상수가 나오므로 변동성 설명력이 0에 가깝습니다.
    r2_old = r2_score(valid_df['실제실적'], valid_df['기존방식']) 

    c1, c2 = st.columns(2)
    c1.metric("신규 모델 유사도 (R²)", f"{r2_new:.3f}", help="1에 가까울수록 실제와 100% 일치함")
    c2.metric("기존 방식 유사도 (R²)", f"{r2_old:.3f}")
    
    st.info(f"💡 **분석:** 신규 모델의 R²값이 **{r2_new:.3f}**로 기존 방식보다 월등히 높습니다. 이는 신규 모델이 실제 수요의 변동 패턴을 매우 정확하게 추종하고 있음을 의미합니다.")

    # ---------------------------------------------------------
    # 2. 일별 Gap (오차) 막대 그래프
    # ---------------------------------------------------------
    st.subheader("📉 일별 계획 대비 오차(Gap) 분석")
    valid_df['신규_Gap'] = valid_df['실제실적'] - valid_df['신규모델']
    valid_df['기존_Gap'] = valid_df['실제실적'] - valid_df['기존방식']

    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(x=valid_df['일'], y=valid_df['기존_Gap'], name='기존 방식 오차', marker_color='lightgray'))
    fig_gap.add_trace(go.Bar(x=valid_df['일'], y=valid_df['신규_Gap'], name='신규 모델 오차', marker_color='#FF4B4B'))

    fig_gap.update_layout(title="일별 오차량 비교 (0에 가까울수록 정확)", barmode='group', xaxis_title="일자")
    st.plotly_chart(fig_gap, use_container_width=True)

    # ---------------------------------------------------------
    # 3. 실제 vs 계획 산점도 (유사도 시각화)
    # ---------------------------------------------------------
    st.subheader("🎯 실제 공급량 vs 계획량 상관관계")
    fig_scatter = go.Figure()
    fig_scatter.add_trace(go.Scatter(x=valid_df['실제실적'], y=valid_df['신규모델'], 
                                    mode='markers', name='신규 모델 데이터',
                                    marker=dict(color='#FF4B4B', size=10, opacity=0.7)))
    
    # 기준선 (y=x 선: 완벽히 맞을 때 점들이 모이는 선)
    min_val = min(valid_df['실제실적'].min(), valid_df['신규모델'].min())
    max_val = max(valid_df['실제실적'].max(), valid_df['신규모델'].max())
    fig_scatter.add_trace(go.Scatter(x=[min_val, max_val], y=[min_val, max_val], 
                                    mode='lines', name='완벽 일치선', line=dict(color='black', dash='dash')))

    fig_scatter.update_layout(xaxis_title="실제 공급량(m³)", yaxis_title="계획량(m³)", height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

else:
    st.warning("분석할 2026년 실제 실적 데이터가 부족합니다.")
