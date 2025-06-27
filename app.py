
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
    lineas = texto.splitlines()
    item_actual = {}

    for linea in lineas:
        linea = linea.strip()

        precios = re.findall(r"\d{1,3}(?:[.,]\d{3})*[.,]\d{2}", linea)
        cantidades = re.findall(r"\b\d{1,3}\b", linea)

        if len(precios) >= 2 and len(cantidades) >= 1:
            try:
                codigo_match = re.match(r"^(\d{3,6})", linea)
                codigo = codigo_match.group(1) if codigo_match else ""

                cantidad = int(cantidades[0])
                unit = float(precios[-2].replace(".", "").replace(",", "."))
                total = float(precios[-1].replace(".", "").replace(",", "."))

                descripcion = item_actual.get("desc", "")
                if not descripcion:
                    partes = re.split(r"\s{2,}", linea)
                    if len(partes) > 1:
                        descripcion = partes[1]
                    else:
                        descripcion = linea

                items.append({
                    "Código": codigo,
                    "Descripción": descripcion[:120],
                    "Cantidad": cantidad,
                    "Precio Unitario (USD)": unit,
                    "Valor Total (USD)": total
                })

                item_actual = {}
            except:
                continue

        elif not re.search(r"\d{1,3}(?:[.,]\d{3})*[.,]\d{2}", linea):
            if "desc" in item_actual:
                item_actual["desc"] += " " + linea
            else:
                item_actual["desc"] = linea

    return items
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
