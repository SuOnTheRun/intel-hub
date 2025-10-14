import streamlit as st

def inject_css():
    st.markdown("""
    <style>
      /* Quiet luxury trims */
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1200px; }
      .stMarkdown a { text-decoration: none; }
      .kpi{
        border:1px solid #e7e7e4; border-radius:14px; padding:12px; background:#fff;
      }
      .kpi .l{ color:#5a5a5e; font-size:12px; }
      .kpi .v{ font-weight:600; font-size:20px; }
      .kpi .s{ color:#5a5a5e; font-size:12px; }
    </style>
    """, unsafe_allow_html=True)

def kpi(label:str, value:str, sub:str=""):
    st.markdown(f"""
      <div class="kpi">
        <div class="l">{label}</div>
        <div class="v">{value}</div>
        <div class="s">{sub}</div>
      </div>
    """, unsafe_allow_html=True)
