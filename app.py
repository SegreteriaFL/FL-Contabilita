# commit: fix ImportError debug - aggiunto blocco try/except globale per mostrare eccezioni interne

import streamlit as st

# DEBUG: cattura errori generici oscurati da Streamlit Cloud
try:
    from sezioni import (
        mostra_prima_nota,
        mostra_dashboard,
        mostra_rendiconto,
        mostra_nuovo_movimento,
        mostra_saldi_cassa
    )
except Exception as e:
    st.error("\u274c Errore durante l'import di 'sezioni.py'")
    st.exception(e)
    st.stop()

st.set_page_config(
    page_title="Gestionale Contabilit\u00e0 ETS",
    page_icon="\ud83d\udcd2",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === Login simulato ===
utenti = {
    "Mario Rossi (superadmin)": "superadmin",
    "Lucia Bianchi (tesoriere)": "tesoriere",
    "Anna Verdi (lettore)": "lettore"
}

st.sidebar.markdown("### \ud83d\udc64 Seleziona utente:")
utente = st.sidebar.selectbox("Utente:", list(utenti.keys()))
ruolo = utenti[utente]
st.sidebar.markdown(f"**Ruolo:** `{ruolo}`")

# === Navigazione ===
st.sidebar.markdown("### \ud83d\udcc1 Sezioni")
sezione = st.sidebar.radio("Naviga", [
    "Prima Nota",
    "Dashboard",
    "Rendiconto ETS",
    "\u2795 Nuovo Movimento",
    "\u270f\ufe0f Saldi Cassa"
])

# === Contenuto dinamico ===
if sezione == "Prima Nota":
    mostra_prima_nota(ruolo)
elif sezione == "Dashboard":
    mostra_dashboard()
elif sezione == "Rendiconto ETS":
    mostra_rendiconto()
elif sezione == "\u2795 Nuovo Movimento":
    mostra_nuovo_movimento(ruolo)
elif sezione == "\u270f\ufe0f Saldi Cassa":
    mostra_saldi_cassa(ruolo)
