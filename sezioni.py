
# commit: nuovo movimento usa fogli rif_cassa, rif_causale, rif_centro per i campi a discesa

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SHEET_ID = "1Jg5g27twiVixfA8U10HvaTJ2HbAWS_YcbNB9VWdFwxo"

def get_worksheet(nome="prima_nota"):
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(nome)

def load_data():
    ws = get_worksheet("prima_nota")
    records = ws.get_all_records()
    if not records:
        raise ValueError("Il foglio 'prima_nota' è vuoto o senza intestazione valida.")
    df = pd.DataFrame(records)
    required_columns = ["Data", "Importo"]
    for col in required_columns:
        if col not in df.columns:
            raise KeyError(f"Colonna richiesta '{col}' non trovata nel foglio. Verifica l'intestazione.")
    df["Importo"] = df["Importo"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0.0)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")
    df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")
    return df, ws

def update_sheet(dataframe):
    worksheet = get_worksheet("prima_nota")
    clean_df = dataframe.fillna("")
    worksheet.clear()
    worksheet.update([clean_df.columns.values.tolist()] + clean_df.values.tolist())

def leggi_riferimenti(nome_foglio):
    ws = get_worksheet(nome_foglio)
    valori = ws.col_values(1)
    return [v for v in valori if v.strip() != "" and v.strip().lower() != nome_foglio.lower()]

def mostra_nuovo_movimento(ruolo):
    st.header("Nuovo Movimento")
    try:
        opzioni_cassa = leggi_riferimenti("rif cassa")
        opzioni_causale = leggi_riferimenti("rif causale")
        opzioni_centro = leggi_riferimenti("rif centro")

        with st.form("nuovo_movimento"):
            data = st.date_input("Data")
            causale = st.selectbox("Causale", opzioni_causale)
            centro = st.selectbox("Centro", opzioni_centro)
            importo = st.text_input("Importo")
            descrizione = st.text_input("Descrizione")
            cassa = st.selectbox("Cassa", opzioni_cassa)
            note = st.text_input("Note")
            submit = st.form_submit_button("Aggiungi")

        if submit:
            parsed = float(importo.replace(".", "").replace(",", "."))
            nuova_riga = [
                data.strftime("%d/%m/%Y"),
                causale,
                centro,
                parsed,
                descrizione,
                cassa,
                note,
                data.strftime("%Y-%m")
            ]
            df, _ = load_data()
            df.loc[len(df)] = nuova_riga
            update_sheet(df)
            st.success("Movimento aggiunto.")
            st.experimental_rerun()
    except Exception as e:
        st.error("Errore nell'inserimento movimento.")
        st.exception(e)
