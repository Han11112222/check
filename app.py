import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="공급량 계획 모델 성능 비교", layout="wide")

# [데이터 로드] - 파일명 및 컬럼명을 업로드하신 파일 기준으로 정확히 맞춤
@st.cache_data
def load_comparison_data():
    # 1. 신규 계획 데이터 (2026_연간_일별공급계획_2.xlsx)
    plan_path = "2026_연간_일별공급계획_2.xlsx"
    try:
        # '연간' 시트에서 데이터 로드 (첫 번째 행은 MJ/Nm3 정보이므로 건너뜀)
        df_plan = pd.read_excel(plan_path, sheet_name='연간', skiprows=1)
        df_plan.columns = ['연', '월', '일', '계획_GJ', '계획_m3']
        df_plan = df_plan.dropna(subset=['연', '월', '일'])
    except Exception as e:
        st.error(f"계획 파일 로드 실패: {e}")
        return None, None

    # 2. 실제 실적 데이터 (공급량(계획_실적).xlsx)
    hist_path = "공급량(계획_실적).xlsx"
    try:
        # '일별실적' 시트에서 데이터 로드
        df_hist = pd.read_excel(hist_path, sheet_name='일별실적')
        df_hist['일자'] = pd.to_datetime(df_hist['일자'])
        # 비교를 위해 2026년 데이터만 추출
        df_actual = df_hist[df_hist['일자'].dt.year == 2026].copy()
    except Exception as e:
        st.error(f"실적 파일 로드 실패: {e}")
        return df_plan, None

    return df_plan, df_actual

st.title("📊 일일 공급량 계획 모델 우월성 분석")
st.markdown("### 기존 방식(단순 n분화) vs 신규 방식(요일/주별 그룹핑)")

df_plan, df_actual = load_comparison_data()

if df_plan is not None and df_actual is not None:
    # 분석 대상 월 선택 (기본 1월)
    target_month = st.selectbox("분석 대상 월 선택", sorted(df_plan['월'].unique().astype(int)), index=0)
    
    # 해당 월의 데이터 필터링
    jan_plan = df_plan[df_plan['월'] == target_month].copy()
    jan_actual = df_actual[df_actual['일자'].dt.month == target_month].copy()
    jan_actual['일'] = jan_actual['일자'].dt.day

    if not jan_actual.empty:
        # 1. 기존 방식 계산: 월간 총 계획 / 해당 월 일수 (n분화)
        total_monthly_plan = jan_plan['계획_m3'].sum()
        days_in_month = len(jan_plan)
        jan_plan['기존방식_계획'] = total_monthly_plan / days_in_month
        
        # 2. 데이터 병합 (신규모델 vs 기존방식 vs 실제실적)
        compare_df = pd.merge(jan_plan[['일', '계획_m3', '기존방식_계획']], 
                              jan_actual[['일', '공급량(M3)']], on='일', how='left')
        compare_df.columns = ['일', '신규모델_계획', '기존방식_계획', '실제실적']

        # [시각화] 차트 구성
        fig = go.Figure()
        # 실제 실적 (검정색 굵은 선)
        fig.add_trace(go.Scatter(x=compare_df['일'], y=compare_df['실제실적'], name='실제 공급실적',
                                 line=dict(color='black', width=3), mode='lines+markers'))
        # 기존 방식 (회색 점선 - 변화 없음)
        fig.add_trace(go.Scatter(x=compare_df['일'], y=compare_df['기존방식_계획'], name='기존 방식 (단순 n분화)',
                                 line=dict(color='gray', dash='dot'), mode='lines'))
        # 신규 모델 (빨간색 선 - 요일/주별 패턴 반영)
        fig.add_trace(go.Scatter(x=compare_df['일'], y=compare_df['신규모델_계획'], name='신규 모델 (그룹핑 적용)',
                                 line=dict(color='#FF4B4B', width=2), mode='lines+markers'))

        fig.update_layout(title=f"2026년 {target_month}월 계획 모델 적합도 비교",
                          xaxis_title="일자 (Day)", yaxis_title="공급량 (m³)", 
                          legend_orientation="h", height=600)
        st.plotly_chart(fig, use_container_width=True)

        # [수치적 우월성 증명]
        st.subheader("🧐 왜 신규 모델이 더 우월한가? (오차 분석)")
        
        # 실제 데이터가 있는 날만 계산
        valid_df = compare_df.dropna(subset=['실제실적']).copy()
        valid_df['기존_오차'] = abs(valid_df['실제실적'] - valid_df['기존방식_계획'])
        valid_df['신규_오차'] = abs(valid_df['실제실적'] - valid_df['신규모델_계획'])
        
        c1, c2, c3 = st.columns(3)
        avg_old_err = valid_df['기존_오차'].mean()
        avg_new_err = valid_df['신규_오차'].mean()
        improvement = ((avg_old_err - avg_new_err) / avg_old_err) * 100
        
        c1.metric("기존 방식 일평균 오차", f"{avg_old_err:,.0f} m³")
        c2.metric("신규 모델 일평균 오차", f"{avg_new_err:,.0f} m³")
        c3.metric("예측 정확도 개선율", f"{improvement:.1f}%", delta=f"{improvement:.1f}% 상승")

        st.success(f"💡 **분석 결과:** 신규 모델은 실제 수요의 요일별/주별 상·하락 패턴을 **{improvement:.1f}%** 더 정확하게 추종하여 공급 안정성을 확보합니다.")
    else:
        st.warning(f"선택하신 {target_month}월의 실제 실적 데이터가 아직 입력되지 않았습니다.")
else:
    st.info("좌측 사이드바에서 분석에 필요한 엑셀 파일들을 업로드해 주세요.")
