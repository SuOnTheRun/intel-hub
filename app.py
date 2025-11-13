import streamlit as st
from src.ui_us import render as render_us
from src.theming import set_dark_theme
from src.ui_markets import render as render_markets


PAGES = {
    "US — Command Center": render_us,
}

def main():
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio("", ["US — Command Center", "Markets & Macro"])

    if page == "US — Command Center":
        from src.ui_us import render as render_us
        render_us()
    else:
        render_markets()

if __name__ == "__main__":
    main()
