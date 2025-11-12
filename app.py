# app.py
import streamlit as st
from src.ui_us import render as render_us
from src.theming import set_dark_theme

PAGES = {
    "US — Command Center": render_us,
    # future: "Markets & Macro": render_macro, "Mobility": render_mobility, etc.
}

def main():
    set_dark_theme()
    st.sidebar.title("Intelligence Hub — US")
    choice = st.sidebar.radio("Navigation", list(PAGES.keys()), index=0)
    PAGES[choice]()

if __name__ == "__main__":
    main()
