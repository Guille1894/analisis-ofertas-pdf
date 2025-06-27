
import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import tempfile

st.set_page_config(page_title="Comparador de Ofertas PDF", layout="wide")
st.title("📄 Comparador Automático de Ofertas en PDF")

uploaded_files = st.file_uploader("📎 Cargar una o más ofertas en PDF", type=["pdf"], accept_multiple_files=True)

def extraer_texto(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                texto += page.extract_text() + "\n"
    return texto

def extraer_items_flexibles(texto):
    items = []
    patron = re.compile(r"(\d{2,6})\s+(\d{1,3})\s+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")
    bloques = patron.findall(texto)
    descripciones = re.split(r"\n\d{2,6}\s+\d{1,3}\s+\d{1,3}[.,]\d{2}\s+\d{1,3}[.,]\d{2}", texto)
    descripciones = [d.strip().replace("\n", " ") for d in descripciones[1:]]  # saltar encabezado

    for i, match in enumerate(bloques):
        codigo, cantidad, unit, total = match
        desc = descripciones[i] if i < len(descripciones) else ""
        try:
            items.append({
                "Código": codigo.strip(),
                "Descripción": desc[:120],
                "Cantidad": int(cantidad),
                "Precio Unitario (USD)": float(unit.replace(".", "").replace(",", ".")),
                "Valor Total (USD)": float(total.replace(".", "").replace(",", "."))
            })
        except:
            continue
    return items

def buscar_condicion(texto, clave):
    patrones = {
        "forma_pago": r"(forma de pago|pago:?)\s*:?\s*(.+?)(\n|$)",
        "plazo_entrega": r"(plazo de entrega|entrega:?)\s*:?\s*(.+?)(\n|$)",
        "incoterm": r"(incoterm|entrega en|transporte:?)\s*:?\s*(.+?)(\n|$)"
    }
    if clave in patrones:
        match = re.search(patrones[clave], texto, re.IGNORECASE)
        if match:
            return match.group(2).strip()
    return ""

datos = []

if uploaded_files:
    for archivo in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.read())
            texto = extraer_texto(tmp.name)

        proveedor = archivo.name.replace(".pdf", "")
        items = extraer_items_flexibles(texto)
        if items:
            for item in items:
                item["Proveedor"] = proveedor
                item["Plazo Entrega"] = buscar_condicion(texto, "plazo_entrega")
                item["Forma de Pago"] = buscar_condicion(texto, "forma_pago")
                item["Incoterm"] = buscar_condicion(texto, "incoterm")
            datos.extend(items)
        else:
            st.warning(f"⚠️ No se detectaron ítems válidos en: {archivo.name}")

if datos:
    df = pd.DataFrame(datos)
    st.subheader("📊 Comparativa de Ofertas")
    st.dataframe(df, use_container_width=True)

    resumen = df.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
    resumen = resumen.sort_values("Valor Total (USD)")
    mejor = resumen.iloc[0]

    st.subheader("💰 Total por Proveedor")
    st.dataframe(resumen)

    st.success(f"🏆 Proveedor recomendado: {mejor['Proveedor']} (USD {mejor['Valor Total (USD)']:.2f})")

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    st.download_button("📥 Descargar Excel comparativo", output, file_name="comparativa_ofertas.xlsx")
else:
    st.info("📂 Cargá uno o más PDFs para iniciar la comparativa.")
