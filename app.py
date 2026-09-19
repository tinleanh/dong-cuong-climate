import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# =====================================================================
# PAGE CONFIGURATION & COMPACT CSS STYLING
# =====================================================================
st.set_page_config(
    page_title="Climate Projections Dashboard - Dong Cuong",
    page_icon="🌏",
    layout="wide"
)

# Tối ưu CSS để giao diện siêu gọn, hiển thị trọn vẹn trong 1 màn hình
st.markdown("""
<style>
    /* Giảm khoảng đệm trên/dưới toàn màn hình */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    /* Thu nhỏ tiêu đề H1 và H5 */
    h1 {
        font-size: 1.45rem !important;
        margin-bottom: 0.1rem !important;
        padding-bottom: 0rem !important;
    }
    h5 {
        font-size: 0.88rem !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.2rem !important;
        font-weight: 600 !important;
    }
    .stCaption {
        font-size: 0.8rem !important;
        margin-bottom: 0.4rem !important;
    }
    /* Thu nhỏ kích thước chữ của các thẻ st.metric */
    [data-testid="stMetricValue"] {
        font-size: 1.15rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: #555555 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.72rem !important;
    }
    hr {
        margin-top: 0.35rem !important;
        margin-bottom: 0.35rem !important;
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 1. LOAD DATA AND ALIGN HISTORICAL-FUTURE TRANSITION (SMOOTH AT 2021)
# =====================================================================
@st.cache_data
def load_data(csv_path="climate_projections_tinleanh.csv"):
    df = pd.read_csv(csv_path)

    # 1. Tách chuỗi quan trắc trạm
    df_hist = df[df['Scenario'] == 'Historical'].sort_values('Year').copy()
    hist_end_year = int(df_hist['Year'].max())

    last_hist_temp = df_hist[df_hist['Year'] == hist_end_year]['Temperature'].values[0]
    last_hist_precip = df_hist[df_hist['Year'] == hist_end_year]['Precipitation'].values[0]

    # 2. Dữ liệu tương lai
    df_future = df[df['Scenario'] != 'Historical'].copy()

    # Khắc phục lệch mốc 2021
    df_future.loc[df_future['Year'] == hist_end_year, 'Temperature'] = last_hist_temp
    df_future.loc[df_future['Year'] == hist_end_year, 'Precipitation'] = last_hist_precip

    return df_hist, df_future, hist_end_year

# =====================================================================
# 2. SIDEBAR CONTROLS & FILTERS
# =====================================================================
st.sidebar.title("⚙️ Control Panel")

try:
    df_hist, df_future, hist_end_year = load_data()
    min_year = int(df_hist['Year'].min())
    max_year = int(df_future['Year'].max())

    st.sidebar.subheader("📅 Time Horizon")
    year_range = st.sidebar.slider(
        "Select Year Range:",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )

    st.sidebar.subheader("🌱 Emission Scenarios")
    available_scenarios = ['ssp126', 'ssp245', 'ssp370', 'ssp585']
    scenario_labels = {
        'ssp126': 'SSP1-2.6 (Low)',
        'ssp245': 'SSP2-4.5 (Intermediate)',
        'ssp370': 'SSP3-7.0 (Medium-to-high)',
        'ssp585': 'SSP5-8.5 (High)'
    }
    selected_scenarios = st.sidebar.multiselect(
        "Choose Scenarios to display:",
        options=available_scenarios,
        default=available_scenarios,
        format_func=lambda x: scenario_labels[x]
    )

    st.sidebar.subheader("🛰️ CMIP6 Climate Models")
    available_models = sorted(df_future['Model'].unique().tolist())
    
    col_m1, col_m2 = st.sidebar.columns(2)
    select_all = col_m1.button("Select All", use_container_width=True)
    clear_all = col_m2.button("Clear All", use_container_width=True)

    if select_all:
        st.session_state['selected_models'] = available_models
    elif clear_all:
        st.session_state['selected_models'] = []
    elif 'selected_models' not in st.session_state:
        st.session_state['selected_models'] = available_models

    selected_models = st.sidebar.multiselect(
        "Filter Climate Models (GCMs):",
        options=available_models,
        default=st.session_state['selected_models']
    )
    st.session_state['selected_models'] = selected_models

    st.sidebar.subheader("🎨 Display Options")
    show_uncertainty = st.sidebar.checkbox("Show Uncertainty Envelope", value=True)
    show_individual_models = st.sidebar.checkbox("Show Individual Model Curves", value=False)

    if not selected_scenarios:
        st.warning("⚠️ Please select at least one Emission Scenario.")
    if not selected_models:
        st.warning("⚠️ Please select at least one Climate Model.")

    # =====================================================================
    # 3. COMPACT INTERACTIVE PLOT BUILDER
    # =====================================================================
    def build_chart(variable_col, y_axis_label, main_title, color_palette, unit):
        fig = go.Figure()

        # 1. Đường quan trắc lịch sử
        df_h_filtered = df_hist[(df_hist['Year'] >= year_range[0]) & (df_hist['Year'] <= year_range[1])]
        if not df_h_filtered.empty:
            fig.add_trace(go.Scatter(
                x=df_h_filtered['Year'],
                y=df_h_filtered[variable_col],
                mode='lines',
                name=f"Observed ({min_year}-{hist_end_year})",
                line=dict(color='#111111', width=2.0),
                hovertemplate=f"Year: %{{x}}<br>Observed: %{{y:.2f}} {unit}<extra></extra>"
            ))

        # 2. Dữ liệu tương lai
        df_f_filtered = df_future[
            (df_future['Year'] >= year_range[0]) & 
            (df_future['Year'] <= year_range[1]) & 
            (df_future['Scenario'].isin(selected_scenarios)) &
            (df_future['Model'].isin(selected_models))
        ]

        if not df_f_filtered.empty:
            for sc in selected_scenarios:
                sc_data = df_f_filtered[df_f_filtered['Scenario'] == sc]
                if sc_data.empty:
                    continue

                hex_color = color_palette[sc]
                rgb_color = f"rgba({int(hex_color[1:3], 16)}, {int(hex_color[3:5], 16)}, {int(hex_color[5:7], 16)}, 0.16)"

                if show_individual_models:
                    for m in selected_models:
                        m_data = sc_data[sc_data['Model'] == m].sort_values('Year')
                        if not m_data.empty:
                            fig.add_trace(go.Scatter(
                                x=m_data['Year'],
                                y=m_data[variable_col],
                                mode='lines',
                                name=f"{scenario_labels[sc].split(' ')[0]} - {m}",
                                line=dict(color=hex_color, width=0.7, dash='dot'),
                                opacity=0.4,
                                showlegend=False,
                                hovertemplate=f"Model: {m}<br>Year: %{{x}}<br>Value: %{{y:.2f}} {unit}<extra></extra>"
                            ))

                summary = sc_data.groupby('Year')[variable_col].agg(Mean='mean', Min='min', Max='max').reset_index()

                if show_uncertainty and len(selected_models) > 1:
                    fig.add_trace(go.Scatter(
                        x=summary['Year'], y=summary['Min'],
                        mode='lines', line=dict(width=0),
                        showlegend=False, hoverinfo='skip'
                    ))
                    fig.add_trace(go.Scatter(
                        x=summary['Year'], y=summary['Max'],
                        mode='lines', line=dict(width=0),
                        fill='tonexty', fillcolor=rgb_color,
                        showlegend=False, hoverinfo='skip'
                    ))

                mean_label = f"{scenario_labels[sc].split(' ')[0]}"
                fig.add_trace(go.Scatter(
                    x=summary['Year'],
                    y=summary['Mean'],
                    mode='lines',
                    name=mean_label,
                    line=dict(color=hex_color, width=2.0),
                    hovertemplate=f"{mean_label}: %{{y:.2f}} {unit}<extra></extra>"
                ))

        if year_range[0] <= hist_end_year <= year_range[1]:
            fig.add_vline(x=hist_end_year, line_width=1.1, line_dash="dash", line_color="#777777")
            fig.add_annotation(
                x=hist_end_year + 1, y=0.98, yref='paper',
                text=f"Forecast ({hist_end_year}➔)",
                showarrow=False, xanchor='left', font=dict(size=10, color="#555555")
            )

        subtitle_text = "Dong Cuong Commune, Lao Cai Province • 1990-2100 • CMIP6 Multi-Model Ensemble • Delta Scaling"

        # Cấu hình chiều cao biểu đồ vừa vặn (410px) và lề sát viền
        fig.update_layout(
            title=dict(
                text=f"<b>{main_title}</b><br><span style='font-size: 11px; color: #666666; font-weight: normal;'>{subtitle_text}</span>",
                x=0.01, y=0.96, xanchor='left', yanchor='top'
            ),
            xaxis=dict(title=None, showgrid=True, gridcolor='#ececec', range=[year_range[0], year_range[1]]),
            yaxis=dict(title=y_axis_label, showgrid=True, gridcolor='#ececec'),
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5, font=dict(size=10)),
            margin=dict(t=50, b=30, l=55, r=25),
            height=410
        )
        return fig

    # =====================================================================
    # 4. COMPACT MAIN DASHBOARD CONTENT & KPI METRICS
    # =====================================================================
    st.title("🌏 Interactive Climate Change Projections Dashboard")
    st.caption("Dong Cuong Commune, Lao Cai Province — CMIP6 Downscaled Projections (1990-2100)")

    baseline_temp = df_hist['Temperature'].mean()
    baseline_precip = df_hist['Precipitation'].mean()

    df_end_century = df_future[
        (df_future['Year'] >= 2080) & 
        (df_future['Model'].isin(selected_models))
    ]

    scenario_short = {'ssp126': 'SSP1-2.6', 'ssp245': 'SSP2-4.5', 'ssp370': 'SSP3-7.0', 'ssp585': 'SSP5-8.5'}

    # ROW 1: TEMPERATURE
    st.markdown("##### 🌡️ Projected Mean Surface Temperature (2080–2100 vs Baseline)")
    col_t_base, col_t1, col_t2, col_t3, col_t4 = st.columns(5)
    
    col_t_base.metric(label="Historical Baseline", value=f"{baseline_temp:.2f} °C", delta="1990–2021 Mean", delta_color="off")

    for col, sc in zip([col_t1, col_t2, col_t3, col_t4], ['ssp126', 'ssp245', 'ssp370', 'ssp585']):
        if sc in selected_scenarios and not df_end_century.empty:
            sub = df_end_century[df_end_century['Scenario'] == sc]
            if not sub.empty:
                val = sub['Temperature'].mean()
                col.metric(label=f"{scenario_short[sc]} Warming", value=f"{val:.2f} °C", delta=f"{val - baseline_temp:+.2f} °C", delta_color="inverse")
            else:
                col.metric(label=f"{scenario_short[sc]} Warming", value="N/A")
        else:
            col.metric(label=f"{scenario_short[sc]} Warming", value="Inactive", delta="Filtered", delta_color="off")

    # ROW 2: PRECIPITATION
    st.markdown("##### 🌧️ Projected Total Annual Precipitation (2080–2100 vs Baseline)")
    col_p_base, col_p1, col_p2, col_p3, col_p4 = st.columns(5)

    col_p_base.metric(label="Historical Baseline", value=f"{baseline_precip:.0f} mm", delta="1990–2021 Mean", delta_color="off")

    for col, sc in zip([col_p1, col_p2, col_p3, col_p4], ['ssp126', 'ssp245', 'ssp370', 'ssp585']):
        if sc in selected_scenarios and not df_end_century.empty:
            sub = df_end_century[df_end_century['Scenario'] == sc]
            if not sub.empty:
                val = sub['Precipitation'].mean()
                pct_diff = ((val - baseline_precip) / baseline_precip) * 100
                col.metric(label=f"{scenario_short[sc]} Precip", value=f"{val:.0f} mm", delta=f"{pct_diff:+.1f} %")
            else:
                col.metric(label=f"{scenario_short[sc]} Precip", value="N/A")
        else:
            col.metric(label=f"{scenario_short[sc]} Precip", value="Inactive", delta="Filtered", delta_color="off")

    st.divider()

    # TABS FOR VISUALIZATION
    tab_temp, tab_precip, tab_table = st.tabs([
        "🌡️ Surface Temperature",
        "🌧️ Annual Total Precipitation",
        "📑 Data Table & Export"
    ])

    temp_colors = {'ssp126': '#e6b800', 'ssp245': '#e67e22', 'ssp370': '#e74c3c', 'ssp585': '#800020'}
    precip_colors = {'ssp126': '#48cae4', 'ssp245': '#0096c7', 'ssp370': '#0077b6', 'ssp585': '#03045e'}

    with tab_temp:
        fig_t = build_chart(
            variable_col='Temperature',
            y_axis_label='Annual Mean Temp (°C)',
            main_title='Time Series of Projected Mean Surface Temperature',
            color_palette=temp_colors,
            unit='°C'
        )
        st.plotly_chart(fig_t, use_container_width=True)

    with tab_precip:
        fig_p = build_chart(
            variable_col='Precipitation',
            y_axis_label='Annual Precip (mm)',
            main_title='Time Series of Projected Annual Total Precipitation',
            color_palette=precip_colors,
            unit='mm'
        )
        st.plotly_chart(fig_p, use_container_width=True)

    with tab_table:
        f_hist_show = df_hist[(df_hist['Year'] >= year_range[0]) & (df_hist['Year'] <= year_range[1])]
        f_fut_show = df_future[
            (df_future['Year'] >= year_range[0]) & 
            (df_future['Year'] <= year_range[1]) & 
            (df_future['Scenario'].isin(selected_scenarios)) &
            (df_future['Model'].isin(selected_models))
        ]
        df_display = pd.concat([f_hist_show, f_fut_show], ignore_index=True)

        st.dataframe(df_display, use_container_width=True, height=350)
        csv_data = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv_data,
            file_name=f"dong_cuong_climate_{year_range[0]}_{year_range[1]}.csv",
            mime="text/csv"
        )

except FileNotFoundError:
    st.error("Error: `climate_projections_tinleanh.csv` not found in the directory.")