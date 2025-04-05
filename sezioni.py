import streamlit as st
import pandas as pd
import gspread
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
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
        st.info("🔍 Checkpoint 1: Inizio funzione")
        df, ws = load_data()
        st.success("✅ Caricati dati dal foglio. Righe: " + str(len(df)))

        df_display = df.copy()
        df_display["Importo"] = df_display["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".")

        gb = GridOptionsBuilder.from_dataframe(df_display)
        gb.configure_selection("single")
        gb.configure_grid_options(domLayout='normal')
        gb.configure_pagination()
        grid_options = gb.build()

        st.info("🔍 Checkpoint 2: Prima di AgGrid")

        grid_response = AgGrid(
            df_display,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=True,
            selection_mode="single"
        )

        st.info("🔍 Checkpoint 3: Dopo AgGrid")

        selected = grid_response["selected_rows"]

        with st.expander("🧪 Debug AgGrid"):
            st.write(grid_response)

        col1, col2 = st.columns(2)

        with col1:
            if isinstance(selected, list) and len(selected) > 0:
                st.success("✅ Riga selezionata")
                st.json(selected[0])
            else:
                st.info("ℹ️ Nessuna riga selezionata")

        with col2:
            if isinstance(selected, list) and len(selected) > 0 and st.button("🗑️ Elimina riga"):
                st.warning("🔒 Elimina disattivato in debug")

    except Exception as e:
        st.error("❌ Errore in mostra_prima_nota()")
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
