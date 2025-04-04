import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
import matplotlib.pyplot as plt

SHEET_ID = "1Jg5g27twiVixfA8U10HvaTJ2HbAWS_YcbNB9VWdFwxo"

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
    }

def mostra_prima_nota(ruolo):
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())

    st.title("📒 Prima Nota")
    st.dataframe(df)

    if ruolo in ["tesoriere", "superadmin"]:
        if "form_visibile" not in st.session_state:
            st.session_state.form_visibile = False

        if st.button("➕ Nuovo Movimento"):
            st.session_state.form_visibile = not st.session_state.form_visibile

        if st.session_state.form_visibile:
            with st.form("nuovo_movimento"):
                data = st.date_input("Data")
                
                causali = [r[0] for r in ws["causali"].get_all_values()]
                causale = st.selectbox("Causale", ["— Seleziona causale —"] + causali)

                centri = [r[0] for r in ws["centri"].get_all_values()]
                centro = st.selectbox("Centro", ["— Seleziona centro —"] + centri)

                casse = [r[0] for r in ws["casse"].get_all_values()]
                cassa = st.selectbox("Cassa", ["— Seleziona cassa —"] + casse)

                importo = st.number_input("Importo", step=1.0)
                descrizione = st.text_input("Descrizione")
                note = st.text_area("Note")

                submitted = st.form_submit_button("Salva movimento")
                if submitted:
                    if causale.startswith("—") or centro.startswith("—") or cassa.startswith("—"):
                        st.warning("⚠️ Completa tutti i campi prima di salvare.")
                    else:
                        nuova_riga = [str(data), causale, centro, cassa, importo, descrizione, note]
                        ws["movimenti"].append_row(nuova_riga)
                        st.success("✅ Movimento salvato!")
                        st.session_state.form_visibile = False
                        try:
                            st.rerun()
                        except AttributeError:
                            st.experimental_rerun()

def mostra_dashboard():
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    st.title("📊 Dashboard")

    df.columns = [col.strip() for col in df.columns]
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce")
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")

    entrate = df[df["Importo"] > 0].groupby("Mese")["Importo"].sum()
    uscite = df[df["Importo"] < 0].groupby("Mese")["Importo"].sum()

    if not entrate.empty or not uscite.empty:
        st.subheader("Entrate e Uscite mensili")
        fig, ax = plt.subplots()
        if not entrate.empty:
            entrate.plot(kind="bar", ax=ax, label="Entrate", color="green")
        if not uscite.empty:
            uscite.plot(kind="bar", ax=ax, label="Uscite", color="red")
        ax.legend()
        st.pyplot(fig)
    else:
        st.info("Ancora nessun dato da visualizzare.")

def mostra_rendiconto():
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    st.title("📄 Rendiconto ETS")

    df.columns = [col.strip() for col in df.columns]
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce")
    entrate = df[df["Importo"] > 0]["Importo"].sum()
    uscite = df[df["Importo"] < 0]["Importo"].sum()
    saldo = entrate + uscite

    st.metric("Totale Entrate", f"{entrate:,.2f} €")
    st.metric("Totale Uscite", f"{-uscite:,.2f} €")
    st.metric("Saldo Finale", f"{saldo:,.2f} €")