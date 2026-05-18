import os
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image

# Importación del controlador orquestador (Facade)
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de las constantes de estilo centralizadas
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_AZUL_HOVER, 
    C_TEXTO_OSCURO, C_BLANCO
)

class VentanaLogin(ctk.CTk):
    """Pantalla inicial para ingresar al sistema o crear un nuevo usuario."""
    def __init__(self):
        super().__init__()
        self.sistema = SistemaBloodConnect()
        self.title("BloodConnect 2026 - Autenticación")
        self.geometry("500x600")
        self.eval('tk::PlaceWindow . center')
        
        ctk.set_appearance_mode("Light")
        self.configure(fg_color=C_FONDO)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        frame_principal = ctk.CTkFrame(self, fg_color=C_FONDO)
        frame_principal.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")
        
        try:
            # Ruta actualizada a la nueva carpeta assets
            ruta_logo = os.path.join("assets", "logo.png")
            imagen_pil = Image.open(ruta_logo)
            self.logo_img = ctk.CTkImage(light_image=imagen_pil, dark_image=imagen_pil, size=(450, 200))
            
            self.lbl_logo = ctk.CTkLabel(frame_principal, image=self.logo_img, text="")
            self.lbl_logo.pack(pady=(10, 25))
            
        except Exception as e:
            print(f"⚠️ Alerta: No se pudo renderizar logo.png: {e}")
            ctk.CTkLabel(frame_principal, text="🩸 BloodConnect", font=ctk.CTkFont(size=32, weight="bold"), text_color=C_ROJO).pack(pady=(40, 30))

        self.ent_id = ctk.CTkEntry(
            frame_principal, 
            placeholder_text="Matrícula Institucional", 
            width=280, 
            height=40,
            border_color=C_ROJO,
            border_width=2,
            text_color=C_TEXTO_OSCURO
        )
        self.ent_id.pack(pady=10)
        
        self.ent_pwd = ctk.CTkEntry(
            frame_principal, 
            placeholder_text="Contraseña", 
            show="*", 
            width=280, 
            height=40,
            border_color=C_ROJO,
            border_width=2,
            text_color=C_TEXTO_OSCURO
        )
        self.ent_pwd.pack(pady=10)
        
        self.btn_autorizar = ctk.CTkButton(
            frame_principal, 
            text="Iniciar Sesión", 
            width=280, 
            height=45, 
            fg_color=C_ROJO,
            hover_color=C_ROJO_HOVER,
            text_color=C_BLANCO,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.btn_autorizar.configure(command=self.iniciar_sesion)
        self.btn_autorizar.pack(pady=25)
        
        self.btn_apertura = ctk.CTkButton(
            frame_principal, 
            text="Registrar Nuevo Usuario", 
            fg_color=C_AZUL,        
            hover_color=C_AZUL_HOVER,     
            text_color=C_BLANCO,        
            width=280, 
            height=42, 
            command=self.abrir_registro,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_apertura.pack(pady=10)

    def iniciar_sesion(self):
        exito, msj = self.sistema.login_sistema(self.ent_id.get(), self.ent_pwd.get())
        if exito:
            self.withdraw() 
            self.after(200, self._transicion_segura_dashboard)
        else:
            messagebox.showerror("Error al ingresar", "Sus credenciales son incorrectas.")

    def _transicion_segura_dashboard(self):
        self.destroy()
        # Importación local para evitar dependencias circulares con el orquestador
        from gui_vistas.ventana_principal import VentanaPrincipal
        app = VentanaPrincipal(self.sistema) 
        app.mainloop()

    def abrir_registro(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Registro de Personal")
        modal.geometry("450x550")
        modal.grab_set()
        modal.lift()
        modal.configure(fg_color=C_FONDO)
        
        ctk.CTkLabel(modal, text="Crear Cuenta de Usuario", font=ctk.CTkFont(size=20, weight="bold"), text_color=C_TEXTO_OSCURO).pack(pady=15)
        
        f = ctk.CTkFrame(modal, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=20)
        
        e_nom = self._c(f, "Nombre Completo:", 0)
        e_nac = self._c(f, "F. Nacimiento (YYYY-MM-DD):", 1)
        
        ctk.CTkLabel(f, text="Género:", text_color=C_TEXTO_OSCURO).grid(row=2, column=0, sticky="e", padx=5, pady=5)
        cb_gen = ctk.CTkComboBox(f, values=["MASCULINO", "FEMENINO"])
        cb_gen.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        ctk.CTkLabel(f, text="Cargo:", text_color=C_TEXTO_OSCURO).grid(row=3, column=0, sticky="e", padx=5, pady=5)
        cb_rol = ctk.CTkComboBox(f, values=["Enfermero", "Laboratorista", "Médico", "Administrador"])
        cb_rol.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        e_ced = self._c(f, "Cédula Profesional:", 4)
        
        e_pwd = self._c(f, "Crear Contraseña:", 5)
        e_pwd.configure(show="*")
        
        def guardar():
            datos = {
                'nombre': e_nom.get(), 
                'fecha_nacimiento': e_nac.get(),
                'genero': cb_gen.get(), 
                'cedula_profesional': e_ced.get(), 
                'rol': cb_rol.get(),
                'password_plana': e_pwd.get()
            }
            
            exito, msj, id_generado = self.sistema.registrar_nuevo_trabajador(datos)
            
            if exito:
                mensaje_final = f"Usuario registrado exitosamente.\n\nIMPORTANTE:\nSu MATRÍCULA asignada es: {id_generado}\nPor favor, guárdela. La necesitará para Iniciar Sesión."
                messagebox.showinfo("Registro Exitoso", mensaje_final)
                modal.destroy()
            else:
                messagebox.showerror("Error", msj)
                
        ctk.CTkButton(modal, text="Guardar y Crear Cuenta", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=guardar).pack(pady=20)
        
    def _c(self, p, t, r):
        ctk.CTkLabel(p, text=t, text_color=C_TEXTO_OSCURO).grid(row=r, column=0, sticky="e", padx=5, pady=5)
        e = ctk.CTkEntry(p, width=200, text_color=C_TEXTO_OSCURO)
        e.grid(row=r, column=1, sticky="w", padx=5, pady=5)
        return e