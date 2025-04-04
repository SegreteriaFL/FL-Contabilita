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
    # Togli lo spazio come migliaia o tab eventualmente
    val = val.replace(" ", "").replace("\t", "")
    if "," in val:
        # caso italiano: 1.234,56
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
    st.dataframe(df)

def mostra_nuovo_movimento(ruolo):
    if ruolo not in ["tesoriere", "superadmin"]:
        st.warning("Accesso negato.")
        return

    if "form_inviato" not in st.session_state:
        st.session_state["form_inviato"] = False

    st.title("➕ Nuovo Movimento")
    ws = get_worksheet()

    if not st.session_state["form_inviato"]:
        with st.form("form_movimento"):
            data = st.date_input("Data")
            causali = [r[0] for r in ws["causali"].get_all_values()]
            causale = st.selectbox("Causale", ["— Seleziona —"] + causali)
            centri = [r[0] for r in ws["centri"].get_all_values()]
            centro = st.selectbox("Centro", ["— Seleziona —"] + centri)
            casse = [r[0] for r in ws["casse"].get_all_values()]
            cassa = st.selectbox("Cassa", ["— Seleziona —"] + casse)
            importo_raw = st.text_input("Importo", value="0,00")
            try:
                importo = parse_italian_number(importo_raw)
            except ValueError:
                importo = 0
                st.warning("⚠️ Inserisci un numero valido (es. 1.234,56)")
            descrizione = st.text_input("Descrizione")
            note = st.text_area("Note")
            invia = st.form_submit_button("Salva")

            if invia:
                if causale.startswith("—") or centro.startswith("—") or cassa.startswith("—"):
                    st.warning("Compila tutti i campi prima di salvare.")
                else:
                    riga = [str(data), causale, centro, cassa, importo, descrizione, note]
                    ws["movimenti"].append_row(riga)
                    st.success("✅ Movimento salvato!")
                    st.session_state["form_inviato"] = True
                    time.sleep(1)
                    st.experimental_rerun()
    else:
        st.info("✅ Movimento salvato. Vai alla sezione '📒 Prima Nota' per vederlo.")
        if st.button("↩️ Torna alla Prima Nota"):
            st.experimental_rerun()

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

    st.metric("Totale Entrate", format_euro(entrate))
    st.metric("Totale Uscite", format_euro(-uscite))
    st.metric("Saldo Finale", format_euro(saldo_movimenti))

    try:
        estratti = pd.DataFrame(ws["estratti"].get_all_records())
        estratti["Saldo dichiarato"] = pd.to_numeric(estratti["Saldo dichiarato"], errors="coerce")
        totale_estratti = estratti["Saldo dichiarato"].sum()
        st.metric("Totale Saldi Cassa Dichiarati", format_euro(totale_estratti))

        saldi_cassa = df.groupby("Cassa")["Importo"].sum().reset_index().rename(columns={"Importo": "Saldo movimenti"})
        confronto = pd.merge(saldi_cassa, estratti, on="Cassa", how="outer").fillna(0)
        confronto["Delta"] = confronto["Saldo movimenti"] - confronto["Saldo dichiarato"]
        confronto["Saldo movimenti"] = confronto["Saldo movimenti"].apply(format_euro)
        confronto["Saldo dichiarato"] = confronto["Saldo dichiarato"].apply(format_euro)
        confronto["Delta"] = confronto["Delta"].apply(format_euro)
        st.dataframe(confronto)

        if not confronto["Delta"].astype(str).str.replace(".", "").str.replace(",", "").astype(float).between(-1e-2, 1e-2).all():
            st.error("⚠️ Attenzione: i saldi non coincidono!")
        else:
            st.success("✅ Tutto torna: prova del 9 superata!")

    except Exception:
        st.info("💡 Nessun estratto conto caricato. Aggiungilo nel foglio `estratti_conto`.")