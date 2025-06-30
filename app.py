import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import tempfile

st.set_page_config(page_title="Comparador de Ofertas PDF", layout="wide")
st.title("📄 Comparador Avanzado de Ofertas en PDF")

uploaded_files = st.file_uploader("📎 Cargar una o más ofertas en PDF", type=["pdf"], accept_multiple_files=True)

def extraer_texto(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                texto += page.extract_text() + "\n"
    return texto

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
                    "Descripción": descripcion.strip()[:120],
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

# Procesar archivos PDF cargados
datos = []

if uploaded_files:
    for archivo in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.read())
            texto = extraer_texto(tmp.name)

        proveedor = archivo.name.replace(".pdf", "")
        entrega = buscar_condicion(texto, "plazo_entrega")
        items = extraer_items_flexibles(texto)

        if items:
            for item in items:
                item["Proveedor"] = proveedor
                item["Entrega"] = entrega
            datos.extend(items)
        else:
            st.warning(f"⚠️ No se detectaron ítems válidos en: {archivo.name}")

if datos:
    df = pd.DataFrame(datos)
    productos = df[["Código", "Descripción"]].drop_duplicates()
    proveedores = df["Proveedor"].unique()

    columnas = []
    for proveedor in proveedores:
        columnas.extend([
            f"{proveedor} - Cantidad",
            f"{proveedor} - Unitario",
            f"{proveedor} - Total",
            f"{proveedor} - Entrega"
        ])

    tabla_final = pd.DataFrame()

    for _, prod in productos.iterrows():
        fila = {
            "Código": prod["Código"],
            "Descripción": prod["Descripción"]
        }
        producto_df = df[(df["Código"] == prod["Código"]) & (df["Descripción"] == prod["Descripción"])]
        mejores = producto_df.loc[producto_df["Precio Unitario (USD)"].idxmin(), "Proveedor"]

        for proveedor in proveedores:
            datos_p = producto_df[producto_df["Proveedor"] == proveedor]
            if not datos_p.empty:
                fila[f"{proveedor} - Cantidad"] = datos_p["Cantidad"].values[0]
                fila[f"{proveedor} - Unitario"] = datos_p["Precio Unitario (USD)"].values[0]
                fila[f"{proveedor} - Total"] = datos_p["Valor Total (USD)"].values[0]
                fila[f"{proveedor} - Entrega"] = datos_p["Entrega"].values[0]
            else:
                fila[f"{proveedor} - Cantidad"] = ""
                fila[f"{proveedor} - Unitario"] = ""
                fila[f"{proveedor} - Total"] = ""
                fila[f"{proveedor} - Entrega"] = ""

        fila["🟢 Mejor Proveedor"] = mejores
        tabla_final = pd.concat([tabla_final, pd.DataFrame([fila])], ignore_index=True)

    st.subheader("📊 Comparativa estructurada por ítem")
    st.dataframe(tabla_final, use_container_width=True)

    output = BytesIO()
    tabla_final.to_excel(output, index=False)
    output.seek(0)
    st.download_button("📥 Descargar Excel comparativo", output, file_name="comparativa_estructura.xlsx")
else:
    st.info("📂 Cargá uno o más PDFs para iniciar la comparativa.")
