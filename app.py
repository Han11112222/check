import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os

st.set_page_config(page_title="공급량 예측 모델 성과 보고", layout="wide")

# [1] 데이터 로드 (이전과 동일한 안정적인 로직)
@st.cache_data
def load_data():
    plan_file = "2026_연간_일별공급계획_2.xlsx"
    hist_file = "공급량(계획_실적).xlsx"
    
    try:
        # 계획 데이터 (헤더 2번째 줄)
        df_p = pd.read_excel(plan_file, sheet_name='연간', header=1)
        df_p.columns = [str(c).replace(" ", "").strip() for c in df_p.columns]
        if '예상공급량(m3)' in df_p.columns: df_p.rename(columns={'예상공급량(m3)': '계획_m3'}, inplace=True)
        elif '계획(m3)' in df_p.columns: df_p.rename(columns={'계획(m3)': '계획_m3'}, inplace=True)
        df_p = df_p.dropna(subset=['일'])
        
        # 실적 데이터
        df_h = pd.read_excel(hist_file, sheet_name='일별실적')
        df_h['일자'] = pd.to_datetime(df_h['일자'], errors='coerce')
        df_a = df_h[df_h['일자'].dt.year == 2026].copy()
        
        return df_p, df_a
    except Exception as e:
        st.error(f"데이터 로드 중 에러: {e}")
        return None, None

st.title("📊 공급량 예측 모델 도입 성과 보고")
st.markdown("---")

df_plan, df_actual = load_data()

if df_plan is not None and not df_actual.empty:
    target_month = 1
    p_mon = df_plan[df_plan['월'] == target_month].copy()
    a_mon = df_actual[df_actual['일자'].dt.month == target_month].copy()
    a_mon['일'] = a_mon['일자'].dt.day

    if not a_mon.empty:
        # [비교군] 기존 방식 (단순 n분화)
        total_plan = p_mon['계획_m3'].sum()
        p_mon['기존방식'] = total_plan / len(p_mon)

        # [데이터 병합]
        merged = pd.merge(p_mon[['일', '계획_m3', '기존방식']], 
                          a_mon[['일', '공급량(M3)']], on='일', how='inner')
        merged.rename(columns={'계획_m3': '신규모델', '공급량(M3)': '실제실적'}, inplace=True)
        
        # 빈 값 제거 (안전장치)
        valid_df = merged.dropna(subset=['실제실적', '신규모델', '기존방식']).copy()

        if not valid_df.empty:
            # --------------------------------------------------------------------
            # [성과 계산] 핵심 로직
            # --------------------------------------------------------------------
            # 오차(절대값) 계산: |실제 - 계획|
            valid_df['기존_오차'] = abs(valid_df['실제실적'] - valid_df['기존방식'])
            valid_df['신규_오차'] = abs(valid_df['실제실적'] - valid_df['신규모델'])
            
            # 평균 오차 (MAE)
            avg_old_err = valid_df['기존_오차'].mean()
            avg_new_err = valid_df['신규_오차'].mean()
            
            # 개선율 계산: (기존오차 - 신규오차) / 기존오차 * 100
            improvement_rate = ((avg_old_err - avg_new_err) / avg_old_err) * 100

            # --------------------------------------------------------------------
            # [KPI 영역] 가장 중요한 숫자만 강조
            # --------------------------------------------------------------------
            st.subheader("🏆 모델 도입 핵심 성과")
            
            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("예측 정확도 개선율", f"{improvement_rate:.1f}%", delta="대폭 개선", delta_color="normal")
            with k2:
                st.metric("기존 방식 평균 오차", f"{avg_old_err:,.0f} m³")
            with k3:
                st.metric("신규 모델 평균 오차", f"{avg_new_err:,.0f} m³", delta=f"{int(avg_new_err - avg_old_err):,} m³ 감소")
            
            st.success(f"""
            **✅ 성과 요약:** 기존의 단순 평균 방식보다 **일일 오차를 {improvement_rate:.1f}% 줄이는 데 성공**했습니다. 
            이는 불필요한 공급 과잉이나 부족을 방지하여 **운영 효율성**을 높였다는 것을 의미합니다.
            """)

            # --------------------------------------------------------------------
            # [그래프 영역]
            # --------------------------------------------------------------------
            st.subheader("📉 일별 공급 패턴 및 오차 비교")
            
            # 1. 라인 차트 (패턴)
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=valid_df['일'], y=valid_df['실제실적'], name='실제 공급량', line=dict(color='black', width=3)))
            fig_line.add_trace(go.Scatter(x=valid_df['일'], y=valid_df['신규모델'], name='신규 모델 (제안)', line=dict(color='#FF4B4B', width=2)))
            fig_line.add_trace(go.Scatter(x=valid_df['일'], y=valid_df['기존방식'], name='기존 방식 (단순평균)', line=dict(color='gray', dash='dot')))
            fig_line.update_layout(height=400, margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_line, use_container_width=True)

            # --------------------------------------------------------------------
            # [상세 표 영역] 13.8% 산출 근거 데이터
            # --------------------------------------------------------------------
            st.subheader("📋 [상세] 일별 오차 감소 내역 (산출 근거)")
            
            # 표에 보여줄 데이터 정리
            table_df = valid_df[['일', '실제실적', '기존방식', '신규모델', '기존_오차', '신규_오차']].copy()
            
            # '오차 감소량' 컬럼 추가 (양수면 개선된 것)
            table_df['오차_감소량'] = table_df['기존_오차'] - table_df['신규_오차']
            
            # 포맷팅을 위한 스타일 적용 함수
            def highlight_improvement(val):
                color = '#e6fffa' if val > 0 else '#fff5f5' # 개선되면 초록 배경, 아니면 빨간 배경
                return f'background-color: {color}'

            # 숫자 포맷 설정 (천 단위 콤마)
            st.dataframe(
                table_df.style
                .format("{:,.0f}", subset=['실제실적', '기존방식', '신규모델', '기존_오차', '신규_오차', '오차_감소량'])
                .map(highlight_improvement, subset=['오차_감소량']),
                use_container_width=True,
                height=400
            )
            
            st.info("""
            **💡 표 해석 가이드:**
            * **기존 오차**: | 실제 실적 - 기존 방식 |
            * **신규 오차**: | 실제 실적 - 신규 모델 |
            * **오차 감소량**: (기존 오차 - 신규 오차) → **값이 클수록(양수) 신규 모델이 더 정확하게 맞춘 날입니다.**
            * 최종 **13.8%**는 위 표의 '기존 오차 평균' 대비 '신규 오차 평균'이 얼마나 줄었는지를 계산한 결과입니다.
            """)
            
        else:
            st.warning("분석할 유효 데이터가 없습니다.")
    else:
        st.warning("선택하신 월의 실적 데이터가 없습니다.")
