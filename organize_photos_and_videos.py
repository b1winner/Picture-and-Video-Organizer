import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime

# --- Third-party libraries ---
# You must install these for the script to work:
# pip install Pillow exifread hachoir
from PIL import Image
import exifread
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

# --- Core Logic ---

def get_media_date(path):
    """
    Extracts the creation date from a photo or video file.
    Returns a datetime object if successful, otherwise None.
    """
    file_ext = os.path.splitext(path)[1].lower()
    photo_extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', '.cr2', '.cr3', '.nef', '.arw', '.orf', '.rw2', '.dng']
    video_extensions = ['.mp4', '.mov', '.avi', '.m4v', '.3gp']

    # --- PHOTO LOGIC ---
    if file_ext in photo_extensions:
        # Try with exifread first for broad (RAW) support
        try:
            with open(path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
                if "EXIF DateTimeOriginal" in tags:
                    date_str = str(tags["EXIF DateTimeOriginal"])
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except Exception:
            pass # Silently fail and try next method

        # Fallback to Pillow for other formats
        try:
            with Image.open(path) as img:
                exif_data = img._getexif()
                if exif_data:
                    date_str = exif_data.get(36867) # DateTimeOriginal tag
                    if date_str:
                        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except Exception:
            pass # Silently fail

    # --- VIDEO LOGIC ---
    elif file_ext in video_extensions:
        try:
            parser = createParser(path)
            if not parser:
                return None
            with parser:
                metadata = extractMetadata(parser)
            if metadata:
                # hachoir can find multiple date fields, we prioritize 'creation_date'
                if metadata.has('creation_date'):
                    return metadata.get('creation_date')
        except Exception as e:
            print(f"Could not read metadata from video {path}: {e}")
            
    return None

def organize_media(source_dir, dest_dir, log_widget):
    """
    Organizes photos and videos from a source directory into a destination directory.
    """
    if not source_dir or not dest_dir:
        messagebox.showerror("Error", "Please select both a source and a destination directory.")
        return

    log_widget.delete('1.0', tk.END) # Clear previous logs
    log_widget.insert(tk.END, f"Starting organization...\nSource: {source_dir}\nDestination: {dest_dir}\n\n")
    log_widget.see(tk.END)
    
    supported_extensions = (
        # Photos
        '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', 
        '.cr2', '.cr3', '.nef', '.arw', '.orf', '.rw2', '.dng',
        # Videos
        '.mp4', '.mov', '.avi', '.m4v', '.3gp'
    )
    files_processed = 0
    files_copied = 0

    for root, _, files in os.walk(source_dir):
        for filename in files:
            if filename.lower().endswith(supported_extensions):
                files_processed += 1
                source_path = os.path.join(root, filename)
                log_widget.insert(tk.END, f"Processing: {filename}\n")
                
                dt_object = get_media_date(source_path)

                # If no metadata date, fall back to file's modification time
                if not dt_object:
                    mod_time = os.path.getmtime(source_path)
                    dt_object = datetime.fromtimestamp(mod_time)
                    log_widget.insert(tk.END, "  -> No metadata date found. Using file modification date.\n")
                
                # --- Create Destination Folder ---
                year = dt_object.strftime('%Y')
                month = dt_object.strftime('%m')
                day = dt_object.strftime('%d')

                target_folder = os.path.join(dest_dir, year, month, day)
                os.makedirs(target_folder, exist_ok=True)

                # --- Create New Filename and Handle Collisions ---
                time_str = dt_object.strftime('%Y-%m-%d_%H-%M-%S')
                file_extension = os.path.splitext(filename)[1]
                new_filename = f"{time_str}{file_extension}"
                dest_path = os.path.join(target_folder, new_filename)

                counter = 1
                while os.path.exists(dest_path):
                    new_filename = f"{time_str}_{counter}{file_extension}"
                    dest_path = os.path.join(target_folder, new_filename)
                    counter += 1

                # --- Copy the File ---
                try:
                    shutil.copy2(source_path, dest_path)
                    files_copied += 1
                    log_widget.insert(tk.END, f"  -> Copied to: {dest_path}\n")
                except Exception as e:
                    log_widget.insert(tk.END, f"  -> ERROR copying file: {e}\n")

                log_widget.see(tk.END)
                root_tk.update_idletasks()

    summary = f"\n--- Organization Complete ---\nFiles Scanned: {files_processed}\nFiles Copied: {files_copied}\n"
    log_widget.insert(tk.END, summary)
    log_widget.see(tk.END)
    messagebox.showinfo("Complete", "Media organization process has finished!")

# --- GUI Setup ---
def create_gui():
    """Creates the graphical user interface for the application."""
    global root_tk
    root_tk = tk.Tk()
    root_tk.title("Photo & Video Organizer")
    root_tk.geometry("700x500")

    frame = tk.Frame(root_tk, padx=10, pady=10)
    frame.pack(fill=tk.X, padx=10, pady=5)

    lbl_source = tk.Label(frame, text="Source Folder:")
    lbl_source.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    entry_source = tk.Entry(frame, width=60)
    entry_source.grid(row=0, column=1, padx=5, pady=5)
    btn_source = tk.Button(frame, text="Browse...", command=lambda: entry_source.insert(0, filedialog.askdirectory()))
    btn_source.grid(row=0, column=2, padx=5, pady=5)

    lbl_dest = tk.Label(frame, text="Destination Folder:")
    lbl_dest.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    entry_dest = tk.Entry(frame, width=60)
    entry_dest.grid(row=1, column=1, padx=5, pady=5)
    btn_dest = tk.Button(frame, text="Browse...", command=lambda: entry_dest.insert(0, filedialog.askdirectory()))
    btn_dest.grid(row=1, column=2, padx=5, pady=5)

    log_frame = tk.Frame(root_tk, padx=10, pady=10)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
    log_widget.pack(fill=tk.BOTH, expand=True)

    btn_start = tk.Button(
        root_tk,
        text="Start Organizing",
        font=('Helvetica', 12, 'bold'),
        bg='#4CAF50',
        fg='white',
        command=lambda: organize_media(entry_source.get(), entry_dest.get(), log_widget)
    )
    btn_start.pack(pady=10)

    root_tk.mainloop()

if __name__ == "__main__":
    # Before running, ensure you have the necessary libraries installed.
    # Open a terminal or command prompt and run:
    # pip install Pillow exifread hachoir
    create_gui()
