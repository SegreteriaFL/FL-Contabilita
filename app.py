import streamlit as st
from sezioni import (
    mostra_prima_nota,
    mostra_dashboard,
    mostra_rendiconto,
    mostra_nuovo_movimento,
    mostra_saldi_cassa
)

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
sezione = st.sidebar.radio("Naviga", [
    "Prima Nota",
    "Dashboard",
    "Rendiconto ETS",
    "➕ Nuovo Movimento",
    "✏️ Saldi Cassa"
])

# === Contenuto dinamico ===
if sezione == "Prima Nota":
    mostra_prima_nota(ruolo)
elif sezione == "Dashboard":
    mostra_dashboard()
elif sezione == "Rendiconto ETS":
    mostra_rendiconto()
elif sezione == "➕ Nuovo Movimento":
    mostra_nuovo_movimento(ruolo)
elif sezione == "✏️ Saldi Cassa":
    mostra_saldi_cassa(ruolo)
