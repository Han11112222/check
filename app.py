from sklearn.metrics import r2_score

# ... (기존 데이터 병합 로직 이후)

# 1. 통계 지표 계산 (실제 데이터가 있는 날 기준)
valid_data = compare_df.dropna(subset=['실제실적'])
r2_new = r2_score(valid_data['실제실적'], valid_data['신규모델_계획'])
r2_old = r2_score(valid_data['실적실적'], valid_data['기존방식_계획']) # 보통 0에 수렴

st.subheader("📈 모델 적합도 지수 (R² Score)")
c1, c2 = st.columns(2)
c1.metric("신규 모델 유사도", f"{r2_new:.2f}", help="1에 가까울수록 실제와 유사")
c2.metric("기존 방식 유사도", f"{r2_old:.2f}")

# 2. 일별 Gap (오차) 시각화
st.subheader("📉 일별 계획 대비 오차(Gap) 분석")
compare_df['신규_Gap'] = compare_df['실제실적'] - compare_df['신규모델_계획']
compare_df['기존_Gap'] = compare_df['실제실적'] - compare_df['기존방식_계획']

fig_gap = go.Figure()
fig_gap.add_trace(go.Bar(x=compare_df['일'], y=compare_df['기존_Gap'], 
                         name='기존 방식 오차', marker_color='lightgray'))
fig_gap.add_trace(go.Bar(x=compare_df['일'], y=compare_df['신규_Gap'], 
                         name='신규 모델 오차', marker_color='#FF4B4B'))

fig_gap.update_layout(title="일별 오차 비교 (0에 가까울수록 정확)",
                      xaxis_title="일자", yaxis_title="오차량 (m³)", barmode='group')
st.plotly_chart(fig_gap, use_container_width=True)

# 3. 잔차 산점도 (Similarity Scatter Plot)
st.subheader("🎯 실제 vs 계획 산점도 (유사도 시각화)")
fig_scatter = go.Figure()
fig_scatter.add_trace(go.Scatter(x=valid_data['실제실적'], y=valid_data['신규모델_계획'], 
                                mode='markers', name='신규 모델',
                                marker=dict(color='#FF4B4B', size=10, opacity=0.6)))
# 기준선 (y=x)
fig_scatter.add_trace(go.Scatter(x=[valid_data['실제실적'].min(), valid_data['실제실적'].max()],
                                y=[valid_data['실제실적'].min(), valid_data['실제실적'].max()],
                                mode='lines', name='완벽 일치선', line=dict(color='black', dash='dash')))

fig_scatter.update_layout(title="실제값과 계획값의 상관관계",
                          xaxis_title="실제 공급량", yaxis_title="계획 공급량")
st.plotly_chart(fig_scatter, use_container_width=True)
