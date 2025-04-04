import streamlit as st
from sezioni import mostra_prima_nota, mostra_dashboard, mostra_rendiconto
from st_pages import Page, show_pages

st.set_page_config(page_title="Contabilità ETS", layout="wide")

# Menu simulato (puoi sostituire con login reale in futuro)
ruolo = st.sidebar.selectbox("Ruolo", ["lettore", "tesoriere", "superadmin"])

# Mostra le sezioni
show_pages([
    Page("app.py", "📒 Prima Nota", "📒"),
    Page("app.py", "📊 Dashboard", "📊"),
    Page("app.py", "📄 Rendiconto ETS", "📄")
])

pagina = st.sidebar.radio("Naviga", ["📒 Prima Nota", "📊 Dashboard", "📄 Rendiconto ETS"])

if pagina == "📒 Prima Nota":
    mostra_prima_nota(ruolo)
elif pagina == "📊 Dashboard":
    mostra_dashboard()
elif pagina == "📄 Rendiconto ETS":
    mostra_rendiconto()