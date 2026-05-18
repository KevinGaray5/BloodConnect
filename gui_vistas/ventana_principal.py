import os
from PIL import Image
import customtkinter as ctk
from tkinter import ttk

# Importación del controlador
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de las constantes de estilo
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_TEXTO_OSCURO, C_BLANCO
)

# Importación de nuestros módulos SRP (Vistas)
from gui_vistas.dashboard import FrameDashboard
from gui_vistas.donantes import FrameDonantes
from gui_vistas.agenda import FrameAgenda
from gui_vistas.almacen import FrameAlmacen
from gui_vistas.pacientes import FramePacientes
from gui_vistas.logistica import FrameLogistica
from gui_vistas.auditoria import FrameAuditoria

class VentanaPrincipal(ctk.CTk):
    """Ventana principal que controla los menús laterales y muestra las diferentes pantallas modulares."""
    def __init__(self, sistema_autenticado): 
        super().__init__()
        self.sistema = sistema_autenticado

        self.title("BloodConnect 2026 - Control Integral de Banco de Sangre")
        self.geometry("1400x850")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.set_appearance_mode("Light")
        self.configure(fg_color=C_FONDO)
        self.aplicar_estilo_treeview()

        # SIDEBAR CON LOGO
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=C_FONDO)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        try:
            # Ruta actualizada a la nueva carpeta assets
            ruta_logo = os.path.join("assets", "logo.png")
            imagen_pil = Image.open(ruta_logo)
            self.logo_sidebar = ctk.CTkImage(light_image=imagen_pil, dark_image=imagen_pil, size=(180, 80))
            self.lbl_logo_sidebar = ctk.CTkLabel(self.sidebar, image=self.logo_sidebar, text="")
            self.lbl_logo_sidebar.grid(row=0, column=0, pady=25, padx=20)
        except Exception as e:
            print(f"⚠️ No se pudo renderizar logo.png en sidebar: {e}")
            ctk.CTkLabel(self.sidebar, text="🩸 BloodConnect", font=ctk.CTkFont(size=22, weight="bold"), text_color=C_ROJO).grid(row=0, column=0, pady=25)

        self.btns = {}
        for i, (t, k) in enumerate([
            ("📊 Panel de Control", "dash"), ("🩸 Registro Donantes", "don"), ("🗓️ Agenda de Citas", "age"), 
            ("❄️ Laboratorio e Inventario", "alm"), ("🏥 Despacho a Pacientes", "pac"), ("🚚 Envíos y Solicitudes", "log"), ("🛡️ Seguridad y Accesos", "aud")
        ]):
            b = ctk.CTkButton(self.sidebar, text=t, fg_color="transparent", text_color=C_TEXTO_OSCURO, hover_color="#e0e0e0", anchor="w", command=lambda x=k: self.mostrar_seccion(x))
            b.grid(row=i+1, column=0, sticky="ew", padx=10, pady=2)
            self.btns[k] = b

        self.p_sesion = ctk.CTkFrame(self.sidebar, corner_radius=8, fg_color=C_BLANCO)
        self.p_sesion.grid(row=10, column=0, sticky="ew", padx=10, pady=30)
        
        usuario = self.sistema.usuario_actual
        ctk.CTkLabel(self.p_sesion, text=f"👤 Dr/Lic. {usuario.nombre}", font=ctk.CTkFont(weight="bold"), text_color=C_TEXTO_OSCURO).pack(pady=(10, 0))
        ctk.CTkLabel(self.p_sesion, text=f"{usuario.rol}", text_color="gray").pack(pady=(0, 10))
        
        ctk.CTkButton(self.p_sesion, text="Cerrar Sesión", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.logout).pack(pady=10, padx=10, fill="x")

        # Contenedor Frames
        self.contenedor = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor.grid(row=0, column=1, sticky="nsew")
        self.contenedor.grid_columnconfigure(0, weight=1)
        self.contenedor.grid_rowconfigure(0, weight=1)

        # Inyección de dependencias: Instanciamos los módulos importados
        self.marcos = {
            "dash": FrameDashboard(self.contenedor, self.sistema), 
            "don": FrameDonantes(self.contenedor, self.sistema),
            "age": FrameAgenda(self.contenedor, self.sistema), 
            "alm": FrameAlmacen(self.contenedor, self.sistema),
            "pac": FramePacientes(self.contenedor, self.sistema), 
            "log": FrameLogistica(self.contenedor, self.sistema),
            "aud": FrameAuditoria(self.contenedor, self.sistema)
        }
        for f in self.marcos.values(): 
            f.grid(row=0, column=0, sticky="nsew")
            
        self.mostrar_seccion("dash")

    def aplicar_estilo_treeview(self):
        style = ttk.Style(self)
        style.theme_use("default")
        
        bg, fg, field = C_BLANCO, C_TEXTO_OSCURO, C_BLANCO
        head_bg, head_fg = "#e1e1e1", C_TEXTO_OSCURO
            
        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=field, borderwidth=0)
        style.configure("Treeview.Heading", background=head_bg, foreground=head_fg, font=("Arial", 10, "bold"))
        style.map('Treeview', background=[('selected', C_AZUL)])

    def mostrar_seccion(self, k):
        for b in self.btns.values(): 
            b.configure(fg_color="transparent", text_color=C_TEXTO_OSCURO)
        self.btns[k].configure(fg_color=C_AZUL, text_color=C_BLANCO)
        self.marcos[k].tkraise()

    def logout(self):
        self.sistema.logout_sistema()
        self.withdraw() 
        self.after(200, self._transicion_segura_login)
        
    def _transicion_segura_login(self):
        # Limpiador de hilos de Tkinter para evitar errores 'check_dpi_scaling' en terminal
        for after_id in self.tk.eval('after info').split():
            self.after_cancel(after_id)
            
        self.destroy() 
        
        # Importación local para evitar dependencia circular
        from gui_vistas.login import VentanaLogin
        app_login = VentanaLogin()
        app_login.mainloop()