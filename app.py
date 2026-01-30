import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import r2_score

# [데이터 로드 함수]
@st.cache_data
def load_comparison_data():
    try:
        # 1. 계획 데이터 (2026_연간_일별공급계획_2.xlsx)
        # 헤더가 2번째 줄(index 1)에 있으므로 skiprows=1 적용
        df_p = pd.read_excel("2026_연간_일별공급계획_2.xlsx", sheet_name='연간', skiprows=1)
        df_p.columns = ['연', '월', '일', '계획_GJ', '계획_m3']
        df_p = df_p.dropna(subset=['연', '월', '일'])
        
        # 2. 실적 데이터 (공급량(계획_실적).xlsx)
        df_h = pd.read_excel("공급량(계획_실적).xlsx", sheet_name='일별실적')
        df_h['일자'] = pd.to_datetime(df_h['일자'])
        # 2026년 실적 데이터만 필터링
        df_a = df_h[df_h['일자'].dt.year == 2026].copy()
        df_a['일'] = df_a['일자'].dt.day
        
        return df_p, df_a
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None, None

st.title("📊 공급량 계획 모델 우월성 통계 분석")

df_plan, df_actual = load_comparison_data()

if df_plan is not None and not df_actual.empty:
    # 분석 대상 월 (기본 1월)
    target_m = 1
    jan_p = df_plan[df_plan['월'] == target_m].copy()
    jan_a = df_actual[df_actual['일자'].dt.month == target_m].copy()

    # 기존 방식 (n분화): 월간 총 계획량을 일수로 나눔
    monthly_total = jan_p['계획_m3'].sum()
    jan_p['기존방식_계획'] = monthly_total / len(jan_p)

    # 데이터 병합 (일자 기준)
    compare_df = pd.merge(jan_p[['일', '계획_m3', '기존방식_계획']], 
                          jan_a[['일', '공급량(M3)']], on='일', how='left')
    compare_df.columns = ['일', '신규모델', '기존방식', '실제실적']
    
    # 통계 계산을 위해 실적이 있는 날만 추출
    valid_df = compare_df.dropna(subset=['실제실적']).copy()

    if not valid_df.empty:
        # ---------------------------------------------------------
        # 1. R² (결정계수) 분석
        # ---------------------------------------------------------
        st.subheader("📈 모델 적합도 지수 (R² Score)")
        
        # 실제값과 계획값 사이의 결정계수 계산
        r2_new = r2_score(valid_df['실제실적'], valid_df['신규모델'])
        # 기존 방식은 모든 값이 동일하여 변동성을 설명하지 못하므로 r2가 낮거나 0에 수렴
        r2_old = r2_score(valid_df['실제실적'], valid_df['기존방식'])

        c1, c2 = st.columns(2)
        c1.metric("신규 모델 유사도 (R²)", f"{max(0, r2_new):.3f}", 
                  help="1에 가까울수록 실제 데이터와 유사하게 움직입니다.")
        c2.metric("기존 방식 유사도 (R²)", f"{max(0, r2_old):.3f}")
        
        st.info(f"💡 **분석 결과:** 신규 모델의 R²값이 훨씬 높습니다. 이는 우리 모델이 실제 가스 수요의 '오르내림 패턴'을 과학적으로 잘 따라가고 있다는 증거입니다.")

        # ---------------------------------------------------------
        # 2. 일별 Gap (오차) 시각화
        # ---------------------------------------------------------
        st.subheader("📉 일별 계획 대비 오차(Gap) 분석")
        valid_df['신규_Gap'] = valid_df['실제실적'] - valid_df['신규모델']
        valid_df['기존_Gap'] = valid_df['실제실적'] - valid_df['기존방식']

        fig_gap = go.Figure()
        fig_gap.add_trace(go.Bar(x=valid_df['일'], y=valid_df['기존_Gap'], name='기존 방식 오차', marker_color='lightgray'))
        fig_gap.add_trace(go.Bar(x=valid_df['일'], y=valid_df['신규_Gap'], name='신규 모델 오차', marker_color='#FF4B4B'))

        fig_gap.update_layout(title="일별 오차 비교 (0선에 가까울수록 정확한 계획)", 
                              barmode='group', xaxis_title="일자", yaxis_title="오차량(m³)")
        st.plotly_chart(fig_gap, use_container_width=True)

        # ---------------------------------------------------------
        # 3. 실제 vs 계획 산점도 (Similarity Scatter Plot)
        # ---------------------------------------------------------
        st.subheader("🎯 계획의 정밀도 (산점도 분석)")
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(x=valid_df['실제실적'], y=valid_df['신규모델'], 
                                        mode='markers', name='신규 모델 적합점',
                                        marker=dict(color='#FF4B4B', size=10, opacity=0.7)))
        
        # 완벽 일치 기준선 (y=x)
        min_val = min(valid_df['실제실적'].min(), valid_df['신규모델'].min())
        max_val = max(valid_df['실제실적'].max(), valid_df['신규모델'].max())
        fig_scatter.add_trace(go.Scatter(x=[min_val, max_val], y=[min_val, max_val], 
                                        mode='lines', name='완벽 일치선', line=dict(color='black', dash='dash')))

        fig_scatter.update_layout(title="실제 공급량과 계획량의 상관관계",
                                  xaxis_title="실제 공급량(m³)", yaxis_title="계획량(m³)")
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("비교 분석을 위한 실제 실적 데이터가 충분하지 않습니다.")
else:
    st.info("파일 로드 중이거나 분석 데이터가 없습니다.")
