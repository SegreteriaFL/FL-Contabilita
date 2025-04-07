import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SHEET_ID = "1Jg5g27twiVixfA8U10HvaTJ2HbAWS_YcbNB9VWdFwxo"


def get_worksheet():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet("prima_nota")


def load_data():
    ws = get_worksheet()
    records = ws.get_all_records()
    if not records:
        raise ValueError("Il foglio 'prima_nota' è vuoto o senza intestazione valida.")
    df = pd.DataFrame(records)
    if "Importo" not in df.columns:
        raise KeyError("Colonna 'Importo' non trovata. Verifica l'intestazione del foglio.")
    df["Importo"] = df["Importo"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0.0)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")
    df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")
    return df, ws


def update_sheet(dataframe):
    worksheet = get_worksheet()
    clean_df = dataframe.fillna("")  # FIX: sostituisce NaN con stringa vuota
    worksheet.clear()
    worksheet.update([clean_df.columns.values.tolist()] + clean_df.values.tolist())


def mostra_prima_nota(ruolo):
    st.header("\ud83d\udcd2 Prima Nota")

    try:
        df, ws = load_data()
        df_display = df.copy()
        df_display["Importo"] = df_display["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".")
        df_display["\u2714\ufe0f Seleziona"] = False

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=["Data", "Mese"],
            column_config={
                "\u2714\ufe0f Seleziona": st.column_config.CheckboxColumn(required=False)
            }
        )

        selezionate = edited_df[edited_df["\u2714\ufe0f Seleziona"] == True]

        st.divider()
        st.subheader("\ud83d\udee0\ufe0f Azioni disponibili")

        if len(selezionate) == 1:
            riga = selezionate.iloc[0]
            st.success("\u2705 Riga selezionata:")
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

                submit = st.form_submit_button("\ud83d\udcc2 Salva modifiche")
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
                        st.success("\u2705 Modifica salvata.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error("\u274c Errore durante la modifica.")
                        st.exception(e)

            if st.button("\ud83d\udd1d\ufe0f Elimina riga"):
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
                    st.success("\ud83d\udd1d\ufe0f Riga eliminata.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("\u274c Errore durante eliminazione.")
                    st.exception(e)

        elif len(selezionate) > 1:
            st.warning("\u2757 Seleziona solo una riga per eseguire le azioni.")
        else:
            st.info("\u2139\ufe0f Nessuna riga selezionata.")

    except Exception as e:
        st.error("\u274c Errore generale nella sezione Prima Nota.")
        st.exception(e)
