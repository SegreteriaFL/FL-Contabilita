import streamlit as st
import pandas as pd
import gspread
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
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
    df = pd.DataFrame(records)
    df["Importo"] = df["Importo"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0.0)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")
    df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")
    return df, ws

def update_sheet(dataframe):
    worksheet = get_worksheet()
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

def mostra_prima_nota(ruolo):
    st.header("📒 Prima Nota")

    try:
        df, ws = load_data()
        df_display = df.copy()
        df_display["Importo"] = df_display["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".")

        gb = GridOptionsBuilder.from_dataframe(df_display)
        gb.configure_selection("multiple", use_checkbox=True)
        gb.configure_grid_options(domLayout='normal')
        gb.configure_pagination()
        grid_options = gb.build()

        grid_response = AgGrid(
            df_display,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            data_return_mode=DataReturnMode.FILTERED,
            allow_unsafe_jscode=True,
            theme="streamlit"
        )

        selected = grid_response["selected_rows"]

        st.divider()
        st.subheader("🛠️ Azioni disponibili")

        if isinstance(selected, list) and len(selected) == 1:
            riga = selected[0]
            st.success("✅ Riga selezionata:")
            st.json(riga)

            with st.form("modifica_riga"):
                st.subheader("✏️ Modifica movimento")
                data_dt = datetime.strptime(riga["Data"], "%d/%m/%Y")
                nuova_data = st.date_input("Data", data_dt)
                nuova_causale = st.text_input("Causale", riga["Causale"])
                nuovo_centro = st.text_input("Centro", riga["Centro"])
                nuovo_importo = st.text_input("Importo", riga["Importo"])
                nuova_descrizione = st.text_input("Descrizione", riga["Descrizione"])
                nuova_cassa = st.text_input("Cassa", riga["Cassa"])
                nuove_note = st.text_input("Note", riga["Note"])

                submit = st.form_submit_button("💾 Salva modifiche")
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
                        st.success("✅ Modifiche salvate.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error("❌ Errore durante la modifica.")
                        st.exception(e)

            if st.button("🗑️ Elimina riga"):
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
                    st.success("🗑️ Riga eliminata con successo.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("❌ Errore durante l'eliminazione.")
                    st.exception(e)

        elif isinstance(selected, list) and len(selected) > 1:
            st.warning("❗ Seleziona solo una riga per modificare o eliminare.")
        else:
            st.info("ℹ️ Nessuna riga selezionata.")

    except Exception as e:
        st.error("❌ Errore generale nella sezione Prima Nota.")
        st.exception(e)

def mostra_dashboard():
    st.header("📊 Dashboard")
    st.warning("🛠️ Questa sezione è in fase di sviluppo.")

def mostra_rendiconto():
    st.header("📑 Rendiconto ETS")
    st.warning("🛠️ Questa sezione è in fase di sviluppo.")

def mostra_nuovo_movimento(ruolo):
    st.header("➕ Nuovo Movimento")
    st.warning("🛠️ Questa sezione è in fase di sviluppo.")

def mostra_saldi_cassa(ruolo):
    st.header("✏️ Saldi Cassa")
    st.warning("🛠️ Questa sezione è in fase di sviluppo.")
