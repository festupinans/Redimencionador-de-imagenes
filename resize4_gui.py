import os
from tkinter import Tk, filedialog, StringVar, IntVar, BooleanVar, END, BOTH, RIGHT, Y, Listbox
from tkinter import ttk
from PIL import Image

def closest_div4(n):
    """Redondea al múltiplo de 4 más cercano."""
    return n - n % 4 if n % 4 < 2 else n + (4 - n % 4)

def closest_div4_down(n):
    """Redondea hacia abajo al múltiplo de 4 más cercano (para no exceder el máximo)."""
    return n - (n % 4)

def calculate_proportional_size(w, h, max_size):
    """
    Calcula las nuevas dimensiones manteniendo la proporción,
    asegurando que ninguna dimensión exceda max_size y ambas sean divisibles por 4.
    """
    if w <= max_size and h <= max_size:
        # Si ya está dentro del límite, solo ajustar a múltiplo de 4
        new_w = closest_div4(w)
        new_h = closest_div4(h)
        # Verificar que no exceda el límite después del ajuste
        if new_w > max_size:
            new_w = closest_div4_down(max_size)
        if new_h > max_size:
            new_h = closest_div4_down(max_size)
        return new_w, new_h
    
    # Calcular el factor de escala basado en la dimensión más grande
    scale = min(max_size / w, max_size / h)
    
    # Aplicar el factor de escala
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    # Ajustar a múltiplos de 4 hacia abajo (para no exceder el límite)
    new_w = closest_div4_down(new_w)
    new_h = closest_div4_down(new_h)
    
    # Asegurar que no sea 0
    new_w = max(4, new_w)
    new_h = max(4, new_h)
    
    return new_w, new_h

def resize_image(path, overwrite, remove_meta, optimize, quality, out_format, only_resize, use_max_size=False, max_size=2048, use_custom_size=False, custom_width=1000, custom_height=1000):
    try:
        img = Image.open(path)
    except Exception as e:
        raise Exception(f"No se pudo cargar: {e}")

    # --- Guardar metadatos originales si se pide no eliminarlos ---
    exif_data = img.info.get('exif')

    # --- Redimensionar según configuración ---
    w, h = img.size
    
    if use_custom_size and custom_width > 0 and custom_height > 0:
        new_w, new_h = custom_width, custom_height
    elif use_max_size and max_size > 0:
        new_w, new_h = calculate_proportional_size(w, h, max_size)
    else:
        new_w, new_h = closest_div4(w), closest_div4(h)
    
    if (new_w, new_h) != (w, h):
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS
        img = img.resize((new_w, new_h), resample_filter)

    # --- Determinar formato de salida ---
    # Ignorar "solo redimensionar" para el formato si explícitamente eligió uno distinto.
    original_ext = os.path.splitext(path)[1][1:].lower()
    if not original_ext:
        original_ext = "jpg"

    if out_format.lower() == "mantener original":
        out_ext = original_ext
        save_format = img.format or out_ext.upper()
    else:
        out_ext = out_format.lower()
        save_format = out_format.upper()

    FORMAT_MAP = {
        "JPG": "JPEG",
        "JPEG": "JPEG",
        "PNG": "PNG",
        "WEBP": "WEBP",
        "BMP": "BMP",
    }
    save_format = FORMAT_MAP.get(save_format, save_format)
    if save_format == "JPG":
        save_format = "JPEG"

    # --- Manejo seguro de transparencia ---
    if img.mode in ("RGBA", "LA", "P") and save_format in ["JPEG", "BMP"]:
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.split()[-1]
        background.paste(img, mask=alpha)
        img = background
    elif save_format not in ["JPEG", "BMP"] and img.mode not in ["RGB", "RGBA"]:
        if "A" in img.mode or img.mode == "P":
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
    elif save_format in ["JPEG", "BMP"] and img.mode != "RGB":
        img = img.convert("RGB")

    # --- Crear ruta de salida ---
    if overwrite:
        out_path = os.path.splitext(path)[0] + "." + out_ext
    else:
        folder = os.path.join(os.path.dirname(path), 'processed')
        os.makedirs(folder, exist_ok=True)
        base = os.path.splitext(os.path.basename(path))[0]
        out_path = os.path.join(folder, f"{base}.{out_ext}")

    # --- Argumentos de guardado ---
    save_kwargs = {}
    
    if not remove_meta and exif_data:
        save_kwargs['exif'] = exif_data

    # Desvincular 'only_resize' del control principal para que no bloquee otras funciones.
    if optimize and not only_resize:
        save_kwargs['optimize'] = True
    if save_format in ["JPEG", "WEBP"] and not only_resize:
        save_kwargs['quality'] = quality

    img.save(out_path, format=save_format, **save_kwargs)

    # Si se sobrescribe pero cambió el formato, el archivo original con la extensión antigua quedará.
    # Borramos el original si realmente queremos "sobrescribir" la imagen
    if overwrite and os.path.abspath(out_path) != os.path.abspath(path):
        try:
            os.remove(path)
        except OSError:
            pass

    return out_path

# --- INTERFAZ ---

def select_images():
    filetypes = [("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp")]
    paths = filedialog.askopenfilenames(title="Selecciona imágenes", filetypes=filetypes)
    if not paths:
        status.set("No se seleccionaron imágenes.")
        return
    listbox.delete(0, END)
    for p in paths:
        listbox.insert(END, os.path.basename(p))
    selected_images[:] = paths
    status.set(f"{len(paths)} imágenes seleccionadas.")

def process_images():
    if not selected_images:
        status.set("Primero selecciona imágenes.")
        return
    total = len(selected_images)
    pb["maximum"] = total
    pb["value"] = 0

    processed = 0
    for i, path in enumerate(selected_images, 1):
        try:
            resize_image(
                path,
                overwrite_var.get(),
                remove_meta_var.get(),
                optimize_var.get(),
                quality_var.get(),
                format_var.get(),
                only_resize_var.get(),
                use_max_size_var.get(),
                max_size_var.get(),
                use_custom_size_var.get(),
                custom_width_var.get(),
                custom_height_var.get()
            )
            pb["value"] = i
            processed += 1
            root.update_idletasks()
        except Exception as e:
            status.set(f"Error en {os.path.basename(path)}: {e}")

    status.set(f"✅ {processed}/{total} imágenes procesadas correctamente.")
    pb["value"] = 0

# --- UI ---
root = Tk()
root.title("Editor de imágenes avanzado")
root.geometry("650x620")

selected_images = []
status = StringVar()
overwrite_var = BooleanVar(value=True)
remove_meta_var = BooleanVar(value=True)
optimize_var = BooleanVar(value=True)
only_resize_var = BooleanVar(value=True)
quality_var = IntVar(value=85)
format_var = StringVar(value="Mantener original")
use_max_size_var = BooleanVar(value=False)
max_size_var = IntVar(value=2048)
use_custom_size_var = BooleanVar(value=False)
custom_width_var = IntVar(value=1000)
custom_height_var = IntVar(value=1000)

ttk.Label(root, text="Lista de imágenes:").pack(anchor="w", padx=10, pady=5)
frame = ttk.Frame(root)
frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
listbox = Listbox(frame, height=10)
scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
listbox.config(yscrollcommand=scrollbar.set)
listbox.pack(side="left", fill=BOTH, expand=True)
scrollbar.pack(side=RIGHT, fill=Y)

ttk.Button(root, text="Seleccionar imágenes", command=select_images).pack(pady=5)

options_frame = ttk.LabelFrame(root, text="Opciones de procesamiento")
options_frame.pack(fill="x", padx=10, pady=10)
ttk.Checkbutton(options_frame, text="Solo redimensionar", variable=only_resize_var).grid(row=0, column=0, sticky="w", padx=5, pady=2)
ttk.Checkbutton(options_frame, text="Sobrescribir originales", variable=overwrite_var).grid(row=1, column=0, sticky="w", padx=5, pady=2)
ttk.Checkbutton(options_frame, text="Eliminar metadatos EXIF", variable=remove_meta_var).grid(row=2, column=0, sticky="w", padx=5, pady=2)
ttk.Checkbutton(options_frame, text="Optimizar tamaño", variable=optimize_var).grid(row=3, column=0, sticky="w", padx=5, pady=2)
ttk.Checkbutton(options_frame, text="Limitar tamaño máximo", variable=use_max_size_var).grid(row=4, column=0, sticky="w", padx=5, pady=2)
ttk.Label(options_frame, text="Calidad (solo JPG/WebP):").grid(row=1, column=1, padx=5, sticky="e")
ttk.Scale(options_frame, from_=10, to=100, orient="horizontal", variable=quality_var).grid(row=1, column=2, sticky="we", padx=5)
ttk.Label(options_frame, text="Formato de salida:").grid(row=2, column=1, padx=5, sticky="e")
ttk.Combobox(options_frame, textvariable=format_var, values=["Mantener original", "jpg", "png", "webp", "bmp"], width=15, state="readonly").grid(row=2, column=2, sticky="we", padx=5)
ttk.Label(options_frame, text="Tamaño máximo (px):").grid(row=3, column=1, padx=5, sticky="e")
max_size_combo = ttk.Combobox(options_frame, textvariable=max_size_var, values=[32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384], width=15, state="readonly")
max_size_combo.grid(row=3, column=2, sticky="we", padx=5)
max_size_combo.set(2048)

ttk.Checkbutton(options_frame, text="Tamaño exacto (Ignorar prop.)", variable=use_custom_size_var).grid(row=5, column=0, sticky="w", padx=5, pady=2)
ttk.Label(options_frame, text="Ancho exacto (px):").grid(row=4, column=1, padx=5, sticky="e")
ttk.Entry(options_frame, textvariable=custom_width_var, width=15).grid(row=4, column=2, sticky="we", padx=5)
ttk.Label(options_frame, text="Alto exacto (px):").grid(row=5, column=1, padx=5, sticky="e")
ttk.Entry(options_frame, textvariable=custom_height_var, width=15).grid(row=5, column=2, sticky="we", padx=5)

for i in range(3):
    options_frame.columnconfigure(i, weight=1)

pb = ttk.Progressbar(root, mode="determinate")
pb.pack(fill="x", padx=10, pady=5)
ttk.Button(root, text="Procesar imágenes", command=process_images).pack(pady=10)
ttk.Label(root, textvariable=status).pack(pady=5)

root.mainloop()
