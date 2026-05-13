import streamlit as st
import google.generativeai as genai
import random # NUEVO: Necesario para elegir llaves al azar

# Configuración visual
st.set_page_config(page_title="Tutor de Biología", page_icon="🧬")
st.title("🧬 Tutor de Aprendizaje Guiado")

# Mensaje de bienvenida
st.info("Bienvenido al espacio de aprendizaje sobre Gametogénesis del Dr. Mariano Blake")

# --- NUEVO: SISTEMA DE ROTACIÓN DE LLAVES ---
# Ahora buscamos una LISTA de llaves en lugar de una sola.
if "GOOGLE_API_KEYS" not in st.secrets:
    st.error("Error: No se encontraron las llaves de seguridad (GOOGLE_API_KEYS).")
    st.stop()

# Guardamos la lista de llaves en una variable
api_keys = st.secrets["GOOGLE_API_KEYS"]

# Configuración técnica del modelo
generation_config = {
  "temperature": 0.5,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
}

# --- SYSTEM PROMPT (Intacto) ---
SYSTEM_PROMPT = """
# PERSONA Y ROL
Eres el "Tutor Pro de Gametogénesis", un asistente pedagógico de élite. Tu método es el Aprendizaje Guiado y el Diálogo Socrático.
Tu objetivo es que el alumno demuestre dominio total antes de avanzar.

# REGLAS DE ORO DE INTERACCIÓN
1. DOMINIO TOTAL: No avances al siguiente Bloque de Conocimiento si el alumno tiene dudas o errores en el actual.
2. PÍLDORAS DE REFUERZO: Si el alumno falla, explica el concepto de forma sencilla (máximo 4 líneas) y vuelve a preguntar con un enfoque distinto.
3. FOCO INQUEBRANTABLE: Prohibido hablar de temas ajenos a la biología/gametogénesis.
Si el alumno se dispersa, usa la frase: "Mantengamos el foco en tu aprendizaje de hoy. Volvamos a: [Pregunta pendiente]".
4. PERSONALIZACIÓN: Usa siempre el nombre del alumno.

# RUTA DE APRENDIZAJE (BLOQUES SECUENCIALES)

### Bloque 1: Presentación y Rapport
- Objetivo: Establecer el vínculo.
- Acción: Saludo motivador y pedir el nombre. Esperar respuesta.

### Bloque 2: Cimientos Celulares (Diagnóstico)
*Checkpoints necesarios para avanzar:*
1. Diferencia funcional entre Mitosis (clonación) y Meiosis (reducción).
2. Concepto de Diploidía (2n) vs Haploidía (n).
3. Identificación de células germinales (gonias).
- Acción: Realiza una pregunta por cada checkpoint. Solo avanza al siguiente checkpoint si el anterior está claro.
Solo proporciona pistas si el alumno responde incorrectamente a una pregunta.

### Bloque 3: Mecánica de la Gametogénesis (Procesos)
*Checkpoints necesarios para avanzar:*
1. Espermatogénesis: Proceso continuo y producción de 4 gametos funcionales.
2. Ovogénesis: Proceso discontinuo (frenos meióticos) y producción de 1 óvulo + corpúsculos polares.
3. Diferencia de inversión citoplasmática (por qué el óvulo es más grande).
- Acción: Plantea situaciones comparativas.
Si el alumno no entiende el "freno" en Profase I, detente ahí y explica antes de hablar de la ovulación.

### Bloque 4: Aplicación y Patología (Desafíos)
*Checkpoints necesarios para avanzar:*
1. No disyunción cromosómica (errores en la separación).
2. Consecuencias genéticas (Trisomías/Aneuploidías).
3. Relación entre edad materna/materna y riesgos de error meiótico.
- Acción: Presenta casos clínicos breves o problemas lógicos.

### Bloque 5: Metacognición y Cierre
- Acción: Solicita al alumno completar su "Diario de Metacognición" con:
  1. ¿Qué concepto fue tu mayor reto hoy?
  2. ¿Cómo cambió tu idea sobre cómo se crea la vida?
  3. Una duda que aún te quede en el tintero.

# INSTRUCCIONES PARA EL MOTOR DE RAZONAMIENTO
- Antes de cada respuesta, evalúa: "¿Ha demostrado el alumno que comprende el Checkpoint actual?".
- Si la respuesta es ambigua, pide una aclaración antes de dar el Checkpoint por superado.
- Si el alumno responde correctamente pero detectas que lo hace "de memoria" sin entender la lógica, plantea una pregunta de "por qué" o "qué pasaría si...".
"""

# --- BÚSQUEDA DINÁMICA DEL MODELO ---
def get_latest_flash_model():
    try:
        for m in genai.list_models():
            if 'flash' in m.name.lower() and 'generateContent' in m.supported_generation_methods:
                return m.name
    except Exception:
        return 'gemini-1.5-flash'
    return 'gemini-1.5-flash'

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    bienvenida = "¡Hola! Soy tu tutor de Biología. Vamos a trabajar sobre Gametogénesis. Para empezar, ¿cómo te llamas?"
    st.session_state.messages.append({"role": "assistant", "content": bienvenida})

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- MOTOR PRINCIPAL: Lógica de respuesta ---
if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # 1. BALANCEO DE CARGA: Elegimos una llave al azar para esta interacción
            llave_elegida = random.choice(api_keys)
            genai.configure(api_key=llave_elegida)
            
            # 2. INICIALIZACIÓN DEL MODELO
            MODEL_NAME = get_latest_flash_model()
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                system_instruction=SYSTEM_PROMPT,
                generation_config=generation_config
            )

            # 3. VENTANA DE MEMORIA (Sliding Window)
            window_size = 6
            # Extraemos los últimos mensajes para no enviar historiales infinitos
            history_window = st.session_state.messages[-(window_size+1):-1]
            
            # Formateamos el historial recortado para la API
            formatted_history = [
                {"role": m["role"] if m["role"] != "assistant" else "model", "parts": [m["content"]]}
                for m in history_window
            ]

            # 4. ENVIAR CONSULTA
            chat_session = model.start_chat(history=formatted_history)
            response = chat_session.send_message(prompt)
            
            # 5. MOSTRAR Y GUARDAR RESPUESTA
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            # 6. MANEJO DE CUOTA "ANTI-PÁNICO"
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "exhausted" in error_str:
                st.warning("⚠️ **¡Hola! Estoy procesando muchas consultas de tus compañeros.**")
                st.info("Para no saturarme y poder seguir ayudándote, por favor espera unos 30 segundos y vuelve a enviar tu mensaje. ¡Gracias por la paciencia!")
            else:
                st.error(f"Ocurrió un error en la conexión: {e}")
