# src/app.py
from __future__ import annotations
import streamlit as st

from src.ui_us import render as render_us
from src.ui_markets import render as render_markets

PAGES = {
    "US — Command Center": render_us,
    "Markets & Macro": render_markets,
}

def main():
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("", list(PAGES.keys()), index=0)
    PAGES[choice]()

if __name__ == "__main__":
    main()
