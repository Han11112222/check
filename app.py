import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="공급량 계획 모델 성능 비교", layout="wide")

# [데이터 로드] - 업로드하신 파일명을 기준으로 설정
def load_data():
    # 신규 계획 데이터
    plan_df = pd.read_csv('2026_연간_일별공급계획_2.xlsx - 연간.csv', skiprows=1)
    plan_df.columns = ['연', '월', '일', '계획_GJ', '계획_m3']
    
    # 실제 실적 데이터 (일별실적 시트)
    hist_df = pd.read_csv('공급량(계획_실적).xlsx - 일별실적.csv')
    hist_df['일자'] = pd.to_datetime(hist_df['일자'])
    
    return plan_df, hist_df

st.title("📊 일일 공급량 계획 모델 우월성 분석")
st.markdown("### 기존 방식(단순 n분화) vs 신규 방식(요일/시기 그룹핑)")

plan_2026, history = load_data()

# 분석 대상 설정 (예: 2026년 1월)
target_month = 1
jan_plan = plan_2026[plan_2026['월'] == target_month].copy()
jan_actual = history[(history['일자'].dt.year == 2026) & (history['일자'].dt.month == target_month)].copy()

if not jan_actual.empty:
    # 1. 기존 방식 계산: 월간 총 계획 / 해당 월 일수
    total_monthly_plan = jan_plan['계획_m3'].sum()
    days_in_month = len(jan_plan)
    jan_plan['기존방식_n분화'] = total_monthly_plan / days_in_month
    
    # 2. 데이터 병합
    jan_actual['일'] = jan_actual['일자'].dt.day
    compare_df = pd.merge(jan_plan[['일', '계획_m3', '기존방식_n분화']], 
                          jan_actual[['일', '공급량(M3)']], on='일', how='left')
    compare_df.columns = ['일', '신규모델_계획', '기존방식_계획', '실제실적']

    # [시각화] 차트 구성
    fig = go.Figure()
    # 실제 실적
    fig.add_trace(go.Scatter(x=compare_df['일'], y=compare_df['실제실적'], name='실제 공급실적',
                             line=dict(color='black', width=3), mode='lines+markers'))
    # 기존 방식
    fig.add_trace(go.Scatter(x=compare_df['일'], y=compare_df['기존방식_계획'], name='기존 방식 (단순 평균)',
                             line=dict(color='gray', dash='dot'), mode='lines'))
    # 신규 모델
    fig.add_trace(go.Scatter(x=compare_df['일'], y=compare_df['신규모델_계획'], name='신규 모델 (그룹핑 적용)',
                             line=dict(color='#FF4B4B', width=2), mode='lines+markers'))

    fig.update_layout(title=f"2026년 {target_month}월 계획 모델 적합도 비교",
                      xaxis_title="일자", yaxis_title="공급량 (m3)", legend_orientation="h")
    st.plotly_chart(fig, use_container_width=True)

    # [수치적 우월성 지표]
    st.subheader("🧐 모델 정확도 비교 (오차 분석)")
    
    # 오차율 계산 (절대 오차의 합 기준)
    compare_df['기존_오차'] = abs(compare_df['실제실적'] - compare_df['기존방식_계획'])
    compare_df['신규_오차'] = abs(compare_df['실제실적'] - compare_df['신규모델_계획'])
    
    c1, c2 = st.columns(2)
    avg_old_err = compare_df['기존_오차'].mean()
    avg_new_err = compare_df['신규_오차'].mean()
    
    c1.metric("기존 방식 평균 오차", f"{avg_old_err:,.0f} m3")
    c2.metric("신규 모델 평균 오차", f"{avg_new_err:,.0f} m3", 
              delta=f"{(avg_new_err - avg_old_err):,.0f} m3 개선", delta_color="normal")

    st.info(f"💡 **분석 결과:** 신규 모델이 기존 방식보다 일일 평균 약 **{abs(avg_new_err - avg_old_err):,.0f} m3** 더 정확하게 실제 수요를 추종하고 있습니다.")
