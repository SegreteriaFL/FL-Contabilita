import streamlit as st
import pandas as pd
import gspread
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from google.oauth2 import service_account
from datetime import datetime

# --- Connessione a Google Sheets ---
@st.cache_resource
def get_worksheet():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(credentials)
    sh = gc.open("Prima Nota 2024")
    return sh.worksheet("prima_nota_2024")

# --- Caricamento dati ---
def load_data():
    ws = get_worksheet()
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    df["Importo"] = df["Importo"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0.0)
    return df, ws

# --- Salvataggio dati aggiornati ---
def update_sheet(dataframe):
    worksheet = get_worksheet()
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())

# --- Sezione: Prima Nota ---
def mostra_prima_nota():
    st.header("📒 Prima Nota")

    df, ws = load_data()

    df_display = df.copy()
    df_display["Importo"] = df_display["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".")

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection("single")
    gb.configure_grid_options(domLayout='normal')
    gb.configure_pagination()
    grid_options = gb.build()

    custom_css = {
        ".ag-row-green": {"background-color": "#d4f7dc !important"},
        ".ag-row-red": {"background-color": "#f7d4d4 !important"}
    }

    def get_row_style(row):
        return 'ag-row-green' if row["Importo"].replace(".", "").replace(",", ".").startswith("-") == False else 'ag-row-red'

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=True,
        custom_css=custom_css,
        getRowStyle=get_row_style,
    )

    selected = grid_response["selected_rows"]

    col1, col2 = st.columns(2)

    with col1:
        if selected:
            st.success("Hai selezionato una riga.")
            if st.button("✏️ Modifica riga"):
                riga = selected[0]
                index = df_display.index[df_display["Data"] == riga["Data"]].tolist()[0]

                with st.form("modifica"):
                    st.subheader("Modifica movimento")
                    nuova_data = st.date_input("Data", datetime.strptime(riga["Data"], "%Y-%m-%d"))
                    nuova_causale = st.text_input("Causale", riga["Causale"])
                    nuovo_centro = st.text_input("Centro", riga["Centro"])
                    nuovo_importo = st.text_input("Importo", riga["Importo"])
                    nuova_descrizione = st.text_input("Descrizione", riga["Descrizione"])
                    nuova_cassa = st.text_input("Cassa", riga["Cassa"])
                    nuove_note = st.text_input("Note", riga["Note"])

                    submit = st.form_submit_button("💾 Salva modifiche")
                    if submit:
                        parsed_importo = float(nuovo_importo.replace(".", "").replace(",", "."))
                        df.loc[index] = [
                            nuova_data.strftime("%Y-%m-%d"),
                            nuova_causale,
                            nuovo_centro,
                            parsed_importo,
                            nuova_descrizione,
                            nuova_cassa,
                            nuove_note,
                        ]
                        update_sheet(df)
                        st.success("Riga aggiornata con successo.")
                        st.experimental_rerun()

        else:
            st.info("Seleziona una riga per modificarla o eliminarla.")

    with col2:
        if selected and st.button("🗑️ Elimina riga"):
            riga = selected[0]
            df = df[~((df["Data"] == riga["Data"]) & (df["Descrizione"] == riga["Descrizione"]) & (df["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".") == riga["Importo"]))]
            update_sheet(df)
            st.success("Riga eliminata.")
            st.experimental_rerun()
