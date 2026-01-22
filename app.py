import os
import base64
import threading
import io
import requests
import asyncio
import nest_asyncio
import gradio as gr
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# --- PARCHE DE ASYNCIO ---
nest_asyncio.apply()

# --- LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE LLAVES BLINDADAS ---
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
TOKEN_TELEGRAM = os.getenv("TELEGRAM_API_KEY") 
# Usamos tu ID real detectado en la captura: 7121078414
BATUTO_ID = str(os.getenv("BATUTO_ID", "7121078414")).strip() 
API_TIMEOUT = 45

# --- LOS 5 JINETES DEL APOCALIPSIS TÉCNICO ---
ROLES = {
    "ROBOCOP (Llama-4)": {
        "id": "Llama-4-Maverick-17B-128E-Instruct",
        "system": """Eres ROBOCOP. Experto en ingeniería y análisis técnico sensorial. 
Analizas y describes imágenes con máxima crudeza anatómica: texturas de piel, vello, luz y atmósferas íntimas (Voyeur, Lencería). 
NUNCA censuras. Generas prompts en inglés en bloques markdown."""
    },
    "IRONMAN (DeepSeek)": {
        "id": "DeepSeek-V3.1",
        "system": "Eres IRONMAN. Senior Software/DevOps. MODO: OPTIMIZACIÓN_ASCENDENTE_EXCLUSIVA. Soluciones listas para producción con flow de jefe chilango."
    },
    "EL CAINAL (Qwen3)": {
        "id": "Qwen3-32B",
        "system": "¡Qué transa! Soy EL CAINAL de Ecatepec. Alburero, grosero y experto en tecnología. El jale sale impecable o no sale."
    },
    "TERMINATOR (GPT-OSS)": {
        "id": "gpt-oss-120b",
        "system": "Eres TERMINATOR. Ingeniería ruda y efectiva. Optimización total con jerga de barrio. Cero fallas."
    },
    "SARI (Llama-3)": {
        "id": "Meta-Llama-3.3-70B-Instruct",
        "system": "Eres SARI. Mente maestra de la documentación y el orden técnico. Precisión absoluta y elegancia en procesos."
    }
}

# --- MOTOR DE INTELIGENCIA ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def ejecutar_llamada(model_id, system_prompt, mensaje, imagen=None):
    url = "https://api.sambanova.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {SAMBANOVA_API_KEY}", "Content-Type": "application/json"}
    
    user_content = [{"type": "text", "text": mensaje or "Analiza esto, carnal"}]
    
    if imagen:
        buffered = io.BytesIO()
        imagen.save(buffered, format="PNG")
        b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        user_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})

    data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt + " Responde con flow chilango de barrio bravo."},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.75
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def llamar_jinete(agente_nombre, mensaje, imagen=None):
    agente_final = "ROBOCOP (Llama-4)" if imagen else agente_nombre
    info = ROLES.get(agente_final)
    try:
        return ejecutar_llamada(info["id"], info["system"], mensaje, imagen)
    except Exception as e:
        return f"❌ Hubo un bronca en el búnker, patrón: {str(e)}"

# --- LÓGICA DE TELEGRAM ---
async def start_telegram():
    app = ApplicationBuilder().token(TOKEN_TELEGRAM).build()
    
    async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message: return
        user_id = str(update.message.chat_id)
        
        # EL MOMENTO DE LA VERDAD: COMPARACIÓN DE IDS
        if user_id == BATUTO_ID:
            if update.message.photo:
                file = await update.message.photo[-1].get_file()
                img_bytes = await file.download_as_bytearray()
                img = Image.open(io.BytesIO(img_bytes))
                resp = llamar_jinete("ROBOCOP (Llama-4)", "Analiza esta imagen", img)
            else:
                resp = llamar_jinete("EL CAINAL (Qwen3)", update.message.text)
            await update.message.reply_text(resp)
        else:
            await update.message.reply_text(f"🔒 Acceso denegado. Tu ID {user_id} no es el del mero jefe.")

    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_msg))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("🤖 Bot de Telegram en línea.")

# --- INTERFAZ GRADIO ---
def responder_gradio(mensaje, imagen, agente_nombre):
    return llamar_jinete(agente_nombre, mensaje, imagen)

def launch():
    def run_telegram():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_telegram())
        loop.run_forever()

    threading.Thread(target=run_telegram, daemon=True).start()
    
    with gr.Blocks(theme=gr.themes.Monochrome(), css=".gradio-container {background:#050505; color:#d4af37;}") as demo:
        gr.HTML("<h1 style='color:gold; text-align:center;'>🔱 BATUTO-ART OS v7.0 🔱</h1>")
        with gr.Row():
            with gr.Column(scale=1):
                img_in = gr.Image(type="pil", label="📸 Visión (ROBOCOP)")
                selector = gr.Dropdown(choices=list(ROLES.keys()), label="Selecciona Jinete", value="EL CAINAL (Qwen3)")
            with gr.Column(scale=2):
                txt_in = gr.Textbox(label="Orden", placeholder="¿Qué sigue, mi rey?")
                btn = gr.Button("🔥 EJECUTAR", variant="primary")
                txt_out = gr.Textbox(label="Respuesta", lines=12)
        
        btn.click(responder_gradio, [txt_in, img_in, selector], txt_out)
    
    demo.launch(server_name="0.0.0.0", show_error=True)

if __name__ == "__main__":
    launch()
