import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from sezioni import mostra_prima_nota

st.set_page_config(
    page_title="Gestionale Contabilità ETS",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === Login simulato ===
utenti = {
    "Mario Rossi (superadmin)": "superadmin",
    "Lucia Bianchi (tesoriere)": "tesoriere",
    "Anna Verdi (lettore)": "lettore"
}

st.sidebar.markdown("### 👤 Seleziona utente:")
utente = st.sidebar.selectbox("Utente:", list(utenti.keys()))
ruolo = utenti[utente]
st.sidebar.markdown(f"**Ruolo:** `{ruolo}`")

# === Navigazione ===
st.sidebar.markdown("### 📁 Sezioni")
sezione = st.sidebar.radio("Naviga", ["Prima Nota"])  # Solo sezione stabile per ora

# === Contenuto dinamico ===
if sezione == "Prima Nota":
    mostra_prima_nota(ruolo)