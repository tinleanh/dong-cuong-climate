import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# =====================================================================
# PAGE CONFIGURATION & ADVANCED RESPONSIVE CSS
# =====================================================================
st.set_page_config(
    page_title="Climate Projections Dashboard - Dong Cuong",
    page_icon="🌏",
    layout="wide"
)

st.markdown("""
<style>
    /* Cấu hình lề tổng thể */
    .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 1.0rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
    }
    h1 {
        font-size: 1.35rem !important;
        margin-bottom: 0.1rem !important;
    }
    h5 {
        font-size: 0.85rem !important;
        margin-top: 0.4rem !important;
        margin-bottom: 0.2rem !important;
        font-weight: 600 !important;
    }
    .stCaption {
        font-size: 0.78rem !important;
        margin-bottom: 0.4rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.05rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        color: #555555 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.70rem !important;
    }
    hr {
        margin-top: 0.4rem !important;
        margin-bottom: 0.4rem !important;
    }

    /* Tối ưu hiển thị Lưới 2 cột cho Điện thoại và Tablet (< 768px) */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
            padding-top: 0.6rem !important;
        }
        /* Ép các cột st.columns hiển thị thành 2 cột cạnh nhau thay vì xếp dọc */
        [data-testid="column"] {
            width: 50% !important;
            flex: 0 0 50% !important;
            min-width: 50% !important;
        }
        h1 {
            font-size: 1.1rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 0.9rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 1. LOAD DATA AND ALIGN HISTORICAL-FUTURE TRANSITION
# =====================================================================
@st.cache_data
def load_data(csv_path="climate_projections_tinleanh.csv"):
    df = pd.read_csv(csv_path)

    df_hist = df[df['Scenario'] == 'Historical'].sort_values('Year').copy()
    hist_end_year = int(df_hist['Year'].max())

    last_hist_temp = df_hist[df_hist['Year'] == hist_end_year]['Temperature'].values[0]
    last_hist_precip = df_hist[df_hist['Year'] == hist_end_year]['Precipitation'].values[0]

    df_future = df[df['Scenario'] != 'Historical'].copy()

    # Nối trơn tru mốc 2021
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
    # 3. RESPONSIVE INTERACTIVE PLOT BUILDER
    # =====================================================================
    def build_chart(variable_col, y_axis_label, main_title, color_palette, unit):
        fig = go.Figure()

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

        subtitle_text = "Dong Cuong, Lao Cai • 1990-2100 • CMIP6 Ensemble • Delta Scaling"

        fig.update_layout(
            title=dict(
                text=f"<b>{main_title}</b><br><span style='font-size: 10px; color: #666666;'>{subtitle_text}</span>",
                x=0.01, y=0.96, xanchor='left', yanchor='top'
            ),
            xaxis=dict(title=None, showgrid=True, gridcolor='#ececec', range=[year_range[0], year_range[1]]),
            yaxis=dict(title=y_axis_label, showgrid=True, gridcolor='#ececec'),
            template="plotly_white",
            hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5, font=dict(size=9)),
            margin=dict(t=50, b=45, l=45, r=20),
            autosize=True,
            height=380
        )
        return fig

    # =====================================================================
    # 4. MAIN DASHBOARD CONTENT & KPI METRICS (2021–2100)
    # =====================================================================
    st.title("🌏 Climate Projections Dashboard")
    st.caption("Dong Cuong Commune, Lao Cai Province — CMIP6 Downscaled Projections (1990-2100)")

    baseline_temp = df_hist['Temperature'].mean()
    baseline_precip = df_hist['Precipitation'].mean()

    # Tính toán trung bình toàn chu kỳ tương lai 2021-2100
    df_future_period = df_future[
        (df_future['Year'] >= 2021) & 
        (df_future['Model'].isin(selected_models))
    ]

    scenario_short = {'ssp126': 'SSP1-2.6', 'ssp245': 'SSP2-4.5', 'ssp370': 'SSP3-7.0', 'ssp585': 'SSP5-8.5'}

    # ROW 1: TEMPERATURE METRICS (2021–2100)
    st.markdown("##### 🌡️ Projected Mean Surface Temperature (2021–2100)")
    col_t_base, col_t1, col_t2, col_t3, col_t4 = st.columns(5)
    
    col_t_base.metric(label="Baseline", value=f"{baseline_temp:.2f} °C", delta="1990-2021", delta_color="off")

    for col, sc in zip([col_t1, col_t2, col_t3, col_t4], ['ssp126', 'ssp245', 'ssp370', 'ssp585']):
        if sc in selected_scenarios and not df_future_period.empty:
            sub = df_future_period[df_future_period['Scenario'] == sc]
            if not sub.empty:
                val = sub['Temperature'].mean()
                col.metric(label=f"{scenario_short[sc]}", value=f"{val:.2f} °C", delta=f"{val - baseline_temp:+.2f} °C", delta_color="inverse")
            else:
                col.metric(label=f"{scenario_short[sc]}", value="N/A")
        else:
            col.metric(label=f"{scenario_short[sc]}", value="Off", delta="Filtered", delta_color="off")

    # ROW 2: PRECIPITATION METRICS (2021–2100)
    st.markdown("##### 🌧️ Projected Total Annual Precipitation (2021–2100)")
    col_p_base, col_p1, col_p2, col_p3, col_p4 = st.columns(5)

    col_p_base.metric(label="Baseline", value=f"{baseline_precip:.0f} mm", delta="1990-2021", delta_color="off")

    for col, sc in zip([col_p1, col_p2, col_p3, col_p4], ['ssp126', 'ssp245', 'ssp370', 'ssp585']):
        if sc in selected_scenarios and not df_future_period.empty:
            sub = df_future_period[df_future_period['Scenario'] == sc]
            if not sub.empty:
                val = sub['Precipitation'].mean()
                pct_diff = ((val - baseline_precip) / baseline_precip) * 100
                col.metric(label=f"{scenario_short[sc]}", value=f"{val:.0f} mm", delta=f"{pct_diff:+.1f} %")
            else:
                col.metric(label=f"{scenario_short[sc]}", value="N/A")
        else:
            col.metric(label=f"{scenario_short[sc]}", value="Off", delta="Filtered", delta_color="off")

    st.divider()

    # TABS FOR VISUALIZATION
    tab_temp, tab_precip, tab_table = st.tabs([
        "🌡️ Surface Temp",
        "🌧️ Precipitation",
        "📑 Data & Export"
    ])

    temp_colors = {'ssp126': '#e6b800', 'ssp245': '#e67e22', 'ssp370': '#e74c3c', 'ssp585': '#800020'}
    precip_colors = {'ssp126': '#48cae4', 'ssp245': '#0096c7', 'ssp370': '#0077b6', 'ssp585': '#03045e'}

    config = {'responsive': True, 'displayModeBar': False, 'scrollZoom': False}

    with tab_temp:
        fig_t = build_chart(
            variable_col='Temperature',
            y_axis_label='Annual Mean Temp (°C)',
            main_title='Time Series of Projected Mean Surface Temperature',
            color_palette=temp_colors,
            unit='°C'
        )
        st.plotly_chart(fig_t, use_container_width=True, config=config)

    with tab_precip:
        fig_p = build_chart(
            variable_col='Precipitation',
            y_axis_label='Annual Precip (mm)',
            main_title='Time Series of Projected Annual Total Precipitation',
            color_palette=precip_colors,
            unit='mm'
        )
        st.plotly_chart(fig_p, use_container_width=True, config=config)

    with tab_table:
        f_hist_show = df_hist[(df_hist['Year'] >= year_range[0]) & (df_hist['Year'] <= year_range[1])]
        f_fut_show = df_future[
            (df_future['Year'] >= year_range[0]) & 
            (df_future['Year'] <= year_range[1]) & 
            (df_future['Scenario'].isin(selected_scenarios)) &
            (df_future['Model'].isin(selected_models))
        ]
        df_display = pd.concat([f_hist_show, f_fut_show], ignore_index=True)

        st.dataframe(df_display, use_container_width=True, height=320)
        csv_data = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv_data,
            file_name=f"dong_cuong_climate_{year_range[0]}_{year_range[1]}.csv",
            mime="text/csv"
        )

except FileNotFoundError:
    st.error("Error: `climate_projections_tinleanh.csv` not found in the directory.")
