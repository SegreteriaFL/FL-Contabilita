# commit: reintegrata funzione mostra_prima_nota mancante + tutte le sezioni operative

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

    ws = get_worksheet("prima_nota")
    records = ws.get_all_records()
    if not records:
        raise ValueError("Il foglio 'prima_nota' è vuoto o senza intestazione valida.")
    df = pd.DataFrame(records)
    required_columns = ["Data", "Importo"]
    for col in required_columns:
        if col not in df.columns:
            raise KeyError(f"Colonna richiesta '{col}' non trovata nel foglio. Verifica l'intestazione.")
    df["Importo"] = df["Importo"].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0.0)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mese"] = df["Data"].dt.strftime("%Y-%m")
    df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")
    return df, ws

def load_data():
    ws = get_worksheet()
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    # Gestione robusta importi (senza locale)
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
    worksheet = get_worksheet("prima_nota")
    clean_df = dataframe.fillna("")
    worksheet.clear()
    worksheet.update([clean_df.columns.values.tolist()] + clean_df.values.tolist())

def leggi_riferimenti(nome_foglio):
    ws = get_worksheet(nome_foglio)
    valori = ws.col_values(1)
    return [v for v in valori if v.strip() != "" and v.strip().lower() != nome_foglio.lower()]

def mostra_prima_nota(ruolo):
    st.header("Prima Nota")
    try:
        df, ws = load_data()
        df_display = df.copy()
        df_display["Importo"] = df_display["Importo"].map("{:,.2f}".format).str.replace(",", "X").str.replace(".", ",").str.replace("X", ".")
        df_display["Seleziona"] = False

        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=["Data", "Mese"],
            column_config={"Seleziona": st.column_config.CheckboxColumn(required=False)}
        )

        selezionate = edited_df[edited_df["Seleziona"] == True]

        st.divider()
        st.subheader("Azioni disponibili")

        if len(selezionate) == 1:
            riga = selezionate.iloc[0]
            st.success("Riga selezionata:")
            st.json(riga.to_dict())

            with st.form("modifica_editor"):
                data_dt = datetime.strptime(riga["Data"], "%d/%m/%Y")
                nuova_data = st.date_input("Data", data_dt)
                nuova_causale = st.text_input("Causale", riga["Causale"])
                nuovo_centro = st.text_input("Centro", riga["Centro"])
                nuovo_importo = st.text_input("Importo", riga["Importo"])
                nuova_descrizione = st.text_input("Descrizione", riga["Descrizione"])
                nuova_cassa = st.text_input("Cassa", riga["Cassa"])
                nuove_note = st.text_input("Note", riga["Note"])

                submit = st.form_submit_button("Salva modifiche")
                if submit:
                    try:
                        parsed_importo = float(nuovo_importo.replace(".", "").replace(",", "."))
                        condizione = (
                            (df["Data"] == riga["Data"]) &
                            (df["Causale"] == riga["Causale"]) &
                            (df["Centro"] == riga["Centro"]) &
                            (df["Descrizione"] == riga["Descrizione"]) &
                            (df["Cassa"] == riga["Cassa"]) &
                            (df["Note"] == riga["Note"])
                        )
                        index = df[condizione].index[0]
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
                        st.success("Modifica salvata.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error("Errore durante la modifica.")
                        st.exception(e)

            if st.button("Elimina riga"):
                try:
                    condizione = (
                        (df["Data"] == riga["Data"]) &
                        (df["Causale"] == riga["Causale"]) &
                        (df["Centro"] == riga["Centro"]) &
                        (df["Descrizione"] == riga["Descrizione"]) &
                        (df["Cassa"] == riga["Cassa"]) &
                        (df["Note"] == riga["Note"])
                    )
                    df = df[~condizione]
                    update_sheet(df)
                    st.success("Riga eliminata.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Errore durante eliminazione.")
                    st.exception(e)

        elif len(selezionate) > 1:
            st.warning("Seleziona solo una riga per eseguire le azioni.")
        else:
            st.info("Nessuna riga selezionata.")

    except Exception as e:
        st.error("Errore generale nella sezione Prima Nota.")
        st.exception(e)


def mostra_dashboard():
    st.header("Dashboard")
    try:
        df, _ = load_data()
        st.subheader("Totale per centro di costo")
        totali = df.groupby("Centro")["Importo"].sum().sort_values(ascending=False)
        st.bar_chart(totali)
        st.subheader("Totale mensile")
        mensili = df.groupby("Mese")["Importo"].sum()
        st.line_chart(mensili)
    except Exception as e:
        st.error("Errore nella dashboard.")
        st.exception(e)

    st.header("Rendiconto ETS")
    try:
        df, _ = load_data()
        entrate = df[df["Importo"] > 0]["Importo"].sum()
        uscite = -df[df["Importo"] < 0]["Importo"].sum()
        st.metric("Entrate totali", f"€ {entrate:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("Uscite totali", f"€ {uscite:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        st.metric("Saldo", f"€ {(entrate - uscite):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    except Exception as e:
        st.error("Errore nel rendiconto.")
        st.exception(e)


    st.header("Nuovo Movimento")
    try:
        opzioni_cassa = leggi_riferimenti("rif cassa")
        opzioni_causale = leggi_riferimenti("rif causale")
        opzioni_centro = leggi_riferimenti("rif centro")

        with st.form("nuovo_movimento"):
            data = st.date_input("Data")
            causale = st.selectbox("Causale", opzioni_causale)
            centro = st.selectbox("Centro", opzioni_centro)
            importo = st.text_input("Importo")
            descrizione = st.text_input("Descrizione")
            cassa = st.selectbox("Cassa", opzioni_cassa)
            note = st.text_input("Note")
            submit = st.form_submit_button("Aggiungi")

        if submit:
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
            st.success("Movimento aggiunto.")
            st.experimental_rerun()
    except Exception as e:
        st.error("Errore nell'inserimento movimento.")
        st.exception(e)


##


    st.header("Saldi Cassa")
    try:
        df, _ = load_data()
        saldo_per_cassa = df.groupby("Cassa")["Importo"].sum().reset_index()
        saldo_per_cassa.columns = ["Cassa", "Saldo attuale"]

        st.subheader("Saldo per cassa registrato in prima nota")
        st.dataframe(saldo_per_cassa, use_container_width=True)

        st.divider()
        st.subheader("Modifica saldi estratto conto")

        try:
            foglio_saldi = get_worksheet("saldi estratto conto")
        except Exception:
            sh = gspread.authorize(
                Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"],
                    scopes=["https://www.googleapis.com/auth/spreadsheets"],
                )
            ).open_by_key(SHEET_ID)
            foglio_saldi = sh.add_worksheet(title="saldi estratto conto", rows=100, cols=2)
            foglio_saldi.update("A1:B1", [["Cassa", "Estratto conto"]])

        records = foglio_saldi.get_all_records()
        df_saldi = pd.DataFrame(records)

        if df_saldi.empty:
            df_saldi = pd.DataFrame({
                "Cassa": [
                    "Banco Posta",
                    "Cassa Contanti Sede",
                    "Unicredit Fiume di Pace",
                    "Unicredit Kimata",
                    "Unicredit Mari e Vulcani",
                    "Unicredit Nazionale",
                    "Conto PayPal",
                    "Accrediti su c/c da regolarizzare"
                ],
                "Estratto conto": [0.0] * 8
            })

        df_edit = st.data_editor(
            df_saldi,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="saldi_editor"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Salva saldi estratto conto"):
                foglio_saldi.clear()
                foglio_saldi.update([df_edit.columns.values.tolist()] + df_edit.fillna("").values.tolist())
                st.success("Saldi aggiornati correttamente.")

        with col2:
            if st.button("🗑️ Cancella tutti i saldi"):
                foglio_saldi.clear()
                foglio_saldi.update("A1:B1", [["Cassa", "Estratto conto"]])
                st.warning("Saldi eliminati.")

        st.divider()
        st.subheader("Confronto saldo vs estratto conto")

        if not df_edit.empty:
            confronto = pd.merge(saldo_per_cassa, df_edit, on="Cassa", how="left")
            confronto["Differenza"] = confronto["Saldo attuale"] - confronto["Estratto conto"].astype(float)
            st.dataframe(confronto, use_container_width=True)

    except Exception as e:
        st.error("Errore nella sezione saldi.")
        st.exception(e)
    st.header("Rendiconto ETS")
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
                differenza = saldo_finale - totale_estratti
                st.metric("Differenza", f"€ {differenza:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        except Exception:
            st.warning("❗ Foglio 'saldi estratto conto' non trovato o non leggibile.")
    except Exception as e:
        st.error("Errore nel rendiconto.")
        st.exception(e)
def mostra_nuovo_movimento(ruolo):
    st.header("Nuovo Movimento")
    try:
        opzioni_cassa = leggi_riferimenti("rif cassa")
        opzioni_causale = leggi_riferimenti("rif causale")
        opzioni_centro = leggi_riferimenti("rif centro")

        if "nuovo_mov_inserito" not in st.session_state:
            st.session_state["nuovo_mov_inserito"] = False

        if not st.session_state["nuovo_mov_inserito"]:
            with st.form("nuovo_movimento"):
                data = st.date_input("Data")
                causale = st.selectbox("Causale", opzioni_causale, index=None)
                centro = st.selectbox("Centro", opzioni_centro, index=None)
                importo = st.text_input("Importo", "")
                descrizione = st.text_input("Descrizione", "")
                cassa = st.selectbox("Cassa", opzioni_cassa, index=None)
                note = st.text_input("Note", "")
                submit = st.form_submit_button("Aggiungi")

            if submit:
                try:
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
                except Exception as e:
                    st.error("Errore durante inserimento.")
                    st.exception(e)
        else:
            st.button("➕ Inserisci nuovo movimento", on_click=lambda: st.session_state.update(nuovo_mov_inserito=False))
    except Exception as e:
        st.error("Errore nell'inserimento movimento.")
        st.exception(e)
def mostra_rendiconto():
    st.header("Rendiconto ETS")
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
def mostra_saldi_cassa(ruolo):
    st.header("✏️ Saldi Cassa")
    try:
        df, _ = load_data()
        saldo_per_cassa = df.groupby("Cassa")["Importo"].sum().reset_index()
        saldo_per_cassa.columns = ["Cassa", "Saldo attuale"]
        st.subheader("💰 Saldi calcolati dalla Prima Nota")
        st.dataframe(saldo_per_cassa, use_container_width=True)

        st.divider()
        st.subheader("📥 Inserisci saldo reale da estratto conto")

        # Valori fissi
        elenco_casse = [
            "Banco Posta",
            "Cassa Contanti Sede",
            "Unicredit Fiume di Pace",
            "Unicredit Kimata",
            "Unicredit Mari e Vulcani",
            "Unicredit Nazionale",
            "Conto PayPal",
            "Accrediti su c/c da regolarizzare"
        ]

        form_data = {}
        with st.form("form_saldi_estratti"):
            for cassa in elenco_casse:
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.text_input("Cassa", value=cassa, disabled=True, key=f"label_{cassa}")
                with col2:
                    form_data[cassa] = st.text_input("Estratto conto (€)", key=f"saldo_{cassa}")
            submitted = st.form_submit_button("💾 Salva tutti i saldi")

        if submitted:
            try:
                output = [["Cassa", "Estratto conto"]]
                for cassa in elenco_casse:
                    val = form_data[cassa].replace(".", "").replace(",", ".").strip()
                    parsed = float(val) if val else 0.0
                    output.append([cassa, parsed])
                foglio = get_worksheet("saldi estratto conto")
                foglio.clear()
                foglio.update(output)
                st.success("✅ Saldi aggiornati correttamente.")
            except Exception as e:
                st.error("❌ Errore durante il salvataggio dei saldi.")
                st.exception(e)

        st.divider()
        st.subheader("📊 Confronto saldo vs estratto conto")
        try:
            foglio_saldi = get_worksheet("saldi estratto conto")
            df_saldi = pd.DataFrame(foglio_saldi.get_all_records())
            confronto = pd.merge(saldo_per_cassa, df_saldi, on="Cassa", how="left")
            confronto["Differenza"] = confronto["Saldo attuale"] - confronto["Estratto conto"].astype(float)
            st.dataframe(confronto, use_container_width=True)
        except Exception as e:
            st.warning("⚠️ Impossibile leggere i saldi estratto conto.")
            st.exception(e)

    except Exception as e:
        st.error("Errore generale nella sezione Saldi Cassa.")
        st.exception(e)