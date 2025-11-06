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

import io
import pandas as pd
import streamlit as st

def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None or getattr(df, "empty", True):
        return b""
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def download_buttons(
    news_df=None, gdelt_df=None, markets_df=None,
    air_df=None, trends_df=None, reddit_df=None
):
    # One centered row; only render buttons that have data
    cols = st.columns([1,1,1,1,1], gap="small")

    idx = 0
    def _place(label, df):
        nonlocal idx
        if df is None or getattr(df, "empty", True):
            return
        with cols[idx % len(cols)]:
            st.download_button(
                label=label,
                data=_df_to_csv_bytes(df),
                file_name=label.lower().replace(" ", "_") + ".csv",
                mime="text/csv",
                use_container_width=True
            )
        idx += 1

    _place("Download News CSV", news_df)
    _place("Download GDELT CSV", gdelt_df)
    _place("Download Markets CSV", markets_df)
    _place("Download Air Traffic CSV", air_df)
    _place("Download Trends CSV", trends_df)
    _place("Download Reddit CSV", reddit_df)

# src/exporters.py
import os
import pandas as pd

def export_us_snapshot(news_df, trends_df, macro_df, bri_df, out_dir="exports"):
    os.makedirs(out_dir, exist_ok=True)
    ts = pd.Timestamp.utcnow().strftime("%Y%m%dT%H%M%SZ")
    if news_df is not None and not news_df.empty:
        news_df.to_csv(os.path.join(out_dir, f"us_news_{ts}.csv"), index=False)
    if trends_df is not None and not trends_df.empty:
        trends_df.to_csv(os.path.join(out_dir, f"us_trends_{ts}.csv"), index=False)
    if macro_df is not None and not macro_df.empty:
        macro_df.to_csv(os.path.join(out_dir, f"us_macro_{ts}.csv"), index=False)
    if bri_df is not None and not bri_df.empty:
        bri_df.to_csv(os.path.join(out_dir, f"us_bri_{ts}.csv"), index=False)

