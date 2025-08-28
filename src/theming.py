import streamlit as st

def apply_page_style():
    st.markdown("""
    <style>
    /* ===== Base layout & typography ===== */
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; }
    h1, h2, h3, h4 { font-family: ui-serif, Georgia, 'Times New Roman', serif; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif; }
    .stDataFrame { border-radius: 12px; }

    /* ===== Premium hero ===== */
    .hero { text-align:center; margin-bottom: 8px; }
    .hero-title { font-size: 36px; font-weight: 800; letter-spacing: .6px; }
    .hero-sub { font-size: 13px; color: #8E94A1; font-style: italic; margin-top: 4px; }
    .hero:after { content:""; display:block; width: 160px; height:1px; margin: 12px auto 6px; background: linear-gradient(90deg, transparent, #C2A86B, transparent); }

    /* ===== Alerts (visible, luxe amber) ===== */
    .alert-strip{
      background: rgba(194,168,107,0.10);
      color: #E9D9A7;
      border: 1px solid rgba(194,168,107,0.35);
      border-radius: 12px;
      padding: 10px 14px;
      margin: 2px 0 12px 0;
    }

    /* ===== Buttons ===== */
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
      box-shadow: none !important;
    }
    .stDownloadButton, .stLinkButton, .stButton { margin-right: 8px !important; }

    /* ===== Section headers & separators (light gray) ===== */
    .section-head{
      display:flex; align-items:baseline; justify-content:space-between;
      border-bottom:1px solid #3E4452; padding:6px 2px 8px 2px; margin:6px 2px 14px 2px;
    }
    .section-title{ font-size:18px; font-weight:600; letter-spacing:.2px; }
    .section-note{ font-size:12px; color:#9AA0A6; font-style:italic; }

    /* ===== Soft card (subtle, not a thick black bar) ===== */
    .soft-card{
      border:1px solid #2A2F3A; border-radius:16px;
      background: linear-gradient(180deg, rgba(20,24,36,.14), rgba(20,24,36,.06));
      padding:12px 14px; margin:4px 0 16px 0;
    }

    /* ===== Tabs (different from buttons) ===== */
    .stTabs [role="tablist"]{ gap:8px; border-bottom:1px solid #3E4452; padding-bottom:6px; }
    .stTabs [role="tab"]{
      background:#101421; border:1px solid #2A2F3A; color:#DDE1E7;
      border-radius:12px; padding:6px 12px; font-weight:600;
    }
    .stTabs [role="tab"][aria-selected="true"]{
      background:#141a2a; border-color:#54607A; color:#FFFFFF;
      box-shadow: 0 8px 20px rgba(0,0,0,.22) inset;
    }

    /* ===== Reliability chips ===== */
    .chip-row{ margin:6px 0 8px 0; }
    .chip{
      display:inline-block; padding:2px 8px; border:1px solid #2A2F3A; border-radius:999px;
      font-size:12px; color:#C9CDD3; background:#10141E; margin-right:6px; margin-bottom:6px;
    }
    </style>
    """, unsafe_allow_html=True)
