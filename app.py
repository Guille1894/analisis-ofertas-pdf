import streamlit as st
import pandas as pd
import pdfplumber
import re
from collections import defaultdict

st.set_page_config(page_title="Comparador de Ofertas", layout="wide")

st.title("📦 Comparador de Ofertas de Proveedores (PDF)")

# --- Función para extraer texto de PDFs ---
def extraer_texto_pdf(pdf_file):
    texto = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() + "\n"
    return texto

# --- Función para detectar proveedor desde el texto ---
def detectar_proveedor(texto):
    patrones = [r"Proveedor:\s*(.+)", r"Company:\s*(.+)", r"Supplier:\s*(.+)"]
    for linea in texto.split("\n"):
        for patron in patrones:
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return "Proveedor desconocido"

# --- Función para extraer ítems con cantidades y precios ---
def extraer_items(texto):
    lineas = texto.split("\n")
    items = []

    for linea in lineas:
        if re.search(r"\d", linea) and re.search(r"\d+(\.\d{1,2})?\s?[€$]", linea):
            partes = linea.split()
            try:
                descripcion = " ".join(partes[1:-3])
                cantidad = float(partes[-3].replace(",", ""))
                precio_unit = float(partes[-2].replace(",", "").replace("$", "").replace("€", ""))
                entrega = partes[-1]
                items.append((descripcion, cantidad, precio_unit, entrega))
            except:
                continue
    return items

# --- Carga de PDFs ---
archivos = st.file_uploader("Cargar archivos PDF de proveedores", type="pdf", accept_multiple_files=True)

if archivos:
    datos = defaultdict(dict)
    lista_productos = set()
    proveedores = []

    for archivo in archivos:
        texto = extraer_texto_pdf(archivo)
        proveedor = detectar_proveedor(texto)
        proveedores.append(proveedor)

        items = extraer_items(texto)
        for descripcion, cantidad, precio_unit, entrega in items:
            lista_productos.add(descripcion)
            datos[descripcion][proveedor] = {
                "cantidad": cantidad,
                "precio_unit": precio_unit,
                "valor_total": cantidad * precio_unit,
                "entrega": entrega
            }

    # --- Construcción de la tabla comparativa ---
    lista_productos = sorted(lista_productos)
    columnas = ["Producto"]

    for proveedor in proveedores:
        columnas += [
            f"{proveedor} - Cantidad",
            f"{proveedor} - Unit",
            f"{proveedor} - Total",
            f"{proveedor} - Entrega"
        ]

    tabla = []

    for producto in lista_productos:
        fila = [producto]
        for proveedor in proveedores:
            info = datos[producto].get(proveedor, {})
            fila += [
                info.get("cantidad", ""),
                info.get("precio_unit", ""),
                info.get("valor_total", ""),
                info.get("entrega", "")
            ]
        tabla.append(fila)

    df = pd.DataFrame(tabla, columns=columnas)

    # --- Mostrar tabla con resaltado del mejor precio unitario ---
    st.subheader("🔍 Comparativa por ítem")

    cols_unit = [f"{p} - Unit" for p in proveedores if f"{p} - Unit" in df.columns and pd.api.types.is_numeric_dtype(df[f"{p} - Unit"])]

    if cols_unit:
        styled_df = df.style.highlight_min(subset=cols_unit, axis=1, color='lightgreen')
    else:
        styled_df = df.style

    st.dataframe(styled_df, use_container_width=True)

    # --- Descargar como Excel ---
    st.markdown("### 📥 Descargar comparación")
    from io import BytesIO

# Convertir DataFrame a archivo Excel en memoria
output = BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False)
output.seek(0)

# Botón de descarga
st.download_button(
    label="Descargar Excel",
    data=output,
    file_name="comparativa_ofertas.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
else:
    st.info("Cargá al menos un archivo PDF para comenzar.")

