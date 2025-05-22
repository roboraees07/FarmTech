import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import os
from datetime import datetime
from PIL import Image, ImageTk
import cv2
from hx711 import HX711
import RPi.GPIO as GPIO
import arabic_reshaper
from bidi.algorithm import get_display
from tkinter import font
import requests
import base64

def upload_vegetable_data(endpoint_url, image_path, weight, veg_name, date_time):
    """
    Uploads a vegetable image and metadata to the Firebase Cloud Function.
    """
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    image_base64 = base64.b64encode(img_bytes).decode('utf-8')

    if isinstance(date_time, datetime):
        date_time = date_time.isoformat()

    # payload = {
    #     "imageBase64": image_base64,
    #     "weight": str(weight),
    #     "vegName": veg_name,
    #     "dateTime": date_time
    # }
    
    payload = {
        "imageBase64": image_base64,
        "weight": str(weight),
        "vegName": veg_name,
        "dateTime": date_time,
        "uploadedAt": date_time  # add this line
    }


    headers = {"Content-Type": "application/json"}
    resp = requests.post(endpoint_url, json=payload, headers=headers)

    try:
        data = resp.json()
    except ValueError:
        resp.raise_for_status()

    if resp.status_code != 200:
        error_msg = data.get("error", resp.text)
        raise Exception(f"Upload failed [{resp.status_code}]: {error_msg}")

    return data


# Define paths
CALIBRATION_FILE = "/home/admin/development/farmtech-weightscale/scale_calibration.json"
FIREBASE_FUNCTION_URL = "https://uploadvegetabledata-6nsemxyzkq-uc.a.run.app"
DATA_FILE = "/home/admin/development/farmtech-weightscale/measurement_data.json"
SAVE_IMAGE_PATH = "/home/admin/development/farmtech-weightscale/saved_images/"
WELCOME_IMAGE_PATH = (
    "/home/admin/development/farmtech-weightscale/Resources/Screen 01.png"
)
BG_IMAGE_PATH = "/home/admin/development/farmtech-weightscale/Resources/bg.png"
VEG_IMAGES = {
    "Brinjal": "/home/admin/development/farmtech-weightscale/Resources/Brinjal.jpeg",
    "Cucumber": "/home/admin/development/farmtech-weightscale/Resources/Cucumber.jpeg",
    "Rice": "/home/admin/development/farmtech-weightscale/Resources/Rice.jpeg",
    "Carrot": "/home/admin/development/farmtech-weightscale/Resources/Carrot.jpeg",
}

# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
hx = HX711(dout_pin=22, pd_sck_pin=26)

# Ensure directories exist
os.makedirs(SAVE_IMAGE_PATH, exist_ok=True)
urdu_font = ("Noto Sans Arabic", 20)

def urdu_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)


class WeightCellApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FarmTech: Weight Cell Application")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#073343")  # Set background color to green
        self.selected_vegetable = None
        self.cap = cv2.VideoCapture(0)  # Open USB camera
        self.get_calibration()  # Load calibration on startup
        self.init_ui()
        self.show_welcome()
        self.root.bind("<Escape>", self.exit_app)

    def init_ui(self):
        self.frame = tk.Frame(
            self.root, bg="#073343"
        )  # Set frame background color to green
        self.frame.pack(fill=tk.BOTH, expand=True)

    def show_welcome(self):
        self.clear_frame()
        img = Image.open(WELCOME_IMAGE_PATH).resize(
            (self.root.winfo_screenwidth(), self.root.winfo_screenheight()),
            Image.LANCZOS,
        )
        imgtk = ImageTk.PhotoImage(img)
        label = tk.Label(self.frame, image=imgtk, bg="#073343")
        label.image = imgtk
        label.pack(fill=tk.BOTH, expand=True)
        self.root.after(2000, self.show_main_menu)

    def show_main_menu(self):
        self.clear_frame()
        # Background Image
        bg_image = Image.open(BG_IMAGE_PATH)
        bg_image = bg_image.resize(
            (self.root.winfo_screenwidth(), self.root.winfo_screenheight()),
            Image.LANCZOS,
        )
        self.bg_photo = ImageTk.PhotoImage(bg_image)
        bg_label = tk.Label(self.frame, image=self.bg_photo)
        bg_label.place(relwidth=1, relheight=1)

        # tk.Button(self.frame, text="Measure Weight", font=("Arial", 20), command=self.show_vegetable_selection, bg="white").pack(expand=True, pady=20)
        # tk.Button(self.frame, text="Calibrate the Cell", font=("Arial", 20), command=self.show_calibration, bg="white").pack(expand=True, pady=10)

        urdu_font = ("Noto Sans Arabic", 20)
        tk.Button(
            self.frame,
            
            text=urdu_text("وزن ناپیں"),
            
            #text=urdu_text("وزن ماپیوزن ناپیں"),
            font=urdu_font,
            command=self.show_vegetable_selection,
            bg="white",
        ).pack(expand=True, pady=20)
        tk.Button(
            self.frame,
            text=urdu_text("کیلریبرٹ کریں"),
            font=urdu_font,
            command=self.show_calibration,
            bg="white",
        ).pack(expand=True, pady=10)

    def show_calibration(self):
		
        
        #------------------------
        self.clear_frame()

        bg_image = Image.open(BG_IMAGE_PATH)
        bg_image = bg_image.resize(
            (self.root.winfo_screenwidth(), self.root.winfo_screenheight()),
            Image.LANCZOS,
        )
        self.bg_photo = ImageTk.PhotoImage(bg_image)
        bg_label = tk.Label(self.frame, image=self.bg_photo)
        bg_label.place(relwidth=1, relheight=1)

        # Label at the top
        label = tk.Label(
            self.frame,
            text=urdu_text("وزن ناپنے کا عمل"),
            #text=urdu_text( " عمل کا  ناپنے  وزن "),
            #text=urdu_text("وزن ماپنے کا عموزن ناپنے کا عمل"),
            font=urdu_font,
            bg="white",
        )
        label.pack(pady=30)
        
        # Larger video display
        self.video_label = tk.Label(self.frame, bg="white")
        self.video_label.pack(pady=20, expand=True)
        self.update_video()

        ## Calibration button
        btn = tk.Button(
            self.frame,
            text=urdu_text("تمام اشیاء ہٹا دیں اور درج کریں"),
            font=urdu_font,
            command=self.zero_scale,
            bg="white",
        )
        btn.pack(pady=15)

        ## Back button at the bottom
        self.back_button()
        
        #**********************

    def zero_scale(self):
        hx.zero()
        
        messagebox.showinfo(urdu_text("ترازو"), urdu_text("ترازو زیرو ہو چکا ہے"))
        reading = hx.get_data_mean(readings=100)
        response = messagebox.askokcancel(
            urdu_text("کیلریبرٹ"), urdu_text(f"اوسط پیمائش: {reading}")
        )
        if response:
            self.get_known_weight()

    def get_known_weight(self):
        value = simpledialog.askfloat(
            urdu_text("کیلریبرٹ"), urdu_text("معروف وزن درج کریں (گرام میں):")
        )
        if value:
            reading = hx.get_data_mean(readings=100)
            ratio = reading / value
            self.save_calibration(ratio)

    def save_calibration(self, ratio):
        with open(CALIBRATION_FILE, "w") as f:
            json.dump({"ratio": ratio}, f)
        messagebox.showinfo(
            urdu_text("کیلریبرٹ"), urdu_text(f"نیا تناسب محفوظ ہو چکا ہے: {ratio}")
        )
        hx.set_scale_ratio(ratio)
        self.show_main_menu()

    def show_vegetable_selection(self):
        self.clear_frame()

        # Set background image
        bg_image = Image.open(BG_IMAGE_PATH)
        bg_image = bg_image.resize(
            (self.root.winfo_screenwidth(), self.root.winfo_screenheight()),
            Image.LANCZOS,
        )
        self.bg_photo = ImageTk.PhotoImage(bg_image)
        bg_label = tk.Label(self.frame, image=self.bg_photo)
        bg_label.place(relwidth=1, relheight=1)

        # Title Label
        tk.Label(
            self.frame,
            text=urdu_text("ایک سبزی منتخب کریں"),
            font=urdu_font,
            bg="#073343",
            fg="white",
        ).pack(pady=10)

        # Frame for vegetable selection (centered)
        veg_frame = tk.Frame(self.frame, bg="#073343")
        veg_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)  # Centering the frame

        # Convert images to a 2x2 grid layout
        row, col = 0, 0
        for index, (veg_name, veg_path) in enumerate(VEG_IMAGES.items()):
            img = Image.open(veg_path).resize((120, 120), Image.LANCZOS)
            img = ImageTk.PhotoImage(img)

            btn = tk.Button(
                veg_frame,
                image=img,
                text=veg_name,
                compound=tk.TOP,
                font=("Arial", 16),
                command=lambda v=veg_name: self.show_measure_weight(v),
                bg="#073343",
                bd=0,
                highlightthickness=0,
                relief=tk.FLAT,  # No strokes or borders
            )
            btn.image = img
            btn.grid(row=row, column=col, padx=15, pady=15)  # Grid placement

            col += 1
            if col > 1:  # 2 items per row
                col = 0
                row += 1

        # Back button at the bottom
        # Back button at the bottom
        back_btn = tk.Button(
            self.frame,
            text="Back",
            font=urdu_font,
            bg="red",
            fg="white",
            command=self.back_button,
        )
        back_btn.place(relx=0.5, rely=0.9, anchor=tk.CENTER)  # Positioned at the bottom

    def show_measure_weight(self, vegetable):
        # load the calibration
        calibration_ratio = self.get_calibration()
        if calibration_ratio is None:
            messagebox.showerror("Calibration not found")

        # Set the calibration
        if calibration_ratio is not None:
            hx.set_scale_ratio(calibration_ratio)
            print(f"کیلیبریشن تناسب مقرر کریں: {calibration_ratio}")
        else:
            messagebox.showerror(
                "Error",
                "کیلیبریشن کے ڈیٹا کی کمی ہے۔ براہ کرم پہلے اسکیل کو کیلیبریٹ کریں۔.",
            )
            return

        # zero the scale
        hx.zero()
        print("اسکیل کو صفر کر دیا گیا۔")
        self.selected_vegetable = vegetable
        self.clear_frame()
        bg_image = Image.open(BG_IMAGE_PATH)
        bg_image = bg_image.resize(
            (self.root.winfo_screenwidth(), self.root.winfo_screenheight()),
            Image.LANCZOS,
        )
        self.bg_photo = ImageTk.PhotoImage(bg_image)
        bg_label = tk.Label(self.frame, image=self.bg_photo)
        bg_label.place(relwidth=1, relheight=1)

        img = Image.open(VEG_IMAGES[vegetable]).resize((200, 200), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(img)
        veg_image_label = tk.Label(self.frame, image=imgtk, bg="#073343")
        veg_image_label.image = imgtk
        veg_image_label.place(relx=0.05, rely=0.40, x=20, y=20)
        self.weight_label = tk.Label(
            self.frame, text="Weight: 0.0g", font=("Arial", 30), bg="#073343", fg="#FFFFFF"
        )
        self.weight_label.pack(expand=True)
        tk.Label(
            self.frame,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            font=("Arial", 16),
            bg="#073343",
            fg="#FFFFFF"
        ).pack()
        tk.Button(
            self.frame,
            text="Save",
            font=("Arial", 16),
            command=self.save_measurement,
            bg="white",
        ).pack(pady=10)
        self.back_button()
        self.video_label = tk.Label(self.frame, bg="#073343")
        self.video_label.place(relx=0.70, rely=0.45, width=200, height=200)
        self.update_video()
        self.update_weight()

    def update_weight(self):
        try:
            weight = hx.get_weight_mean()
            if weight is not None:
                self.weight_label.config(text=f"Weight: {weight:.1f}g")
            else:
                self.weight_label.config(text="Error reading weight")
        except Exception as e:
            self.weight_label.config(text=f"Error: {str(e)}")
        self.root.after(1000, self.update_weight)

    def update_video(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (200, 200))
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            self.video_label.config(image=img)
            self.video_label.image = img
        self.root.after(50, self.update_video)

    # def save_measurement(self):
    #     weight = hx.get_weight_mean()
    #     timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    #     image_filename = f"{self.selected_vegetable}_{timestamp}.jpg"
    #     image_path = os.path.join(SAVE_IMAGE_PATH, image_filename)
    #     ret, frame = self.cap.read()
    #     if ret:
    #         cv2.imwrite(image_path, frame)
    #     else:
    #         messagebox.showerror("Error", "تصویر لینے میں ناکامی ہوئی۔")
    #         return
    #     data = {
    #         "vegetable": self.selected_vegetable,
    #         "weight": weight,
    #         "timestamp": timestamp.replace("_", " "),
    #         "image_path": image_path,
    #     }
    #     try:
    #         with open(DATA_FILE, "a") as f:
    #             json.dump(data, f)
    #             f.write("\n")
    #         messagebox.showinfo(
    #             "ڈیٹا محفوظ کر لیا گیا۔", f"Data saved at {DATA_FILE}\nImage saved at {image_path}"
    #         )
    #     except Exception as e:
    #         messagebox.showerror("Error", f"ڈیٹا محفوظ کرنے میں ناکامی: {str(e)}")
    #     self.show_main_menu()
    
    def save_measurement(self):
        weight = hx.get_weight_mean()
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        image_filename = f"{self.selected_vegetable}_{timestamp_str}.jpg"
        image_path = os.path.join(SAVE_IMAGE_PATH, image_filename)

        # Save image locally
        ret, frame = self.cap.read()
        if ret:
            cv2.imwrite(image_path, frame)
        else:
            messagebox.showerror("Error", "تصویر لینے میں ناکامی ہوئی۔")
            return

        # Save locally to JSON file
        data = {
            "vegetable": self.selected_vegetable,
            "weight": weight,
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "image_path": image_path,
        }

        try:
            with open(DATA_FILE, "a") as f:
                json.dump(data, f)
                f.write("\n")
        except Exception as e:
            messagebox.showerror("Error", f"ڈیٹا محفوظ کرنے میں ناکامی: {str(e)}")
            return

        # Upload to Firebase
        try:
            result = upload_vegetable_data(
                FIREBASE_FUNCTION_URL,
                image_path=image_path,
                weight=weight,
                veg_name=self.selected_vegetable,
                date_time=timestamp.isoformat()  # ensure string format here
            )

            # result = upload_vegetable_data(
            #     FIREBASE_FUNCTION_URL,
            #     image_path=image_path,
            #     weight=weight,
            #     veg_name=self.selected_vegetable,
            #     date_time=timestamp
            # )
            print("Firebase upload successful:", result)
            messagebox.showinfo("ڈیٹا", "ڈیٹا کامیابی سے اپلوڈ ہو گیا۔")
        except Exception as e:
            print("Firebase upload error:", e)
            messagebox.showwarning("اپلوڈ ناکام", f"Firebase پر اپلوڈ ناکام: {str(e)}")

        # Go back to main menu
        self.show_main_menu()


    def back_button(self):
        tk.Button(
            self.frame,
            text="Back",
            font=("Arial", 16),
            command=self.show_main_menu,
            bg="white",
        ).pack(pady=10)

    def clear_frame(self):
        for widget in self.frame.winfo_children():
            widget.destroy()

    def exit_app(self, event=None):
        self.cap.release

        GPIO.cleanup()
        self.root.destroy()

    def get_calibration(self):
        try:
            with open(CALIBRATION_FILE, "r") as f:
                data = json.load(f)
                ratio = data.get("ratio")
                if ratio:
                    print(f"کلیبریشن تناسب ملا  {ratio}")
                    return ratio
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = WeightCellApp(root)
    root.mainloop()
