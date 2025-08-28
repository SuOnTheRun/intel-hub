import streamlit as st

def apply_page_style():
    st.markdown("""
    <style>
      /* Layout */
      .block-container { padding-top: 1.2rem; padding-bottom: 2.4rem; }

      /* Hero (title area) */
      .hero{ display:flex; flex-direction:column; align-items:center; margin:6px 0 12px 0; }
      .hero-title{
        font-family: ui-serif, Georgia, "Times New Roman", serif;
        font-size: 36px; font-weight: 800; letter-spacing: .6px;
        color: #e9edf4;
      }
      .hero-sub{
        margin-top: 2px; font-size: 12.5px; color:#a6aebe; font-style: italic;
      }

      /* Section header & separators (softer, not black) */
      .section-head{
        display:flex; align-items:baseline; justify-content:space-between;
        border-bottom:1px solid #3a4150; padding:6px 2px 8px 2px; margin:8px 2px 14px 2px;
      }
      .section-title{ font-size:18px; font-weight:600; letter-spacing:.2px; }
      .section-note{ font-size:12px; color:#9aa3af; font-style:italic; }

      /* Soft card for KPI area */
      .soft-card{
        border:1px solid #2c3445; border-radius:16px;
        background: #0f141b; padding:12px 14px; margin:6px 0 16px 0;
      }

      /* Alerts bar (subtle amber) */
      .alert-strip{
        background: linear-gradient(180deg,#1a1913,#15140f);
        border:1px solid #4b3e1d; color:#f0e6c8;
        border-radius:12px; padding:8px 12px; margin:4px 0 12px 0;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
      }

      /* Luxe buttons (download/link/normal) */
      .stDownloadButton > button,
      .stLinkButton > button,
      .stButton > button {
        background: linear-gradient(180deg,#171e27,#0f141b);
        color:#e9edf4 !important;
        border:1px solid #344055 !important;
        border-radius:14px !important;
        padding:8px 16px !important;
        font-weight:600 !important;
        letter-spacing:.2px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.03) !important;
        transition: transform .08s ease, box-shadow .18s ease, border-color .18s ease !important;
      }
      .stDownloadButton > button:hover,
      .stLinkButton > button:hover,
      .stButton > button:hover {
        transform: translateY(-1px);
        border-color:#56617a !important;
        box-shadow: 0 6px 16px rgba(0,0,0,.30) !important;
      }
      .stDownloadButton, .stLinkButton, .stButton { margin-right: 6px !important; }

      /* Tabs – distinct from buttons */
      .stTabs [role="tablist"]{ gap:8px; border-bottom:1px solid #3a4150; padding-bottom:6px; }
      .stTabs [role="tab"]{
        background:#121824; border:1px solid #2f3a4a; color:#e7ebf2;
        border-radius:12px; padding:6px 12px; font-weight:500;
      }
      .stTabs [role="tab"][aria-selected="true"]{ background:#0f141b; border-color:#56617a; }

      /* Chips for tiny labels if you need them */
      .chip-row{ margin:6px 0 8px 0; }
      .chip{
        display:inline-block; padding:2px 8px; border:1px solid #2a3140; border-radius:999px;
        font-size:12px; color:#c9cfd6; background:#0f141b; margin-right:6px; margin-bottom:6px;
      }
    </style>
        st.markdown("""
    <style>
      /* Tabs — slim, underline style */
      [data-testid="stTabs"] button[role="tab"]{
        background: transparent !important;
        border: none !important;
        padding: 8px 14px !important;
        margin-right: 8px !important;
        color: #5c6570 !important;
        font-weight: 600 !important;
      }
      [data-testid="stTabs"] button[aria-selected="true"]{
        color: #0f172a !important;
        border-bottom: 2px solid #c1a96b !important; /* muted gold accent */
      }

      /* Ghost icon buttons */
      .ghost-btn{
        border: 1px solid #1f2937;
        background: transparent;
        color: #1f2937;
        padding: 6px 10px;
        border-radius: 10px;
        font-weight: 600;
      }
      .ghost-btn:hover{ background:#1118270f; }

      /* Alert strip */
      .alert-strip{
        background:#1a1a1a;
        color:#e7e5e4;
        border-radius:10px;
        padding:10px 14px;
        font-weight:600;
      }

      /* KPI cards */
      .kpi-card{
        background:#ffffff;
        border:1px solid #e5e7eb;
        border-radius:16px;
        padding:14px 16px;
        box-shadow: 0 0 20px rgba(0,0,0,0.03);
      }
      .kpi-label{ color:#64748b; font-size:12px; text-transform:uppercase; letter-spacing:.06em;}
      .kpi-value{ font-size:28px; font-weight:800; color:#0f172a;}
      .kpi-delta-up{ color:#0f766e; font-weight:700; }
      .kpi-delta-down{ color:#b91c1c; font-weight:700; }

      /* Status chips */
      .chip{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:700;margin-right:6px}
      .chip-ok{background:#e6f4ea;color:#116149;border:1px solid #bfe3cc}
      .chip-warn{background:#fff4e5;color:#92400e;border:1px solid #f2c97d}
      .chip-bad{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}
    </style>
    """, unsafe_allow_html=True)

    """, unsafe_allow_html=True)
