import streamlit as st
import pandas as pd
import pdfplumber
import re
from collections import defaultdict
from io import BytesIO

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
    if "PAN AMERICAN ENERGY" in texto:
        return "PAN AMERICAN ENERGY"
    return "Proveedor desconocido"

# --- Función para extraer ítems ---
def extraer_items(texto):
    items = []
    lineas = texto.split("\n")
    for i, linea in enumerate(lineas):
        match = re.match(r"^\d{3}\s+\S+\s+(\d+)\s+(.+)", linea)
        if match:
            cantidad = float(match.group(1))
            descripcion = match.group(2).strip()
            for j in range(i+1, min(i+5, len(lineas))):
                if "P. UNIT." in lineas[j] and "TOTAL" in lineas[j]:
                    precio_match = re.search(r"(\d[\d,.]*)\s*$", lineas[j+1])
                    if precio_match:
                        precio_unit = float(precio_match.group(1).replace(",", ""))
                        entrega = "No especificada"
                        items.append((descripcion, cantidad, precio_unit, entrega))
                    break
    return items

# --- Función para extraer condiciones comerciales ---
def extraer_condiciones(texto):
    condiciones = {}

    entrega_match = re.search(r"PLAZO DE ENTREGA\s*[:\-]?\s*(.+)", texto, re.IGNORECASE)
    if entrega_match:
        condiciones["Entrega"] = entrega_match.group(1).strip()

    pago_match = re.search(r"FORMA DE PAGO\s*[:\-]?\s*(.+)", texto, re.IGNORECASE)
    if pago_match:
        condiciones["Forma de pago"] = pago_match.group(1).strip()

    validez_match = re.search(r"VALIDEZ DE OFERTA\s*[:\-]?\s*(.+)", texto, re.IGNORECASE)
    if validez_match:
        condiciones["Validez"] = validez_match.group(1).strip()

    return condiciones

# --- Carga de PDFs ---
archivos = st.file_uploader("Cargar archivos PDF de proveedores", type="pdf", accept_multiple_files=True)

if archivos:
    datos = defaultdict(dict)
    condiciones_por_proveedor = {}
    lista_productos = set()
    proveedores = []

    for archivo in archivos:
        texto = extraer_texto_pdf(archivo)
        proveedor = detectar_proveedor(texto)
        proveedores.append(proveedor)

        items = extraer_items(texto)
        condiciones = extraer_condiciones(texto)
        condiciones_por_proveedor[proveedor] = condiciones

        for descripcion, cantidad, precio_unit, entrega in items:
            lista_productos.add(descripcion)
            datos[descripcion][proveedor] = {
                "cantidad": cantidad,
                "precio_unit": precio_unit,
                "valor_total": cantidad * precio_unit,
                "entrega": entrega
            }

    # --- Tabla comparativa de ítems ---
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

    # --- Mostrar condiciones comerciales por proveedor ---
    st.subheader("📄 Condiciones Comerciales")
    tabla_cond = pd.DataFrame(condiciones_por_proveedor).fillna("-")
    st.dataframe(tabla_cond, use_container_width=True)

    # --- Descargar como Excel ---
    st.markdown("### 📥 Descargar comparación")

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Comparativa", index=False)
        tabla_cond.T.to_excel(writer, sheet_name="Condiciones")  # Transpuesta para mostrar bien

    output.seek(0)

    st.download_button(
        label="Descargar Excel",
        data=output,
        file_name="comparativa_ofertas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Cargá al menos un archivo PDF para comenzar.")



