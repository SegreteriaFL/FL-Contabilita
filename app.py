# App funge!
import streamlit as st
from sezioni import mostra_prima_nota, mostra_dashboard, mostra_rendiconto

st.set_page_config(page_title="Contabilita ETS", layout="wide")

# Menu simulato (puoi sostituire con login reale in futuro)
ruolo = st.sidebar.selectbox("Ruolo", ["lettore", "tesoriere", "superadmin"], index=1)

# Menu semplice con radio
pagina = st.sidebar.radio("Naviga", ["📒 Prima Nota", "📊 Dashboard", "📄 Rendiconto ETS"])

if pagina == "📒 Prima Nota":
    mostra_prima_nota(ruolo)
elif pagina == "📊 Dashboard":
    mostra_dashboard()
elif pagina == "📄 Rendiconto ETS":
    mostra_rendiconto()
