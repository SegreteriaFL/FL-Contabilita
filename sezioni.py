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

    # Sidebar: nuovo movimento
    if ruolo in ["tesoriere", "superadmin"]:
        if st.sidebar.button("➕ Nuovo Movimento"):
            st.session_state.form_visibile = not st.session_state.get("form_visibile", False)

    # Filtri
    col1, col2 = st.columns(2)
    centri = df["Centro"].dropna().unique().tolist()
    mesi = sorted(df["Data"].dropna().str[:7].unique())
    centro_sel = col1.selectbox("Filtro Centro", ["Tutti"] + centri)
    mese_sel = col2.selectbox("Filtro Mese", ["Tutti"] + mesi)
    if centro_sel != "Tutti":
        df = df[df["Centro"] == centro_sel]
    if mese_sel != "Tutti":
        df = df[df["Data"].str.startswith(mese_sel)]

    # Pulsanti azione accanto a ogni riga
    st.write("### Movimenti")
    for i, row in df.iterrows():
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.write(f"{row['Data']} | {row['Causale']} | {row['Centro']} | {row['Cassa']} | {row['Importo']} €")
        with col2:
            if st.button("✏️", key=f"edit_{i}"):
                st.session_state.edit_index = row["Index"]
        with col3:
            if st.button("🗑", key=f"del_{i}"):
                ws["movimenti"].delete_rows(row["Index"])
                st.success("Riga eliminata.")
                try: st.rerun()
                except Exception: st.experimental_rerun()

    # Form inserimento
    if st.session_state.get("form_visibile", False) and ruolo in ["tesoriere", "superadmin"]:
        st.subheader("➕ Inserisci nuovo movimento")
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
                    except Exception: st.experimental_rerun()

    # Modifica movimento
    if st.session_state.get("edit_index") and ruolo in ["tesoriere", "superadmin"]:
        idx = st.session_state.edit_index
        row = df[df["Index"] == idx].iloc[0]
        st.subheader(f"✏️ Modifica Movimento ({row['Data']}, {row['Causale']})")
        with st.form("modifica"):
            nuova_data = st.date_input("Data", pd.to_datetime(row["Data"]))
            nuova_causale = st.text_input("Causale", row["Causale"])
            nuovo_centro = st.text_input("Centro", row["Centro"])
            nuova_cassa = st.text_input("Cassa", row["Cassa"])
            nuovo_importo = st.number_input("Importo", value=float(row["Importo"]))
            nuova_descrizione = st.text_input("Descrizione", row["Descrizione"])
            nuove_note = st.text_area("Note", row["Note"])
            if st.form_submit_button("Salva modifiche"):
                ws["movimenti"].update(f"A{idx}:G{idx}", [[str(nuova_data), nuova_causale, nuovo_centro, nuova_cassa, nuovo_importo, nuova_descrizione, nuove_note]])
                st.success("Movimento aggiornato.")
                del st.session_state.edit_index
                try: st.rerun()
                except Exception: st.experimental_rerun()

def mostra_rendiconto():
    ws = get_worksheet()
    df = pd.DataFrame(ws["movimenti"].get_all_records())
    df.columns = [col.strip() for col in df.columns]
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce")
    entrate = df[df["Importo"] > 0]["Importo"].sum()
    uscite = df[df["Importo"] < 0]["Importo"].sum()
    saldo_movimenti = entrate + uscite

    st.title("📄 Rendiconto ETS")
    st.metric("Totale Entrate", f"{entrate:,.2f} €")
    st.metric("Totale Uscite", f"{-uscite:,.2f} €")
    st.metric("Saldo Finale", f"{saldo_movimenti:,.2f} €")

    # Prova del 9
    st.subheader("🏦 Confronto con estratti conto")
    estratti = pd.DataFrame(ws["estratti"].get_all_records())
    estratti["Saldo dichiarato"] = pd.to_numeric(estratti["Saldo dichiarato"], errors="coerce")
    totale_dichiarato = estratti["Saldo dichiarato"].sum()
    st.metric("Totale Saldi Cassa Dichiarati", f"{totale_dichiarato:,.2f} €")

    saldi_cassa = df.groupby("Cassa")["Importo"].sum().reset_index().rename(columns={"Importo": "Saldo movimenti"})
    confronto = pd.merge(saldi_cassa, estratti, on="Cassa", how="outer").fillna(0)
    confronto["Delta"] = confronto["Saldo movimenti"] - confronto["Saldo dichiarato"]
    st.dataframe(confronto)

    if not confronto["Delta"].between(-1e-2, 1e-2).all():
        st.error("⚠️ Attenzione: i saldi non coincidono!")
    else:
        st.success("✅ Tutto torna: prova del 9 superata!")

    # Form saldi estratto conto
    if "edit_saldo" not in st.session_state:
        st.session_state.edit_saldo = False

    if st.button("✏️ Modifica Saldi Cassa"):
        st.session_state.edit_saldo = not st.session_state.edit_saldo

    if st.session_state.edit_saldo:
        with st.form("mod_saldi"):
            nuove_righe = []
            for riga in estratti.itertuples():
                col1, col2 = st.columns(2)
                cassa = col1.text_input(f"Cassa {riga.Index}", riga.Cassa)
                saldo = col2.number_input(f"Saldo {riga.Index}", value=riga._2)
                nuove_righe.append([cassa, saldo])
            if st.form_submit_button("Salva saldi"):
                ws["estratti"].clear()
                ws["estratti"].append_row(["Cassa", "Saldo dichiarato"])
                for r in nuove_righe:
                    ws["estratti"].append_row(r)
                st.success("✅ Saldi aggiornati.")
                st.session_state.edit_saldo = False
                try: st.rerun()
                except Exception: st.experimental_rerun()