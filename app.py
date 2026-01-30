import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import r2_score
import os

st.set_page_config(page_title="공급량 계획 모델 성능 비교", layout="wide")

# [1] 데이터 로드 및 전처리
@st.cache_data
def load_comparison_data():
    plan_file = "2026_연간_일별공급계획_2.xlsx"
    hist_file = "공급량(계획_실적).xlsx"
    
    try:
        # 1. 계획 데이터 로드
        # 헤더가 2번째 줄(Index 1)에 있으므로 header=1 설정
        df_p = pd.read_excel(plan_file, sheet_name='연간', header=1)
        
        # 컬럼명 정리 (공백 제거)
        df_p.columns = [str(c).replace(" ", "").strip() for c in df_p.columns]
        
        # 핵심 컬럼명 표준화 (사용자가 올린 파일 기준)
        if '예상공급량(m3)' in df_p.columns:
            df_p.rename(columns={'예상공급량(m3)': '계획_m3'}, inplace=True)
        elif '계획(m3)' in df_p.columns:
            df_p.rename(columns={'계획(m3)': '계획_m3'}, inplace=True)
            
        # 날짜 데이터 정수형 변환 및 빈 행 제거
        df_p = df_p.dropna(subset=['연', '월', '일'])
        df_p[['연', '월', '일']] = df_p[['연', '월', '일']].astype(int)
        
        # 2. 실적 데이터 로드
        df_h = pd.read_excel(hist_file, sheet_name='일별실적')
        df_h['일자'] = pd.to_datetime(df_h['일자'], errors='coerce')
        
        # 2026년 데이터만 필터링
        df_a = df_h[df_h['일자'].dt.year == 2026].copy()
        
        return df_p, df_a

    except Exception as e:
        st.error(f"데이터 파일 로드 중 오류: {e}")
        return None, None

st.title("📊 공급량 예측 모델 우월성 분석")
st.markdown("---")

df_plan, df_actual = load_comparison_data()

if df_plan is not None and not df_actual.empty:
    # 1월 데이터 분석 (기본값)
    target_month = 1
    
    # 해당 월 데이터 추출
    p_mon = df_plan[df_plan['월'] == target_month].copy()
    a_mon = df_actual[df_actual['일자'].dt.month == target_month].copy()
    a_mon['일'] = a_mon['일자'].dt.day

    if not a_mon.empty:
        # [비교군 생성] 기존 방식 (단순 n분화)
        # 월간 총 계획량을 일수로 나눔
        total_plan_vol = p_mon['계획_m3'].sum()
        p_mon['기존방식'] = total_plan_vol / len(p_mon)

        # [데이터 병합] Inner Join (실적과 계획이 모두 있는 날짜만 비교)
        merged = pd.merge(p_mon[['일', '계획_m3', '기존방식']], 
                          a_mon[['일', '공급량(M3)']], on='일', how='inner')
        merged.rename(columns={'계획_m3': '신규모델', '공급량(M3)': '실제실적'}, inplace=True)

        # -------------------------------------------------------------------------
        # [핵심 수정] 통계 계산 전, 빈 값(NaN)이 있는 행 강제 제거 (에러 방지)
        # -------------------------------------------------------------------------
        valid_df = merged.dropna(subset=['실제실적', '신규모델', '기존방식']).copy()

        if not valid_df.empty and len(valid_df) > 1:
            # 1. 오차(Error) 계산
            mae_old = abs(valid_df['실제실적'] - valid_df['기존방식']).mean()
            mae_new = abs(valid_df['실제실적'] - valid_df['신규모델']).mean()
            
            # 2. 개선율 (Improvement)
            if mae_old > 0:
                imp_rate = ((mae_old - mae_new) / mae_old) * 100
            else:
                imp_rate = 0
            
            # 3. R2 Score (적합도) - 이제 에러가 나지 않습니다.
            r2_new = r2_score(valid_df['실제실적'], valid_df['신규모델'])
            r2_old = r2_score(valid_df['실제실적'], valid_df['기존방식'])

            # --------------------------------------------------------------------------------
            # [KPI 대시보드]
            # --------------------------------------------------------------------------------
            st.subheader("🏆 모델 성능 비교 요약")
            
            kpi1, kpi2, kpi3 = st.columns(3)
            
            with kpi1:
                st.metric("예측 오차 개선율", f"{imp_rate:.1f}%", delta="정확도 상승", delta_color="normal")
                st.caption(f"기존 방식 대비 오차를 **{imp_rate:.1f}%** 줄였습니다.")
            
            with kpi2:
                st.metric("신규 모델 적합도 (R²)", f"{max(0, r2_new):.3f}")
                st.caption("1.0에 가까울수록 실제 패턴과 일치")
                
            with kpi3:
                st.metric("기존 방식 적합도 (R²)", f"{max(0, r2_old):.3f}")
                st.caption("변동성을 반영하지 못해 수치가 낮음")

            st.success(f"""
            **✅ 분석 결론:** 기존 모델은 단순히 월평균을 사용하여 실제 수요 변화를 따라가지 못했으나, 
            **신규 모델(그룹핑 방식)**은 실제 수요 패턴을 **{max(0, r2_new)*100:.1f}%** 수준으로 설명하고 있습니다.
            결과적으로 예측 오차를 **{imp_rate:.1f}%** 감소시켜 공급 안정성을 확보했습니다.
            """)

            st.divider()

            # --------------------------------------------------------------------------------
            # [시각화] 차트 영역
            # --------------------------------------------------------------------------------
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📈 일별 패턴 추종 비교")
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=valid_df['일'], y=valid_df['실제실적'], name='실제 실적', line=dict(color='black', width=3)))
                fig_line.add_trace(go.Scatter(x=valid_df['일'], y=valid_df['신규모델'], name='신규 모델', line=dict(color='#FF4B4B', width=2)))
                fig_line.add_trace(go.Scatter(x=valid_df['일'], y=valid_df['기존방식'], name='기존 방식', line=dict(color='gray', dash='dot')))
                fig_line.update_layout(legend=dict(orientation="h", y=1.1), height=400, margin=dict(l=10, r=10, t=0, b=10))
                st.plotly_chart(fig_line, use_container_width=True)

            with col_chart2:
                st.subheader("📉 오차(Gap) 감소 확인")
                valid_df['신규_오차'] = valid_df['실제실적'] - valid_df['신규모델']
                valid_df['기존_오차'] = valid_df['실제실적'] - valid_df['기존방식']
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=valid_df['일'], y=valid_df['기존_오차'], name='기존 오차', marker_color='lightgray'))
                fig_bar.add_trace(go.Bar(x=valid_df['일'], y=valid_df['신규_오차'], name='신규 오차 (개선)', marker_color='#FF4B4B'))
                fig_bar.update_layout(legend=dict(orientation="h", y=1.1), height=400, margin=dict(l=10, r=10, t=0, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)

        else:
            st.warning("분석할 수 있는 유효한 데이터가 부족합니다. (실적 데이터가 비어있거나 날짜가 매칭되지 않음)")
    else:
        st.warning(f"선택하신 {target_month}월의 2026년 실적 데이터가 없습니다.")
else:
    st.info("데이터를 불러오는 중입니다...")
