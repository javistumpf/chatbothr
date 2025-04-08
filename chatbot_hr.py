import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
from datetime import datetime

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

if not GOOGLE_API_KEY:
    st.error("Falta la API key de Google. Por favor, configúrala en el archivo .streamlit/secrets.toml.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('gemini-1.5-flash')

agradecimientos = [
    "Gracias por compartirlo.",
    "Entiendo, gracias.",
    "Lo valoro, gracias.",
    "Gracias, lo tengo en cuenta.",
    "Bien, gracias por comentarlo."
]

def load_active_jobs():
    try:
        df = pd.read_excel("bd_busquedas.xlsx")
        active_jobs = df[df["estado"] == "Activa"]["Puesto"].tolist()
        return active_jobs
    except Exception as e:
        st.error(f"Error al cargar los puestos desde Excel: {e}")
        return []

def generate_interview_questions(job_title):
    prompt = f"""
    Eres un entrevistador profesional.
    Vas a realizar una entrevista a un candidato para el puesto de {job_title}.
    Genera 10 preguntas diversas (sin repetir) que cubran:
    - Experiencia laboral
    - Habilidades técnicas
    - Habilidades blandas
    - Motivación
    Cada pregunta debe ser clara y concisa.
    Devuelve solo la lista de preguntas, una por línea.
    """
    response = model.generate_content(prompt)
    return [q for q in response.text.strip().split("\n") if q.strip()]

def evaluate_candidate(job_title, answers):
    prompt = f"""
    Eres un experto en selección de personal. Evalúa al candidato para el puesto de {job_title}.
    A partir de sus respuestas:
    - Califica de 1 a 10 en habilidades técnicas
    - Califica de 1 a 10 en habilidades blandas
    - Da una calificación general de 1 a 10
    - Incluye un comentario breve y objetivo
    Respuestas del candidato:
    {answers}
    Formato:
    Habilidades Técnicas: [calificación]
    Habilidades Blandas: [calificación]
    Evaluación General: [calificación]
    Comentario: [comentario breve]
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def save_results(name, job, answers, evaluation):
    filename = "resultados_entrevistas.xlsx"
    data = {
        "Nombre": [name],
        "Puesto": [job],
        "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M")],
        "Respuestas": [answers],
    }
    for line in evaluation.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = [value.strip()]
    df_new = pd.DataFrame(data)
    if os.path.exists(filename):
        df_old = pd.read_excel(filename)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_excel(filename, index=False)

st.title("Entrevista Automatizada con IA")

st.subheader("Cómo funciona")
st.write("""
Esta aplicación automatiza el proceso de entrevista para diferentes puestos. Aquí te explicamos cómo funciona:

**Características Claves:**
- **Selección de Puesto:** Elige el puesto al que deseas simular una entrevista.
- **Entrevista con IA:** Responde a las preguntas generadas por la IA como si estuvieras en una entrevista real.
- **Evaluación Automática:** Al finalizar, la IA evalúa tus respuestas y proporciona una calificación en habilidades técnicas y blandas, además de un comentario general.

**Cómo Realizar las Solicitudes:**
1. **Selecciona el Puesto:** Utiliza el menú desplegable para elegir el puesto.
2. **Ingresa tu Nombre:** Escribe tu nombre en el campo de texto.
3. **Inicia la Entrevista:** Haz clic en el botón "Iniciar Entrevista".
4. **Responde las Preguntas:** Escribe tus respuestas en el cuadro de texto y presiona Enter.

**Qué Esperar:**
- Recibirás preguntas de la IA, una por una.
- Después de responder todas las preguntas, recibirás una evaluación de tu desempeño.

¡Mucha suerte en tu entrevista!
""")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "step" not in st.session_state:
    st.session_state.step = "inicio"
if "answers" not in st.session_state:
    st.session_state.answers = []
if "question_index" not in st.session_state:
    st.session_state.question_index = 0
if "questions" not in st.session_state:
    st.session_state.questions = []
if "disabled" not in st.session_state:
    st.session_state.disabled = False

active_jobs = load_active_jobs()
col1, col2 = st.columns(2)

with col1:
    job_title = st.selectbox("Seleccioná el puesto al que aplicás:", active_jobs)
with col2:
    candidate_name = st.text_input("Tu nombre:")

if st.session_state.step == "inicio" and job_title and candidate_name:
    if st.button("Iniciar Entrevista"):
        st.session_state.questions = generate_interview_questions(job_title)
        st.session_state.step = "entrevista"
        saludo = f"Hola {candidate_name}, gracias por presentarte. Vamos a comenzar con la entrevista para el puesto de **{job_title}**."
        st.session_state.messages.append({"role": "assistant", "content": saludo})
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.questions[0]})
        st.session_state.question_index = 1

if st.session_state.step == "entrevista":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not st.session_state.disabled:
        if prompt := st.chat_input("Escribí tu respuesta..."):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.answers.append(prompt)

            if st.session_state.question_index < len(st.session_state.questions):
                comentario = agradecimientos[st.session_state.question_index % len(agradecimientos)]
                siguiente = st.session_state.questions[st.session_state.question_index]
                with st.chat_message("assistant"):
                    st.markdown(comentario)
                    st.markdown(siguiente)
                st.session_state.messages.append({"role": "assistant", "content": siguiente})
                st.session_state.question_index += 1
            else:
                st.session_state.step = "finalizado"
                st.session_state.disabled = True
                answers_str = "\n".join(st.session_state.answers)
                evaluacion = evaluate_candidate(job_title, answers_str)
                save_results(candidate_name, job_title, answers_str, evaluacion)
                with st.chat_message("assistant"):
                    st.markdown("Gracias por completar la entrevista.\n\nLa entrevista ha finalizado. Nos pondremos en contacto para informarte sobre los próximos pasos del proceso. ¡Muchos éxitos en lo que viene!")
