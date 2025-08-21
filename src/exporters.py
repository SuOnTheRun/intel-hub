import io
from datetime import datetime
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def _make_pdf_brief(kpis: dict, title: str = "Strategic Intelligence Brief") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("Helvetica-Bold", 16); c.drawString(40, y, title); y -= 24
    c.setFont("Helvetica", 10); c.drawString(40, y, f"Generated: {datetime.utcnow():%Y-%m-%d %H:%M UTC}"); y -= 24
    for k, v in kpis.items():
        c.setFont("Helvetica-Bold", 12); c.drawString(40, y, f"{k.replace('_',' ').title()}: "); 
        c.setFont("Helvetica", 12); c.drawString(220, y, str(v)); y -= 18
    y -= 12
    c.setFont("Helvetica", 9); c.drawString(40, y, "Note: Full tables (news, markets, mobility) are exported as CSV via individual buttons in the app.")
    c.showPage(); c.save()
    return buf.getvalue()

def download_buttons(news_df=None, gdelt_df=None, markets_df=None, air_df=None, trends_df=None, reddit_df=None):
    # Minimal KPI snapshot (computed in app, available via st.session_state if needed)
    kpis = {
        "total_reports": 0 if news_df is None else len(news_df),
        "gdelt_reports": 0 if gdelt_df is None else len(gdelt_df),
        "markets_rows": 0 if markets_df is None else len(markets_df),
        "aircraft_rows": 0 if air_df is None else len(air_df),
    }
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    with col1:
        if news_df is not None and not news_df.empty:
            st.download_button("Download News CSV", _df_to_csv_bytes(news_df), "news.csv", mime="text/csv")
    with col2:
        if gdelt_df is not None and not gdelt_df.empty:
            st.download_button("Download GDELT CSV", _df_to_csv_bytes(gdelt_df), "gdelt.csv", mime="text/csv")
    with col3:
        if markets_df is not None and not markets_df.empty:
            st.download_button("Download Markets CSV", _df_to_csv_bytes(markets_df), "markets.csv", mime="text/csv")
    with col4:
        if air_df is not None and not air_df.empty:
            st.download_button("Download Air Traffic CSV", _df_to_csv_bytes(air_df), "air_traffic.csv", mime="text/csv")
    with col5:
        if trends_df is not None and not trends_df.empty:
            st.download_button("Download Trends CSV", _df_to_csv_bytes(trends_df), "trends.csv", mime="text/csv")
    with col6:
        if reddit_df is not None and not reddit_df.empty:
            st.download_button("Download Reddit CSV", _df_to_csv_bytes(reddit_df), "reddit.csv", mime="text/csv")
    with col7:
        st.download_button("Export PDF Brief", _make_pdf_brief(kpis), "intelligence_brief.pdf", mime="application/pdf")
