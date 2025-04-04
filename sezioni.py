from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
import matplotlib.pyplot as plt
import time

SHEET_ID = "1Jg5g27twiVixfA8U10HvaTJ2HbAWS_YcbNB9VWdFwxo"

def format_euro(valore):
    try:
        return f"{valore:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    except:
        return valore

def parse_italian_number(val):
    val = str(val).strip()
    val = val.replace(" ", "").replace("\t", "")
    if "," in val:
        val = val.replace(".", "").replace(",", ".")
    return round(float(val), 2)

@st.cache_resource
def get_worksheet():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    return {
        "movimenti": sheet.worksheet("prima_nota"),
        "causali": sheet.worksheet("rif causale"),
        "centri": sheet.worksheet("rif centro"),
        "casse": sheet.worksheet("rif cassa"),
        "estratti": sheet.worksheet("estratti_conto")
    }

def mostra_prima_nota(ruolo):
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce")
    df["Importo"] = df["Importo"].apply(format_euro)
    st.title("📒 Prima Nota")
    
    
    # Filtro dinamico
    filtro_mese = st.selectbox("📅 Filtra per mese", options=["Tutti"] + sorted(df["Data"].str[:7].unique().tolist()))

    if filtro_mese != "Tutti":
        df = df[df["Data"].str.startswith(filtro_mese)]

    # Colori: entrate verdi, uscite rosse (basato su segno importo)
    def colore_riga(row):
        return "background-color: #ffe6e6;" if row["Importo"] < 0 else "background-color: #e6ffe6;"

    styled_df = df.style.apply(lambda x: [colore_riga(x)], axis=1)

    # Aggiungiamo colonne per azioni (non cliccabili ma visive)
    df["Modifica"] = "✏️"
    df["Elimina"] = "🗑️"

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination()
    gb.configure_default_column(editable=False, groupable=True)
    gb.configure_column("Modifica", header_name="✏️", width=80)
    gb.configure_column("Elimina", header_name="🗑️", width=80)
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        height=600,
        reload_data=True
    )

    selected = grid_response["selected_rows"]
    if selected:
        riga = selected[0]
        idx = df.index[df["Data"] == riga["Data"]].tolist()[0] + 2  # +2 per header
        if st.button("❌ Conferma eliminazione riga selezionata"):
            mov_ws = get_worksheet()["movimenti"]
            mov_ws.delete_rows(idx)
            st.success("Movimento eliminato correttamente.")
            st.rerun()

    # Esporta CSV
    st.download_button("📤 Esporta movimenti filtrati (CSV)", df.to_csv(index=False).encode("utf-8"), "prima_nota.csv", "text/csv")
