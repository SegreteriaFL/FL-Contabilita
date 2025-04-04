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
        "estratti": sheet.worksheet("estratti_conto")
    }

def mostra_prima_nota(ruolo):
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    st.title("📒 Prima Nota")
    st.dataframe(df)

def mostra_nuovo_movimento(ruolo):
    if ruolo not in ["tesoriere", "superadmin"]:
        st.warning("Accesso negato.")
        return

    st.title("➕ Nuovo Movimento")
    ws = get_worksheet()

    with st.form("form_movimento"):
        data = st.date_input("Data")
        causali = [r[0] for r in ws["causali"].get_all_values()]
        causale = st.selectbox("Causale", ["— Seleziona —"] + causali)
        centri = [r[0] for r in ws["centri"].get_all_values()]
        centro = st.selectbox("Centro", ["— Seleziona —"] + centri)
        casse = [r[0] for r in ws["casse"].get_all_values()]
        cassa = st.selectbox("Cassa", ["— Seleziona —"] + casse)
        importo = st.number_input("Importo", step=1.0)
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
                try: st.rerun()
                except Exception: st.experimental_rerun()

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

    except Exception:
        st.info("💡 Nessun estratto conto caricato. Aggiungilo nel foglio `estratti_conto`.")

def mostra_saldi_cassa(ruolo):
    if ruolo not in ["tesoriere", "superadmin"]:
        st.warning("Accesso negato.")
        return

    st.title("✏️ Saldi Cassa")
    ws = get_worksheet()

    try:
        estratti = pd.DataFrame(ws["estratti"].get_all_records())
        estratti["Saldo dichiarato"] = pd.to_numeric(estratti["Saldo dichiarato"], errors="coerce")

        with st.form("form_saldi"):
            nuove_righe = []
            for riga in estratti.itertuples():
                c1, c2 = st.columns(2)
                nome = c1.text_input(f"Cassa {riga.Index}", riga.Cassa)
                saldo = c2.number_input(f"Saldo {riga.Index}", value=riga._2)
                nuove_righe.append([nome, saldo])
            salva = st.form_submit_button("Salva saldi")
            if salva:
                ws["estratti"].clear()
                ws["estratti"].append_row(["Cassa", "Saldo dichiarato"])
                for r in nuove_righe:
                    ws["estratti"].append_row(r)
                st.success("✅ Saldi aggiornati.")
                try: st.rerun()
                except Exception: st.experimental_rerun()
    except Exception:
        st.info("⚠️ Nessun foglio `estratti_conto` trovato o formattazione errata.")