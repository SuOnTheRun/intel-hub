import streamlit as st

BLIS_ACCENT = "#0fb39b"

def inject_css():
    st.markdown(f"""
    <style>
      .block-container {{ padding-top: 1rem; padding-bottom: 2rem; max-width: 1280px; }}
      h1, h2, h3 {{ letter-spacing: .2px; }}
      .kpi {{
        border:1px solid #e7e7e4; border-radius:14px; padding:12px 14px; background:#fff;
        box-shadow: 0 1px 0 rgba(16,17,19,.03);
      }}
      .kpi .l {{ color:#5a5a5e; font-size:12px; margin-bottom:4px; }}
      .kpi .v {{ font-weight:600; font-size:22px; line-height:1.1; }}
      .kpi .s {{ color:#5a5a5e; font-size:12px; margin-top:4px; }}
      .muted {{ color:#5a5a5e; font-size:13px; }}
      .accent {{ color:{BLIS_ACCENT}; }}
      .stMarkdown a {{ text-decoration:none; }}
    </style>
    """, unsafe_allow_html=True)

def kpi(label: str, value: str, sub: str=""):
    st.markdown(f"""
      <div class="kpi">
        <div class="l">{label}</div>
        <div class="v">{value}</div>
        <div class="s">{sub}</div>
      </div>
    """, unsafe_allow_html=True)
