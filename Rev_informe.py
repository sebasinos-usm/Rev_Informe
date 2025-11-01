import streamlit as st
import google.generativeai as genai
import json
import html

# --- CONFIGURACIÓN DE LA API DE GEMINI ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    GEMINI_AVAILABLE = True
except (FileNotFoundError, KeyError):
    GEMINI_AVAILABLE = False

# --- LÓGICA DE CORRECCIÓN (BACKEND CON PROMPT AVANZADO) ---

def construir_prompt_avanzado(texto_informe: str) -> str:
    """
    Crea el prompt detallado basado en el protocolo de corrección riguroso.
    """
    # **CAMBIO CLAVE EN EL PROMPT**
    # Se añade una regla específica para manejar y justificar la eliminación de texto.
    prompt = f"""
    # ROL Y OBJETIVO
    Actúa como un asistente experto en radiología y editor técnico. Tu objetivo es aplicar un protocolo de corrección riguroso al informe médico en español proporcionado.

    # TAREA PRINCIPAL
    Analiza el **[INFORME ORIGINAL]**. Aplica estrictamente TODAS las reglas del protocolo. Debes conservar el formato original, incluyendo todos los saltos de línea y espaciados.

    ---
    ## PROTOCOLO DE CORRECCIÓN (Reglas a Aplicar)

    1.  **Ortografía y Gramática:** Corrige errores ortográficos, de tipeo y gramaticales. Asegura la correcta concordancia.
    2.  **Terminología y Estilo:** Verifica lateralidad, elimina mayúsculas innecesarias, estandariza términos y asegura la puntuación final.
    3.  **Coherencia Interna:** Verifica que los hallazgos descritos en el cuerpo del informe sean consistentes con la conclusión en la "Impresión Diagnóstica".
    4.  **MANEJO DE INCOHERENCIAS GRAVES:** Si un párrafo o frase contradice directamente el resto del informe y no puede ser corregido sin alterar el significado clínico, debes eliminarlo. Si lo haces, en la 'lista_de_cambios', el campo 'despues' debe ser "ELIMINADO" y el 'motivo' debe explicar claramente por qué era incoherente.
    5.  **REGLA FUNDAMENTAL (LO QUE NO DEBES HACER):** No reescribas el estilo narrativo. Corrige solo lo necesario. No inventes información.

    ---
    ## FORMATO DE SALIDA OBLIGATORIO

    Responde únicamente con un objeto JSON válido. La estructura del JSON debe ser:
    {{
      "informe_corregido": "El texto completo del informe corregido. IMPORTANTE: Conserva EXACTAMENTE el mismo formato y saltos de línea que el original. Para marcar los cambios, ENVUELVE la palabra o frase corregida con '@@@', por ejemplo: '@@@nódulo@@@'.",
      "impresion_diagnostica_fluida": "Una versión narrativa y clara de la 'Impresión Diagnóstica'.",
      "lista_de_cambios": [
        {{
          "antes": "El texto original con el error o incoherencia.",
          "despues": "El texto ya corregido o la palabra 'ELIMINADO'.",
          "motivo": "La razón de la corrección o de la eliminación."
        }}
      ],
      "falsos_positivos_descartados": [
        {{
          "termino": "La palabra que parecía un error pero no lo era.",
          "justificacion": "La razón por la que se mantuvo."
        }}
      ],
      "registro_de_perfeccionamiento": [
         "Un error evitado gracias al protocolo."
      ]
    }}

    ---

    **[INFORME ORIGINAL]:**
    {texto_informe}
    """
    return prompt

def corregir_con_gemini(texto_informe: str) -> dict:
    """Envía el texto a la API de Gemini y devuelve el resultado."""
    if not GEMINI_AVAILABLE:
        return {"error": "API Key de Gemini no configurada."}
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        prompt = construir_prompt_avanzado(texto_informe)
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_response)
    except Exception as e:
        return {"error": f"Hubo un problema al contactar la API de Gemini: {e}"}

def resaltar_cambios(texto_corregido: str) -> str:
    """
    Busca los marcadores @@@, resalta el contenido en amarillo con HTML,
    y asegura que el resto del texto sea seguro para mostrar.
    """
    partes = texto_corregido.split('@@@')
    html_resultante = ""
    for i, parte in enumerate(partes):
        if i % 2 == 1:
            html_resultante += f'<span style="background-color: #FFECB3; padding: 2px 1px; border-radius: 3px;">{html.escape(parte)}</span>'
        else:
            html_resultante += html.escape(parte)
    return html_resultante.replace('\n', '<br>')

# --- INTERFAZ DE USUARIO (FRONTEND CON STREAMLIT) ---

st.set_page_config(layout="wide")
st.title("Asistente de Revisión de Informes con Protocolo Avanzado 🔬")
st.markdown("Compare el informe original con la versión corregida por la IA y revise el análisis detallado del protocolo a continuación.")

if not GEMINI_AVAILABLE:
    st.error("**Error de Configuración:** No se pudo encontrar la API Key de Google. Asegúrate de tener un archivo `.streamlit/secrets.toml` con tu `GOOGLE_API_KEY`.")
    st.stop()

ejemplo = """Estudio de TC torax sin contraste:
Se observa un nodulo de aspecto inespecifico en el pulomon izq. que mide 12mm.
Ademas de atelectasia laminar. hay osteofito marginal en cuerpos vertebrales.
El paciente no refiere antecedentes de tabaquismo. El higado es de tamaño normal.

Impresion diagnostica:
- Nodulo pulmonar en estudio"""
informe_texto = st.text_area("Pega el texto del informe aquí:", height=150, value=ejemplo)

if st.button("Aplicar Protocolo de Revisión", type="primary"):
    if informe_texto:
        with st.spinner("Aplicando protocolo con IA... El asistente está revisando el informe... 💡"):
            resultado = corregir_con_gemini(informe_texto)

            if "error" in resultado:
                st.error(resultado["error"])
            else:
                st.success("¡Protocolo aplicado con éxito!")
                
                report_style = """
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    height: 650px;
                    overflow-y: auto;
                    background-color: #ffffff;
                    font-family: monospace;
                    white-space: pre-wrap;
                """
                
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Hoja de Informe Original")
                    texto_original_html = html.escape(informe_texto).replace('\n', '<br>')
                    st.markdown(f"<div style='{report_style}'>{texto_original_html}</div>", unsafe_allow_html=True)

                with col2:
                    st.subheader("Hoja de Informe Corregido")
                    informe_corregido = resultado.get("informe_corregido", "No se pudo generar el texto corregido.")
                    informe_corregido_html = resaltar_cambios(informe_corregido)
                    st.markdown(f"<div style='{report_style} background-color: #f0fff0;'>{informe_corregido_html}</div>", unsafe_allow_html=True)

                st.markdown("<br><hr>", unsafe_allow_html=True)
                st.subheader("Análisis Detallado del Protocolo")

                st.info(f"**Impresión Diagnóstica Fluida:** {resultado.get('impresion_diagnostica_fluida', 'No disponible.')}")

                with st.expander("Ver Lista de Cambios y Análisis Adicional", expanded=True):
                    
                    st.markdown("#### Lista de Cambios Realizados")
                    cambios = resultado.get("lista_de_cambios", [])
                    if cambios:
                        for cambio in cambios:
                            # **CAMBIO CLAVE EN LA INTERFAZ**
                            # Detecta si el cambio fue una eliminación y lo muestra de forma diferente.
                            if cambio.get('despues', '').upper() == 'ELIMINADO':
                                st.markdown(f"🔹 **Texto Eliminado:** <span style='background-color:#FFCDD2; text-decoration: line-through;'>`{cambio.get('antes', 'N/A')}`</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"🔹 **Antes:** `{cambio.get('antes', 'N/A')}` → **Después:** `{cambio.get('despues', 'N/A')}`")
                            
                            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**Motivo:** *{cambio.get('motivo', 'No especificado')}*")
                    else:
                        st.write("No se reportaron cambios específicos.")
    else:
        st.warning("Por favor, introduce el texto de un informe para analizar.")