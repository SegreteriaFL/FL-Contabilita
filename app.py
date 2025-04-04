# ✅ Gestionale Contabilità ETS — Tema coerente, stabile, compatibile Streamlit Cloud

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from fpdf import FPDF
import tempfile

st.set_page_config(
    page_title="Gestionale Contabilità ETS",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ Caricamento tema scuro/chiaro coerente
with open("theme.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# === Utility ===
def format_currency(val):
    try:
        return f"{float(val):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return val

def format_date(dt):
    return dt.strftime("%d/%m/%Y") if not pd.isna(dt) else ""

def download_excel(df, nome_file):
    output = BytesIO()
    df.to_excel(output, index=False)
    st.download_button("📥 Scarica Excel", data=output.getvalue(), file_name=f"{nome_file}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

def download_pdf(text, nome_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        try:
            pdf.cell(200, 10, txt=line.encode("latin-1", "replace").decode("latin-1"), ln=True)
        except:
            pdf.cell(200, 10, txt="[Errore codifica]", ln=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        tmp.seek(0)
        st.download_button("📄 Scarica PDF", data=tmp.read(), file_name=nome_file, mime="application/pdf")

def genera_ricevuta_pdf(d):
    lines = [
        "Ricevuta Donazione",
        f"Data: {format_date(d['data'])}",
        f"Importo: {format_currency(d['Importo'])}",
        f"Causale: {d['Causale']}",
        f"Centro di Costo: {d['Centro di Costo']}",
        f"Metodo: {d['Cassa']}",
        f"Note: {d['Note']}"
    ]
    return "\n".join(lines)

# === Login simulato ===
utenti = [
    {"nome": "Mario Rossi", "email": "mario@fl.org", "ruolo": "superadmin", "provincia": "Tutte"},
    {"nome": "Lucia Bianchi", "email": "lucia@fl.org", "ruolo": "supervisore", "provincia": "Tutte"},
    {"nome": "Paolo Verdi", "email": "paolo.siena@fl.org", "ruolo": "tesoriere", "provincia": "Siena"},
    {"nome": "Anna Neri", "email": "anna.firenze@fl.org", "ruolo": "tesoriere", "provincia": "Firenze"},
    {"nome": "Franca Gialli", "email": "franca@fl.org", "ruolo": "lettore", "provincia": "Pisa"},
]
utente_sel = st.sidebar.selectbox("👤 Seleziona utente:", [f"{u['nome']} ({u['ruolo']})" for u in utenti])
utente = next(u for u in utenti if f"{u['nome']} ({u['ruolo']})" == utente_sel)

st.sidebar.markdown(f"**Ruolo:** {utente['ruolo']}")
if utente['provincia'] != "Tutte":
    st.sidebar.markdown(f"**Provincia:** {utente['provincia']}")

# === Menu laterale ===
menu_style = {
    "container": {"padding": "0!important", "background-color": "#111"},
    "icon": {"color": "white", "font-size": "18px"},
    "nav-link": {"font-size": "16px", "color": "#EEE", "margin": "4px", "--hover-color": "#333"},
    "nav-link-selected": {"background-color": "#4CAF50", "font-weight": "bold", "color": "white"},
}

with st.sidebar:
    sezione_attiva = option_menu(
        menu_title="📂 Sezioni",
        options=["Prima Nota", "Dashboard", "Rendiconto ETS", "Donazioni", "Quote associative", "Nuovo Movimento"],
        icons=["file-earmark-text", "bar-chart", "clipboard-data", "gift", "people", "plus-circle"],
        menu_icon="folder",
        default_index=0,
        styles=menu_style
    )

# === Connessione a Google Sheets ===
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_Dj2IcT1av_UXamj0sFAuslIQ-NYrRRAyI9A31eXwS4/edit"
SHEET_NAME = "prima_nota_2024"

def carica_movimenti():
    df = pd.DataFrame(client.open_by_url(SHEET_URL).worksheet(SHEET_NAME).get_all_records())
    df.columns = df.columns.str.strip()
    if "Provincia" not in df.columns:
        df["Provincia"] = ""
    df["Importo"] = pd.to_numeric(df["Importo"], errors="coerce").fillna(0)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df[df["data"].notna()]
    if utente["ruolo"] == "tesoriere":
        df = df[df["Provincia"] == utente["provincia"]]
    return df

# === Import delle sezioni modulari ===
from sezioni import (
    mostra_prima_nota,
    mostra_dashboard,
    mostra_rendiconto
)

# === Routing ===
if sezione_attiva == "Prima Nota":
    mostra_prima_nota(utente, carica_movimenti, format_currency, format_date, download_excel)
elif sezione_attiva == "Dashboard":
    mostra_dashboard(carica_movimenti)
elif sezione_attiva == "Rendiconto ETS":
    mostra_rendiconto(carica_movimenti, format_currency, download_pdf)
elif sezione_attiva == "Donazioni":
    mostra_donazioni(carica_movimenti, format_currency, format_date, genera_ricevuta_pdf, download_pdf)
elif sezione_attiva == "Quote associative":
    mostra_quote()
elif sezione_attiva == "Nuovo Movimento":
    mostra_nuovo_movimento(utente)
