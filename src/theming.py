import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1400px;}
    .stMarkdown p, .stDataFrame, .stTable {font-size: 0.95rem;}
    .metric-card {border: 1px solid #E7E9EF; border-radius: 16px; padding: 16px; background: #FFFFFF; box-shadow: 0 1px 3px rgba(0,0,0,0.03);}
    .kpi {font-weight:600; font-size: 1.1rem;}
    .kpi-sub {color:#666; font-size: 0.85rem;}
    </style>
    """, unsafe_allow_html=True)
