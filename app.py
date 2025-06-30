import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import tempfile

st.set_page_config(page_title="Comparador Profesional de Ofertas", layout="wide")
st.title("📄 Comparador de Ofertas PDF - Proveedor vs Proveedor")

uploaded_files = st.file_uploader("📎 Cargar ofertas en PDF (hasta 6)", type=["pdf"], accept_multiple_files=True)

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

def extraer_items(texto):
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
                    descripcion = partes[1] if len(partes) > 1 else linea
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

# Procesamiento
datos = []

if uploaded_files:
    for archivo in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.read())
            texto = extraer_texto(tmp.name)

        proveedor = archivo.name.replace(".pdf", "")
        entrega = buscar_condicion(texto, "plazo_entrega")
        items = extraer_items(texto)

        if items:
            for item in items:
                item["Proveedor"] = proveedor
                item["Entrega"] = entrega
            datos.extend(items)
        else:
            st.warning(f"⚠️ No se detectaron ítems en: {archivo.name}")

if datos:
    df = pd.DataFrame(datos)
    productos = df[["Código", "Descripción"]].drop_duplicates()
    proveedores = df["Proveedor"].unique()

    tabla = pd.DataFrame()

    for _, prod in productos.iterrows():
        fila = {
            "Código": prod["Código"],
            "Descripción": prod["Descripción"]
        }
        producto_df = df[(df["Código"] == prod["Código"]) & (df["Descripción"] == prod["Descripción"])]
        mejor_precio = producto_df["Precio Unitario (USD)"].min()

        for proveedor in proveedores:
            datos_p = producto_df[producto_df["Proveedor"] == proveedor]
            if not datos_p.empty:
                unit = datos_p["Precio Unitario (USD)"].values[0]
                fila[f"{proveedor} - Cant"] = datos_p["Cantidad"].values[0]
                fila[f"{proveedor} - Unit"] = unit
                fila[f"{proveedor} - Total"] = datos_p["Valor Total (USD)"].values[0]
                fila[f"{proveedor} - Entrega"] = datos_p["Entrega"].values[0]
                fila[f"{proveedor} - Mejor"] = "🟢" if unit == mejor_precio else ""
            else:
                fila[f"{proveedor} - Cant"] = ""
                fila[f"{proveedor} - Unit"] = ""
                fila[f"{proveedor} - Total"] = ""
                fila[f"{proveedor} - Entrega"] = ""
                fila[f"{proveedor} - Mejor"] = ""
        tabla = pd.concat([tabla, pd.DataFrame([fila])], ignore_index=True)

    st.subheader("📊 Comparativa por Ítem")
    st.dataframe(tabla.style.highlight_min(subset=[f"{p} - Unit" for p in proveedores], axis=1, color='lightgreen'), use_container_width=True)

    output = BytesIO()
    tabla.to_excel(output, index=False)
    output.seek(0)
    st.download_button("📥 Descargar Excel", output, file_name="comparativa_ofertas_profesional.xlsx")
else:
    st.info("📂 Cargá uno o más PDFs para iniciar la comparativa.")
