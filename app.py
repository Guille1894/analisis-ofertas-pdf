
import streamlit as st
import pandas as pd
import pdfplumber
import re
from io import BytesIO

st.set_page_config(page_title="📦 Comparador de Ofertas PDF", layout="wide")
st.title("📦 Comparador de Ofertas de Proveedores (PDF)")

def extraer_texto_pdf(pdf_file):
    texto = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            contenido = page.extract_text()
            if contenido:
                texto += contenido + "\n"
    return texto

def detectar_proveedor(texto):
    if "Cameron" in texto:
        return "Cameron"
    elif "Pernigotti" in texto or "MMA" in texto or "APERNIGOTTI" in texto:
        return "MMA"
    else:
        return "Proveedor desconocido"

def extraer_items(texto):
    items = []
    patron_cameron = r"(\d+)\s+([\dA-Z/-]+)\s+[\d,\.]+\s+(\d+)\s+EA\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))"
    matches = re.findall(patron_cameron, texto)
    for m in matches:
        items.append({
            "Código": m[1],
            "Descripción": "Brida Cameron",
            "Cantidad": int(m[2]),
            "Precio Unitario": float(m[3].replace(".", "").replace(",", ".")) if "," in m[3] else float(m[3].replace(",", "")),
            "Total": float(m[4].replace(".", "").replace(",", ".")) if "," in m[4] else float(m[4].replace(",", ""))
        })

    patron_mma = r"(\d{3})\s+([\dA-Z/-]+)\s+(\d+)\s+(.+?)\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))"
    matches = re.findall(patron_mma, texto)
    for m in matches:
        items.append({
            "Código": m[1],
            "Descripción": m[3].strip(),
            "Cantidad": int(m[2]),
            "Precio Unitario": float(m[4].replace(".", "").replace(",", ".")) if "," in m[4] else float(m[4].replace(",", "")),
            "Total": float(m[5].replace(".", "").replace(",", ".")) if "," in m[5] else float(m[5].replace(",", ""))
        })

    return items

def extraer_condiciones(texto):
    condiciones = {}
    if "30 DÍAS" in texto.upper() or "NET 30" in texto.upper():
        condiciones["Forma de Pago"] = "30 días f/f"
    if "15 DÍAS" in texto.upper():
        condiciones["Forma de Pago"] = "15 días"
    if "45 DIAS" in texto.upper():
        condiciones["Plazo de Entrega"] = "45 días"
    if "5 semanas" in texto.lower() or "15 semanas" in texto.lower():
        condiciones["Plazo de Entrega"] = "5 a 15 semanas"
    if "FCA" in texto.upper():
        condiciones["Incoterm"] = "FCA"
    if "VALIDEZ DE LA OFERTA: treinta (30) días" in texto or "Valid To" in texto:
        condiciones["Validez"] = "30 días"
    return condiciones

archivos_pdf = st.file_uploader("📂 Subí las ofertas en PDF", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    data = []
    productos = set()
    for archivo in archivos_pdf:
        texto = extraer_texto_pdf(archivo)
        proveedor = detectar_proveedor(texto)
        items = extraer_items(texto)
        condiciones = extraer_condiciones(texto)
        for item in items:
            productos.add(item["Descripción"])
            data.append({
                "Proveedor": proveedor,
                "Descripción": item["Descripción"],
                "Cantidad": item["Cantidad"],
                "Precio Unitario": item["Precio Unitario"],
                "Total": item["Total"],
                **condiciones
            })

    if data:
        df = pd.DataFrame(data)
        st.subheader("📊 Comparativa de Ofertas por Ítem")
        tabla = df.pivot_table(index="Descripción", columns="Proveedor",
                               values=["Cantidad", "Precio Unitario", "Total"], aggfunc="first")

        def resaltar_mejor_precio(valores):
            try:
                return ["background-color: lightgreen" if v == min(valores) else "" for v in valores]
            except:
                return [""] * len(valores)

        st.dataframe(tabla.style.apply(resaltar_mejor_precio, subset=("Precio Unitario", slice(None)), axis=1), use_container_width=True)

        st.subheader("📁 Exportar Resultados")
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Comparativa")
        st.download_button("📥 Descargar Excel", data=buffer.getvalue(), file_name="comparativa_ofertas.xlsx")

    else:
        st.warning("No se detectaron ítems en los PDFs cargados.")
