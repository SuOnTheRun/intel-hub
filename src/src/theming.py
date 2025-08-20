import streamlit as st

def apply_page_style():
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
        h1, h2, h3, h4 { font-family: ui-serif, Georgia, 'Times New Roman', serif; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        .stDataFrame { border-radius: 12px; }
        </style>
    """, unsafe_allow_html=True)
