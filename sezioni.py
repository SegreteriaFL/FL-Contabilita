import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SHEET_ID = "1Jg5g27twiVixfA8U10HvaTJ2HbAWS_YcbNB9VWdFwxo"

def get_worksheet(nome="prima_nota"):
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(nome)

def leggi_riferimenti(nome_foglio):
    try:
        ws = get_worksheet(nome_foglio)
        valori = ws.col_values(1)
        return [v for v in valori if v.strip() != "" and v != "Valore"]
    except:
        return []

def load_data():
    ws = get_worksheet()
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    def parse_importo(x):
        try:
            if isinstance(x, (int, float)):
                return float(x)
            x = str(x).strip().replace("€", "").replace(" ", "")
            x = x.replace(".", "").replace(",", ".")
            return float(x)
        except Exception:
            return 0.0

    df["Importo"] = df["Importo"].apply(parse_importo)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")
    df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")
    return df, ws

def update_sheet(dataframe):
    worksheet = get_worksheet()
    worksheet.clear()
    worksheet.update([dataframe.columns.values.tolist()] + dataframe.fillna("").values.tolist())

def mostra_prima_nota(ruolo):
    st.header("📒 Prima Nota")

    try:
        df, ws = load_data()
        df_display = df.copy()
        df_display["Importo"] = df_display["Importo"].map(lambda x: "€ {:,.2f}".format(x).replace(",", "X").replace(".", ",").replace("X", "."))
        df_display["Seleziona"] = False

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=["Data", "Mese"],
            column_order=[col for col in df_display.columns if col != "Mese"],
            column_config={"Seleziona": st.column_config.CheckboxColumn(required=False)}
        )

        selezionate = edited_df[edited_df["Seleziona"] == True]

        st.divider()
        st.subheader("🛠️ Azioni disponibili")

        if len(selezionate) == 1:
            riga = selezionate.iloc[0]
            st.success("✅ Riga selezionata:")
            st.json(riga.to_dict())

        if len(selezionate) > 1:
            st.warning("❗ Seleziona solo una riga per eseguire le azioni.")
        else:
            st.info("ℹ️ Nessuna riga selezionata.")

        st.divider()
        st.markdown("### ➕ Inserisci un nuovo movimento")
        if st.button("Aggiungi movimento dalla Prima Nota"):
            st.session_state["nuovo_mov_inserito"] = False
            st.session_state["page"] = "➕ Nuovo Movimento"
            st.experimental_rerun()

    except Exception as e:
        st.error("❌ Errore generale nella sezione Prima Nota.")
        st.exception(e)

def mostra_dashboard():
    st.header("📊 Dashboard")
    st.warning("🛠️ Sezione in lavorazione.")

def mostra_rendiconto():
    st.header("📑 Rendiconto ETS")
    try:
        df, _ = load_data()
        entrate = df[df["Importo"] > 0]["Importo"].sum()
        uscite = -df[df["Importo"] < 0]["Importo"].sum()
        saldo_finale = entrate - uscite

        st.metric("Entrate totali", f"€ {entrate:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("Uscite totali", f"€ {uscite:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("Saldo finale", f"€ {saldo_finale:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        try:
            foglio_saldi = get_worksheet("saldi estratto conto")
            df_saldi = pd.DataFrame(foglio_saldi.get_all_records())
            if not df_saldi.empty and "Estratto conto" in df_saldi.columns:
                totale_estratti = df_saldi["Estratto conto"].astype(float).sum()
                st.metric("Totale Estratti Conto", f"€ {totale_estratti:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                delta = saldo_finale - totale_estratti
                st.metric("Differenza (Prova del 9)", f"€ {delta:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                if abs(delta) < 0.01:
                    st.success("✅ Saldo combacia con gli estratti conto.")
                else:
                    st.warning("⚠️ Differenza riscontrata tra saldo e totale estratti conto.")
        except Exception:
            st.warning("❗ Foglio 'saldi estratto conto' non trovato o non leggibile.")
    except Exception as e:
        st.error("Errore nel rendiconto.")
        st.exception(e)

def mostra_nuovo_movimento(ruolo):
    st.header("➕ Nuovo Movimento")
    try:
        opzioni_cassa = leggi_riferimenti("rif cassa")
        opzioni_causale = leggi_riferimenti("rif causale")
        opzioni_centro = leggi_riferimenti("rif centro")

        if "nuovo_mov_inserito" not in st.session_state:
            st.session_state["nuovo_mov_inserito"] = False
        if "submit_disabled" not in st.session_state:
            st.session_state["submit_disabled"] = False

        if not st.session_state["nuovo_mov_inserito"]:
            with st.form("nuovo_movimento"):
                data = st.date_input("Data")
                causale = st.selectbox("Causale", opzioni_causale, index=None)
                centro = st.selectbox("Centro", opzioni_centro, index=None)
                importo = st.text_input("Importo", "")
                descrizione = st.text_input("Descrizione", "")
                cassa = st.selectbox("Cassa", opzioni_cassa, index=None)
                note = st.text_input("Note", "")
                submitted = st.form_submit_button("Aggiungi", disabled=st.session_state["submit_disabled"])

            if submitted:
                try:
                    st.session_state["submit_disabled"] = True
                    parsed = float(importo.replace(".", "").replace(",", "."))
                    nuova_riga = [
                        data.strftime("%d/%m/%Y"),
                        causale,
                        centro,
                        parsed,
                        descrizione,
                        cassa,
                        note,
                        data.strftime("%Y-%m")
                    ]
                    df, _ = load_data()
                    df.loc[len(df)] = nuova_riga
                    update_sheet(df)
                    st.session_state["nuovo_mov_inserito"] = True
                    st.success("✅ Movimento aggiunto correttamente.")
                    st.session_state["submit_disabled"] = False
                except Exception as e:
                    st.error("Errore durante inserimento.")
                    st.exception(e)
                    st.session_state["submit_disabled"] = False
        else:
            st.button("➕ Inserisci nuovo movimento", on_click=lambda: st.session_state.update(nuovo_mov_inserito=False))
    except Exception as e:
        st.error("Errore nell'inserimento movimento.")
        st.exception(e)

def mostra_saldi_cassa(ruolo):
    st.header("✏️ Saldi Cassa")
    st.warning("🛠️ UX migliorata in arrivo. Il confronto è ora visibile nel Rendiconto ETS.")