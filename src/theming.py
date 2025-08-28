import streamlit as st

import streamlit as st

def apply_page_style():
    st.markdown("""
<style>
/* Tabs - slim underline style */
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
