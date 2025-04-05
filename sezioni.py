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
        "estratti": sheet.worksheet("estratti_conto")
    }

def mostra_prima_nota(ruolo):
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    st.title("📒 Prima Nota")
    st.dataframe(df)

def mostra_dashboard():
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    st.title("📊 Dashboard")

    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce")
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")

    entrate = df[df["Importo"] > 0].groupby("Mese")["Importo"].sum()
    uscite = df[df["Importo"] < 0].groupby("Mese")["Importo"].sum()

    if not entrate.empty or not uscite.empty:
        st.subheader("📈 Andamento mensile")
        fig, ax = plt.subplots()
        entrate.plot(kind="bar", ax=ax, color="green", label="Entrate")
        uscite.plot(kind="bar", ax=ax, color="red", label="Uscite")
        ax.legend()
        st.pyplot(fig)
    else:
        st.info("Nessun dato da visualizzare.")

def mostra_rendiconto():
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    st.title("📄 Rendiconto ETS")

    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce")

    entrate = df[df["Importo"] > 0]["Importo"].sum()
    uscite = df[df["Importo"] < 0]["Importo"].sum()
    saldo_movimenti = entrate + uscite

    st.metric("Totale Entrate", f"{entrate:,.2f} €")
    st.metric("Totale Uscite", f"{-uscite:,.2f} €")
    st.metric("Saldo Finale", f"{saldo_movimenti:,.2f} €")

    try:
        estratti = pd.DataFrame(ws["estratti"].get_all_records())
        estratti["Saldo dichiarato"] = pd.to_numeric(estratti["Saldo dichiarato"], errors="coerce")
        totale_estratti = estratti["Saldo dichiarato"].sum()
        st.metric("Totale Saldi Cassa Dichiarati", f"{totale_estratti:,.2f} €")

        saldi_cassa = df.groupby("Cassa")["Importo"].sum().reset_index().rename(columns={"Importo": "Saldo movimenti"})
        confronto = pd.merge(saldi_cassa, estratti, on="Cassa", how="outer").fillna(0)
        confronto["Delta"] = confronto["Saldo movimenti"] - confronto["Saldo dichiarato"]

        st.dataframe(confronto)

        if not confronto["Delta"].between(-1e-2, 1e-2).all():
            st.error("⚠️ Attenzione: i saldi non coincidono!")
        else:
            st.success("✅ Tutto torna: prova del 9 superata!")

    except Exception as e:
        st.info("💡 Nessun estratto conto caricato. Aggiungilo nel foglio `estratti_conto`.")
