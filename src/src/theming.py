import streamlit as st

def apply_page_style():
    st.markdown("""
        <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
        h1, h2, h3, h4 { font-family: ui-serif, Georgia, 'Times New Roman', serif; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; }
        .stDataFrame { border-radius: 12px; }
        
        </style>
        st.markdown("""
<style>
/* Quiet-luxury buttons */
.stDownloadButton > button, .stLinkButton > button, .stButton > button {
  background: #0E1117 !important;
  color: #E6E6E6 !important;
  border: 1px solid #2A2F3A !important;
  border-radius: 14px !important;
  padding: 8px 14px !important;
  font-weight: 500 !important;
  letter-spacing: 0.2px !important;
  box-shadow: 0 1px 0 rgba(255,255,255,0.03) inset, 0 6px 12px rgba(0,0,0,0.25) !important;
  transition: transform .08s ease, border-color .15s ease, box-shadow .2s ease !important;
}
.stDownloadButton > button:hover, .stLinkButton > button:hover, .stButton > button:hover {
  border-color: #3A4150 !important;
  box-shadow: 0 2px 0 rgba(255,255,255,0.05) inset, 0 10px 18px rgba(0,0,0,0.32) !important;
  transform: translateY(-1px);
}
.stDownloadButton > button:active, .stLinkButton > button:active, .stButton > button:active {
  transform: translateY(0);
  box-shadow: 0 0 0 rgba(0,0,0,0.25) !important;
}
.stDownloadButton, .stLinkButton, .stButton {
  margin-right: 8px !important;
}
</style>
""", unsafe_allow_html=True)

    """, unsafe_allow_html=True)
