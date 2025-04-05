import streamlit as st
import pandas as pd
import gspread
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Connessione a Google Sheets ---
def get_worksheet():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(credentials)
        sh = gc.open("Contabilità ETS 2024")  # Nome corretto del file
        return sh.worksheet("prima_nota")     # Nome corretto del foglio
    except Exception as e:
        st.error("❌ Errore durante la connessione a Google Sheets.")
        st.exception(e)
        st.stop()

# --- Caricamento dati ---
def load_data():
    try:
        ws = get_worksheet()
        records = ws.get_all_records()
        df = pd.DataFrame(records)

        df["Importo"] = df["Importo"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0.0)

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df["Mese"] = df["Data"].dt.strftime("%Y-%m")
        df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")

        return df, ws
    except Exception as e:
        st.error("❌ Errore durante il caricamento dei dati.")
        st.exception(e)
        st.stop()

# --- Salvataggio dati aggiornati ---
def update_sheet(dataframe):
    try:
        worksheet = get_worksheet()
        worksheet.clear()
        worksheet.update([dataframe.columns.values.tolist()] + dataframe.values.tolist())
    except Exception as e:
        st.error("❌ Errore durante l'aggiornamento dei dati su Google Sheets.")
        st.exception(e)
        st.stop()

# --- Sezione: Prima Nota ---
def mostra_prima_nota(ruolo):
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
        imp = row["Importo"].replace(".", "").replace(",", ".")
        try:
            return 'ag-row-green' if float(imp) >= 0 else 'ag-row-red'
        except:
            return ''

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
                        parsed_importo = float(nuovo_importo.replace(".", "").replace(",", "."))
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
                        st.success("Riga aggiornata con successo.")
                        st.experimental_rerun()
        else:
            st.info("Seleziona una riga per modificarla o eliminarla.")

    with col2:
        if selected and st.button("🗑️ Elimina riga"):
            riga = selected[0]
            df = df[~((df["Data"] == riga["Data"]) & (df["Descrizione"] == riga["Descrizione"]) & (df_display["Importo"] == riga["Importo"]))]
            update_sheet(df)
            st.success("Riga eliminata.")
            st.experimental_rerun()

# --- Sezioni placeholder ---
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
