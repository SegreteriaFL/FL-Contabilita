# Funge!
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
    df["Index"] = df.index + 2

    st.title("📒 Prima Nota")
    col1, col2 = st.columns(2)
    centri = df["Centro"].dropna().unique().tolist()
    mesi = sorted(df["Data"].dropna().str[:7].unique())

    centro_sel = col1.selectbox("Filtro Centro", ["Tutti"] + centri)
    mese_sel = col2.selectbox("Filtro Mese", ["Tutti"] + mesi)

    if centro_sel != "Tutti":
        df = df[df["Centro"] == centro_sel]
    if mese_sel != "Tutti":
        df = df[df["Data"].str.startswith(mese_sel)]

    st.dataframe(df.drop(columns=["Index"]))

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Esporta CSV", data=csv, file_name="prima_nota.csv", mime="text/csv")

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
                centri_rif = [r[0] for r in ws["centri"].get_all_values()]
                centro = st.selectbox("Centro", ["— Seleziona centro —"] + centri_rif)
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
                        try: st.rerun()
                        except: st.experimental_rerun()

        st.subheader("🛠 Modifica o Cancella Movimento")
        riga_sel = st.selectbox("Seleziona riga da modificare/cancellare", df["Index"].tolist())
        selected = df[df["Index"] == riga_sel].iloc[0]
        with st.form("modifica"):
            nuova_data = st.date_input("Data", pd.to_datetime(selected["Data"]))
            nuova_causale = st.text_input("Causale", selected["Causale"])
            nuovo_centro = st.text_input("Centro", selected["Centro"])
            nuova_cassa = st.text_input("Cassa", selected["Cassa"])
            nuovo_importo = st.number_input("Importo", value=float(selected["Importo"]))
            nuova_descrizione = st.text_input("Descrizione", selected["Descrizione"])
            nuove_note = st.text_area("Note", selected["Note"])
            col_mod, col_del = st.columns(2)
            if col_mod.form_submit_button("💾 Salva modifiche"):
                ws["movimenti"].update(f"A{riga_sel}:G{riga_sel}", [[str(nuova_data), nuova_causale, nuovo_centro, nuova_cassa, nuovo_importo, nuova_descrizione, nuove_note]])
                st.success("Movimento aggiornato.")
                try: st.rerun()
                except: st.experimental_rerun()
            if col_del.form_submit_button("🗑 Cancella riga"):
                ws["movimenti"].delete_rows(riga_sel)
                st.success("Riga eliminata.")
                try: st.rerun()
                except: st.experimental_rerun()

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
        if not entrate.empty: entrate.plot(kind="bar", ax=ax, label="Entrate", color="green")
        if not uscite.empty: uscite.plot(kind="bar", ax=ax, label="Uscite", color="red")
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
    saldo_movimenti = entrate + uscite
    st.metric("Totale Entrate", f"{entrate:,.2f} €")
    st.metric("Totale Uscite", f"{-uscite:,.2f} €")
    st.metric("Saldo Finale", f"{saldo_movimenti:,.2f} €")

    st.subheader("🏦 Confronto con estratti conto")
    estratti = pd.DataFrame(ws["estratti"].get_all_records())
    estratti["Saldo dichiarato"] = pd.to_numeric(estratti["Saldo dichiarato"], errors="coerce")
    saldi_cassa = df.groupby("Cassa")["Importo"].sum().reset_index().rename(columns={"Importo": "Saldo movimenti"})
    confronto = pd.merge(saldi_cassa, estratti, on="Cassa", how="outer").fillna(0)
    confronto["Delta"] = confronto["Saldo movimenti"] - confronto["Saldo dichiarato"]
    st.dataframe(confronto)

    if not confronto["Delta"].between(-1e-2, 1e-2).all():
        st.error("⚠️ Attenzione: i saldi non coincidono!")
    else:
        st.success("✅ Tutto torna: prova del 9 superata!")
