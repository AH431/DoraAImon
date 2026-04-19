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

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

current_context = ""
BOOKMARKS_FILE = "bookmarks.json"
UPLOAD_DIR = r"C:\Users\archi\OneDrive\Desktop\DoraAImon\uploads"

def save_chat_export(history):
    if not history: return None
    path = os.path.join(os.path.expanduser("~"), "Downloads", "DoraAImon_Chat_Export.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# 🎓 DoraAImon 對話紀錄\n\n")
        # Handle Gradio 6 format (list of dicts/message objects)
        if hasattr(history[0], "role") or isinstance(history[0], dict):
            for msg in history:
                role = msg.get("role") if isinstance(msg, dict) else msg.role
                content = msg.get("content") if isinstance(msg, dict) else msg.content
                if role == "user":
                    f.write(f"### 👤 您：\n{content}\n\n")
                else:
                    f.write(f"### 🎓 助教：\n{content}\n\n---\n")
        # Handle older Gradio versions format (list of pairs)
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

def chat_interface_fn(message, history):
    global current_context
    try:
        text_context = current_context[:10000] if current_context else "無額外參考資料。"
        prompt = f"請扮演美國脫口秀界傳奇主持人 Conan O'Brien（康納·歐布萊恩），用他那種充滿自嘲、誇張機智又有時帶點神經質的幽默風格來提供充滿知識含量的學習指導。參考內容: {text_context}\n\n用戶提問: {message}"
        if message.startswith("/plan"):
            prompt = f"請扮演 Conan O'Brien，用他那招牌的機智與搞笑方式（可能順便調侃一下你的製作人 Jordan Schlansky 或是吐槽自己的頭髮），幫用戶規劃讀書進度: {message.replace('/plan', '')}. 資料: {text_context}"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text if response.text else "助教沒有產出內容，請換個方式問問看。"
    except Exception as e:
        return f"❌ 系統錯誤: {str(e)}"

custom_css = """
body { background-color: #F0F8FF; }
.gradio-container { background-color: #E3F2FD !important; border-radius: 20px; border: 1px solid #BBDEFB; }
#chatbot { background-color: white !important; }
"""

with gr.Blocks() as demo:
    gr.Markdown("# 🎓 DoraAImon 智慧助教")
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(label="上傳筆記或考題", file_count="multiple")
            topic_input = gr.Textbox(label="自訂主題名稱 (選填)")
            load_btn = gr.Button("解析並儲存", variant="primary", size="sm")
            status = gr.Textbox(label="狀態", interactive=False, show_label=False)
            bookmarks = gr.Dropdown(label="書籤切換", choices=list(get_bookmarks().keys()))
            
            exp_chat = gr.Button("匯出對話紀錄", variant="secondary", size="sm")
            download_file = gr.File(label=None, show_label=False, height=100)

            bookmarks.change(switch_bookmark, inputs=[bookmarks], outputs=[status])
            load_btn.click(load_files, inputs=[file_input, topic_input], outputs=[status, bookmarks])

        with gr.Column(scale=4):
            chatbot = gr.ChatInterface(fn=chat_interface_fn, chatbot=gr.Chatbot(height=650))
            exp_chat.click(fn=save_chat_export, inputs=[chatbot.chatbot], outputs=[download_file])

if __name__ == "__main__":
    def open_browser(): webbrowser.open_new("http://127.0.0.1:7860")
    threading.Timer(1, open_browser).start()
    demo.queue().launch(theme=gr.themes.Soft(), css=custom_css, server_name="127.0.0.1", server_port=7860)
