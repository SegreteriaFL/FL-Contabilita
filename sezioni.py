# commit: reintegrata funzione mostra_prima_nota mancante + tutte le sezioni operative

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

def mostra_prima_nota(ruolo):
    st.header("Prima Nota")
    try:
        df, ws = load_data()
        df_display = df.copy()
        df_display["Importo"] = df_display["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".")
        df_display["Seleziona"] = False

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=["Data", "Mese"],
            column_config={"Seleziona": st.column_config.CheckboxColumn(required=False)}
        )

        selezionate = edited_df[edited_df["Seleziona"] == True]

        st.divider()
        st.subheader("Azioni disponibili")

        if len(selezionate) == 1:
            riga = selezionate.iloc[0]
            st.success("Riga selezionata:")
            st.json(riga.to_dict())

            with st.form("modifica_editor"):
                data_dt = datetime.strptime(riga["Data"], "%d/%m/%Y")
                nuova_data = st.date_input("Data", data_dt)
                nuova_causale = st.text_input("Causale", riga["Causale"])
                nuovo_centro = st.text_input("Centro", riga["Centro"])
                nuovo_importo = st.text_input("Importo", riga["Importo"])
                nuova_descrizione = st.text_input("Descrizione", riga["Descrizione"])
                nuova_cassa = st.text_input("Cassa", riga["Cassa"])
                nuove_note = st.text_input("Note", riga["Note"])

                submit = st.form_submit_button("Salva modifiche")
                if submit:
                    try:
                        parsed_importo = float(nuovo_importo.replace(".", "").replace(",", "."))
                        condizione = (
                            (df["Data"] == riga["Data"]) &
                            (df["Causale"] == riga["Causale"]) &
                            (df["Centro"] == riga["Centro"]) &
                            (df["Descrizione"] == riga["Descrizione"]) &
                            (df["Cassa"] == riga["Cassa"]) &
                            (df["Note"] == riga["Note"])
                        )
                        index = df[condizione].index[0]
                        df.loc[index] = [
                            nuova_data.strftime("%d/%m/%Y"),
                            nuova_causale,
                            nuovo_centro,
                            parsed_importo,
                            nuova_descrizione,
                            nuova_cassa,
                            nuove_note,
                            nuova_data.strftime("%Y-%m")
                        ]
                        update_sheet(df)
                        st.success("Modifica salvata.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error("Errore durante la modifica.")
                        st.exception(e)

            if st.button("Elimina riga"):
                try:
                    condizione = (
                        (df["Data"] == riga["Data"]) &
                        (df["Causale"] == riga["Causale"]) &
                        (df["Centro"] == riga["Centro"]) &
                        (df["Descrizione"] == riga["Descrizione"]) &
                        (df["Cassa"] == riga["Cassa"]) &
                        (df["Note"] == riga["Note"])
                    )
                    df = df[~condizione]
                    update_sheet(df)
                    st.success("Riga eliminata.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Errore durante eliminazione.")
                    st.exception(e)

        elif len(selezionate) > 1:
            st.warning("Seleziona solo una riga per eseguire le azioni.")
        else:
            st.info("Nessuna riga selezionata.")

    except Exception as e:
        st.error("Errore generale nella sezione Prima Nota.")
        st.exception(e)


def mostra_dashboard():
    st.header("Dashboard")
    try:
        df, _ = load_data()
        st.subheader("Totale per centro di costo")
        totali = df.groupby("Centro")["Importo"].sum().sort_values(ascending=False)
        st.bar_chart(totali)
        st.subheader("Totale mensile")
        mensili = df.groupby("Mese")["Importo"].sum()
        st.line_chart(mensili)
    except Exception as e:
        st.error("Errore nella dashboard.")
        st.exception(e)

def mostra_rendiconto():
    st.header("Rendiconto ETS")
    try:
        df, _ = load_data()
        entrate = df[df["Importo"] > 0]["Importo"].sum()
        uscite = -df[df["Importo"] < 0]["Importo"].sum()
        st.metric("Entrate totali", f"€ {entrate:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("Uscite totali", f"€ {uscite:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("Saldo", f"€ {(entrate - uscite):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    except Exception as e:
        st.error("Errore nel rendiconto.")
        st.exception(e)
