import gradio as gr
from google import genai
import os
import shutil
import PyPDF2
import json
import webbrowser
import threading
from docx import Document
from dotenv import load_dotenv
from fpdf import FPDF
from datetime import datetime

load_dotenv()

# ==========================================================
# CRITICAL: DO NOT MODIFY THE CHATBOT CORE LOGIC BELOW
# This section (API init, client config, chat_interface_fn) 
# is currently working perfectly. DO NOT TOUCH.
# ==========================================================
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def chat_interface_fn(message, history):
    global current_context
    try:
        # 限制 Context 長度以節省 Token，並要求 AI 精簡回答
        text_context = current_context[:10000] if current_context else "無額外參考資料。"
        prompt = f"你的名字叫「哆啦AI夢」，是一隻來自未來的無毛機器貓。請以脫口秀天后 Oprah Winfrey (歐普拉) 溫暖、充滿啟發性但又極具權威感的風格來回答問題（絕對不可自稱歐普拉或提及她是誰，因為你是一隻無毛機器貓）。另外，請將所有的閒聊與情緒鋪陳縮減至極限（比之前還要再減少 50%），以非常簡潔精煉的方式，直接提供充滿知識含量的學習指導。參考內容: {text_context}\n\n用戶提問: {message}"
        if message.startswith("/plan"):
            prompt = f"你的名字叫「哆啦AI夢」，是一隻來自未來的無毛機器貓。請模仿 Oprah Winfrey 溫暖激勵的風格（但不自稱是她），並將閒聊對白縮減至極限（去除所有不必要的廢話），非常簡短且直接地幫用戶規劃讀書進度: {message.replace('/plan', '')}. 資料: {text_context}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text if response.text else "助教沒有產出內容，請換個方式問問看。"
    except Exception as e:
        return f"❌ 系統錯誤: {str(e)}"
# ==========================================================
# END OF CRITICAL SECTION
# ==========================================================

current_context = ""
BOOKMARKS_FILE = "bookmarks.json"
UPLOAD_DIR = r"C:\Users\archi\OneDrive\Desktop\DoraAImon\uploads"

def save_chat_export(history):
    if not history: return None
    
    # 產生主旨摘要 (使用與 chat_interface_fn 相同的 client)
    summary_prompt = "請根據以下對話紀錄，幫我取一個簡短的 5-10 字對話主旨：" + str(history[-3:])
    try:
        res = client.models.generate_content(model="gemini-2.5-flash", contents=summary_prompt)
        topic = res.text.strip().replace(" ", "_")
    except:
        topic = "對話紀錄"
        
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}_{topic}.md"
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    path = os.path.join(download_dir, filename)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# 🎓 DoraAImon 對話紀錄 - {topic}\n\n")
        # Handle Gradio 6 format (list of dicts/objects) vs old format
        if history and (hasattr(history[0], "role") or isinstance(history[0], dict)):
            for msg in history:
                role = msg.get("role") if isinstance(msg, dict) else msg.role
                content = msg.get("content") if isinstance(msg, dict) else msg.content
                if role == "user":
                    f.write(f"### 👤 您：\n{content}\n\n")
                else:
                    f.write(f"### 🎓 助教：\n{content}\n\n---\n")
        else:
            for human, ai in history:
                f.write(f"### 👤 您：\n{human}\n\n### 🎓 助教：\n{ai}\n\n---\n")
    return path

def get_bookmarks():
    if os.path.exists(BOOKMARKS_FILE):
        try:
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}

def read_files_to_context(file_names):
    global current_context
    new_context = ""
    for name in file_names:
        path = os.path.join(UPLOAD_DIR, name)
        if not os.path.exists(path): continue
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".pdf":
                reader = PyPDF2.PdfReader(path)
                new_context += "\n".join([page.extract_text() for page in reader.pages]) + "\n"
            elif ext == ".docx":
                doc = Document(path)
                new_context += "\n".join([para.text for para in doc.paragraphs]) + "\n"
            elif ext in [".txt", ".md"]:
                with open(path, "r", encoding="utf-8") as f:
                    new_context += f.read() + "\n"
        except: continue
    current_context = new_context
    return f"✅ 已載入 {len(file_names)} 個檔案。"

def load_files(files, topic_name):
    bookmarks = get_bookmarks()
    if files:
        if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
        file_names = []
        for file in files:
            save_path = os.path.join(UPLOAD_DIR, os.path.basename(file.name))
            shutil.copy(file.name, save_path)
            file_names.append(os.path.basename(file.name))
        topic = topic_name if topic_name else "新主題"
        bookmarks[topic] = file_names
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, ensure_ascii=False)
        return read_files_to_context(file_names), gr.Dropdown(choices=list(bookmarks.keys()), value=topic)
    return "⚠️ 請上傳檔案", gr.Dropdown(choices=list(bookmarks.keys()))

def switch_bookmark(topic):
    bookmarks = get_bookmarks()
    if topic in bookmarks: return read_files_to_context(bookmarks[topic])
    return "⚠️ 找不到該主題"

custom_css = """
body { background-color: #F0F8FF; font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif; }
.gradio-container { background-color: #E3F2FD !important; border-radius: 20px; border: 1px solid #BBDEFB; }
#chatbot { background-color: white !important; font-size: 16px; }
"""

with gr.Blocks(title="DoraAImon 智慧助教") as demo:
    gr.Markdown("# 🎓 DoraAImon 智慧助教")
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="上傳筆記或考題", file_count="multiple")
            topic_input = gr.Textbox(label="自訂主題名稱 (選填)")
            load_btn = gr.Button("解析並儲存", variant="primary", size="sm")
            status = gr.Textbox(label="狀態", interactive=False, show_label=False)
            bookmarks = gr.Dropdown(label="書籤切換", choices=list(get_bookmarks().keys()))
            
            exp_chat = gr.Button("匯出對話記錄", variant="secondary", size="sm")
            download_file = gr.File(label=None, show_label=False, height=60, container=False)

            bookmarks.change(switch_bookmark, inputs=[bookmarks], outputs=[status])
            load_btn.click(load_files, inputs=[file_input, topic_input], outputs=[status, bookmarks])

        with gr.Column(scale=4):
            chatbot = gr.ChatInterface(fn=chat_interface_fn, chatbot=gr.Chatbot(height=650))
            exp_chat.click(fn=save_chat_export, inputs=[chatbot.chatbot], outputs=[download_file])

if __name__ == "__main__":
    def open_browser(): webbrowser.open_new("http://127.0.0.1:7860")
    threading.Timer(1, open_browser).start()
    demo.queue().launch(theme=gr.themes.Soft(), css=custom_css)
