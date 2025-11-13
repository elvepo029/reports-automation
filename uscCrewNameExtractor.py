import tkinter as tk
from tkinter import filedialog, messagebox
from pdf2image import convert_from_path
import pytesseract
import re
from PIL import Image

# ✅ Configura Tesseract a Windows
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\eloi.verge\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

# ✅ Ruta Poppler a Windows
POPPLER_PATH = r"C:\Users\eloi.verge\poppler\Library\Bin"

# Llista de rols que volem trobar
ROLES = [
    "Data Entry Scorer",
    "Caller / Backup 1",
    "Caller / Backup 2",
    "Timer",
    "Shot Clock Operator",
    "IRS Operator (EL Only)"
]

def extract_roles(pdf_path):
    results = {}
    # Convertim PDF a imatges
    pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
    
    for i, page in enumerate(pages):
        text = pytesseract.image_to_string(page)
        if not text:
            continue
        for role in ROLES:
            # Buscar línia amb el rol i el nom després
            pattern = rf"{role}(?:\s*\(.*?\))?\s*[:\-]?\s*(.*)"
            match = re.search(pattern, text)
            if match:
                results[role] = match.group(1).strip()
                print(results[role])
    return results

def upload_file():
    file_path = filedialog.askopenfilename(
        title="Selecciona el PDF",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not file_path:
        return

    try:
        results = extract_roles(file_path)
        output_text.delete(1.0, tk.END)
        if results:
            for role, name in results.items():
                output_text.insert(tk.END, f"{role}: {name}\n")
        else:
            messagebox.showinfo("Resultat", "No s'han trobat noms.")
    except Exception as e:
        messagebox.showerror("Error", f"No s'ha pogut llegir el PDF:\n{e}")

# Crear la finestra
root = tk.Tk()
root.title("Extractor de noms del PDF (OCR)")
root.geometry("500x400")

# Botó per pujar el fitxer
upload_button = tk.Button(root, text="📂 Pujar PDF", command=upload_file, font=("Arial", 12))
upload_button.pack(pady=20)

# Àrea per mostrar els resultats
output_text = tk.Text(root, height=15, width=60, font=("Courier", 10))
output_text.pack(padx=10, pady=10)

# Iniciar la interfície
root.mainloop()

