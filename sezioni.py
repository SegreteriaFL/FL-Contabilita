import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
import matplotlib.pyplot as plt

SHEET_ID = "1Jg5g27twiVixfA8U10HvaTJ2HbAWS_YcbNB9VWdFwxo"

def format_euro(valore):
    try:
        return f"{valore:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    except:
        return valore

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

def mostra_saldi_cassa(ruolo):
    if ruolo not in ["tesoriere", "superadmin"]:
        st.warning("Accesso negato.")
        return

    st.title("✏️ Saldi Cassa")
    ws = get_worksheet()

    try:
        casse_rif = [r[0] for r in ws["casse"].get_all_values()]
        estratti_df = pd.DataFrame(ws["estratti"].get_all_records())
        saldi_map = dict(zip(estratti_df["Cassa"], estratti_df["Saldo dichiarato"])) if not estratti_df.empty else {}
        nuova_tabella = [{"Cassa": cassa, "Saldo": saldi_map.get(cassa, 0)} for cassa in casse_rif]

        with st.form("form_saldi"):
            nuove_righe = []
            for i, riga in enumerate(nuova_tabella):
                c1, c2 = st.columns(2)
                nome = c1.text_input(f"Cassa {i}", riga["Cassa"], disabled=True)
                saldo_input = "{:.2f}".format(riga["Saldo"]).replace(".", ",")
                saldo_raw = c2.text_input(f"Saldo {i}", value=saldo_input)
                try:
                    saldo = round(float(saldo_raw.replace(",", ".")), 2)
                except ValueError:
                    saldo = 0
                    st.warning(f"⚠️ Inserisci un numero valido per {riga['Cassa']}")
                nuove_righe.append([nome, saldo])

            st.markdown("---")
            raw_paste = st.text_area("📋 Incolla qui dati da Excel (una riga per cassa, separati da tab o spazio)", placeholder="Contanti\t300,00\nBanca Intesa\t1.250,00")

            if raw_paste:
                for riga in raw_paste.strip().split("\n"):
                    parts = riga.strip().replace("\t", " ").split()
                    if len(parts) >= 2:
                        nome = " ".join(parts[:-1])
                        try:
                            # Fix formati italiani: 1.234,56 -> 1234.56
                            val = parts[-1].strip()
                            val_clean = val.replace(".", "").replace(",", ".")
                            saldo = round(float(val_clean), 2)
                            nuove_righe.append([nome, saldo])
                        except:
                            st.warning(f"⚠️ Saldo non valido nella riga: {riga}")

            salva = st.form_submit_button("💾 Salva saldi")
            if salva:
                ws["estratti"].clear()
                ws["estratti"].append_row(["Cassa", "Saldo dichiarato"])
                for r in nuove_righe:
                    ws["estratti"].append_row(r)
                st.success("✅ Saldi aggiornati.")
                try: st.rerun()
                except Exception: st.experimental_rerun()
    except Exception as e:
        st.error("Errore nel caricamento dei saldi: " + str(e))