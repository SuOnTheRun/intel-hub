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
/***** Section headers & separators *****/
.section-head{
  display:flex; align-items:baseline; justify-content:space-between;
  border-bottom:1px solid #2A2F3A; padding:6px 2px 8px 2px; margin:6px 2px 14px 2px;
}
.section-title{ font-size:18px; font-weight:600; letter-spacing:.2px; }
.section-note{ font-size:12px; color:#9AA0A6; font-style:italic; }

/***** Soft card for scorecards *****/
.soft-card{
  border:1px solid #2A2F3A; border-radius:16px;
  background:#0B0E14; padding:12px 14px; margin:4px 0 16px 0;
}

/***** Tab styling *****/
.stTabs [role="tablist"]{ gap:8px; border-bottom:1px solid #2A2F3A; padding-bottom:6px; }
.stTabs [role="tab"]{
  background:#0E1117; border:1px solid #2A2F3A; color:#E6E6E6;
  border-radius:12px; padding:6px 12px; font-weight:500;
}
.stTabs [role="tab"][aria-selected="true"]{ background:#141824; border-color:#3A4150; }

/***** Chips (reliability) *****/
.chip-row{ margin:6px 0 8px 0; }
.chip{
  display:inline-block; padding:2px 8px; border:1px solid #2A2F3A; border-radius:999px;
  font-size:12px; color:#C9CDD3; background:#10141E; margin-right:6px; margin-bottom:6px;
}

</style>
""", unsafe_allow_html=True)

    """, unsafe_allow_html=True)
