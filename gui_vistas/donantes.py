import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime

# Importación del controlador
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de las constantes de estilo centralizadas
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_AZUL_HOVER, 
    C_TEXTO_OSCURO, C_BLANCO
)

class FrameDonantes(ctk.CTkFrame):
    """Módulo de Registro y Censo de Donantes."""
    def __init__(self, master, sistema):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # =========================================================================
        # PANEL SUPERIOR IZQUIERDO: REGISTRO DE DONANTE
        # =========================================================================
        self.panel_registro = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.panel_registro.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=(20, 10))
        self.panel_registro.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.panel_registro, text="Registrar Nuevo Donante", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=10)

        ctk.CTkLabel(self.panel_registro, text="— Datos Personales —", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=1, column=0, columnspan=2, pady=(5, 5), sticky="w", padx=15)
        
        self.ent_nombre = self._crear_campo(self.panel_registro, "Nombre Completo:", 2)
        
        self.ent_nacimiento = self._crear_campo(self.panel_registro, "F. Nacimiento (YYYY-MM-DD):", 3)
        self.ent_nacimiento.configure(placeholder_text="Ej. 1990-05-24")
        
        ctk.CTkLabel(self.panel_registro, text="Género:", text_color=C_TEXTO_OSCURO).grid(row=4, column=0, sticky="e", padx=10, pady=5)
        self.cb_genero = ctk.CTkComboBox(self.panel_registro, values=["MASCULINO", "FEMENINO"])
        self.cb_genero.grid(row=4, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.panel_registro, text="— Datos Médicos —", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=5, column=0, columnspan=2, pady=(15, 5), sticky="w", padx=15)
        
        ctk.CTkLabel(self.panel_registro, text="Grupo y RH:", text_color=C_TEXTO_OSCURO).grid(row=6, column=0, sticky="e", padx=10, pady=5)
        self.sub_frame_sangre = ctk.CTkFrame(self.panel_registro, fg_color="transparent")
        self.sub_frame_sangre.grid(row=6, column=1, sticky="ew", padx=10, pady=5)
        self.sub_frame_sangre.grid_columnconfigure((0,1), weight=1)
        self.cb_sangre = ctk.CTkComboBox(self.sub_frame_sangre, values=["A", "B", "AB", "O"])
        self.cb_sangre.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.cb_rh = ctk.CTkComboBox(self.sub_frame_sangre, values=["+", "-"])
        self.cb_rh.grid(row=0, column=1)

        ctk.CTkLabel(self.panel_registro, text="Tipo de Donación:", text_color=C_TEXTO_OSCURO).grid(row=7, column=0, sticky="e", padx=10, pady=5)
        self.cb_tipo_donante = ctk.CTkComboBox(self.panel_registro, values=["Altruista", "Familiar", "Reposición"])
        self.cb_tipo_donante.grid(row=7, column=1, sticky="ew", padx=10, pady=5)

        self.ent_peso = self._crear_campo(self.panel_registro, "Peso estimado (kg):", 8)
        self.ent_hemo = self._crear_campo(self.panel_registro, "Hemoglobina (g/dL):", 9)
        self.ent_contacto = self._crear_campo(self.panel_registro, "Teléfono de contacto:", 10)

        self.btn_registrar = ctk.CTkButton(self.panel_registro, text="Guardar Registro", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_registro)
        self.btn_registrar.grid(row=11, column=0, columnspan=2, pady=15)

        # =========================================================================
        # PANEL SUPERIOR DERECHO: AGENDAR CITA
        # =========================================================================
        self.panel_agendar = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.panel_agendar.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=(20, 10))
        self.panel_agendar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.panel_agendar, text="Agendar Cita", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).pack(pady=(15, 10), padx=15, anchor="w")
        
        ctk.CTkLabel(self.panel_agendar, text="ID del Donante:", text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=20, pady=(5, 0))
        self.ent_agendar_id = ctk.CTkEntry(self.panel_agendar)
        self.ent_agendar_id.pack(fill="x", padx=20, pady=(0, 5))

        ctk.CTkLabel(self.panel_agendar, text="Fecha de la cita (YYYY-MM-DD):", text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=20, pady=(5, 0))
        self.ent_agendar_fecha = ctk.CTkEntry(self.panel_agendar)
        self.ent_agendar_fecha.pack(fill="x", padx=20, pady=(0, 5))
        self.ent_agendar_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ctk.CTkButton(self.panel_agendar, text="🔍 Ver Horarios Disponibles", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.buscar_horarios).pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.panel_agendar, text="Horario Seleccionado:", text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=20)
        self.cb_horarios = ctk.CTkComboBox(self.panel_agendar, values=["Seleccione una fecha primero..."])
        self.cb_horarios.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkButton(self.panel_agendar, text="📅 Confirmar Cita", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.agendar_cita).pack(pady=(15, 30), padx=20, fill="x")

        # =========================================================================
        # PANEL INFERIOR: LISTA DE DONANTES
        # =========================================================================
        self.panel_tabla = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.panel_tabla.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=(10, 20))
        self.panel_tabla.grid_columnconfigure(0, weight=1)
        self.panel_tabla.grid_rowconfigure(1, weight=1)

        self.header_tabla = ctk.CTkFrame(self.panel_tabla, fg_color="transparent")
        self.header_tabla.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.header_tabla.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.header_tabla, text="Lista de Donantes", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(self.header_tabla, text="*Doble clic para ver ficha médica*", text_color=C_AZUL, font=ctk.CTkFont(size=12)).grid(row=0, column=1, sticky="w", padx=10)

        self.ent_buscar = ctk.CTkEntry(self.header_tabla, placeholder_text="🔍 Buscar por ID o Nombre...", width=250)
        self.ent_buscar.grid(row=0, column=2, sticky="e", padx=15)
        self.ent_buscar.bind("<KeyRelease>", lambda event: self.cargar_tabla())

        ctk.CTkButton(self.header_tabla, text="🔄 Actualizar", width=120, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.cargar_tabla).grid(row=0, column=3, sticky="e")

        columnas = ("ID", "Nombre", "Tipo", "Última Donación", "Elegible")
        self.tree = ttk.Treeview(self.panel_tabla, columns=columnas, show="headings")
        for col in columnas:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.column("Nombre", anchor="w", width=250)

        scroll = ttk.Scrollbar(self.panel_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))

        self.tree.bind("<ButtonRelease-1>", self._on_tree_select)
        self.tree.bind("<Double-1>", self.abrir_ficha_medica_modal)
        
        self.cargar_tabla()

    def _crear_campo(self, contenedor, etiqueta, fila):
        ctk.CTkLabel(contenedor, text=etiqueta, text_color=C_TEXTO_OSCURO).grid(row=fila, column=0, sticky="e", padx=10, pady=5)
        ent = ctk.CTkEntry(contenedor)
        ent.grid(row=fila, column=1, sticky="ew", padx=10, pady=5)
        return ent

    def _on_tree_select(self, event):
        seleccion = self.tree.selection()
        if seleccion:
            item_data = self.tree.item(seleccion[0])
            self.ent_agendar_id.delete(0, 'end')
            self.ent_agendar_id.insert(0, str(item_data['values'][0]))

    def abrir_ficha_medica_modal(self, event):
        seleccion = self.tree.selection()
        if not seleccion: return
        
        id_donante = self.tree.item(seleccion[0])['values'][0]
        donante = self.sistema.obtener_donante_especifico(id_donante)
        
        if not donante:
            messagebox.showerror("Error", "No se encontró la información detallada del donante.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title(f"Ficha Médica — ID: {donante.id_global}")
        modal.geometry("400x320")
        modal.grab_set(); modal.lift()
        modal.configure(fg_color=C_FONDO)

        ctk.CTkLabel(modal, text="Información del Donante", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).pack(pady=(15, 2))
        ctk.CTkLabel(modal, text=donante.nombre, font=ctk.CTkFont(size=18, weight="bold"), text_color=C_AZUL).pack(pady=(0, 15))
        
        f_dat = ctk.CTkFrame(modal, fg_color="transparent")
        f_dat.pack(fill="both", expand=True, padx=40)

        ctk.CTkLabel(f_dat, text="Peso:", font=ctk.CTkFont(size=13), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="e", padx=10, pady=4)
        ctk.CTkLabel(f_dat, text=f"{donante.peso_kg} kg", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=1, sticky="w", padx=10, pady=4)
        
        ctk.CTkLabel(f_dat, text="Hemoglobina:", font=ctk.CTkFont(size=13), text_color=C_TEXTO_OSCURO).grid(row=1, column=0, sticky="e", padx=10, pady=4)
        ctk.CTkLabel(f_dat, text=f"{donante.hemoglobina} g/dL", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=1, column=1, sticky="w", padx=10, pady=4)
        
        ctk.CTkLabel(f_dat, text="Grupo Sanguíneo:", font=ctk.CTkFont(size=13), text_color=C_TEXTO_OSCURO).grid(row=2, column=0, sticky="e", padx=10, pady=4)
        ctk.CTkLabel(f_dat, text=f"{donante.tipo_sangre}{donante.factor_rh}", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=2, column=1, sticky="w", padx=10, pady=4)
        
        ctk.CTkLabel(f_dat, text="Teléfono:", font=ctk.CTkFont(size=13), text_color=C_TEXTO_OSCURO).grid(row=3, column=0, sticky="e", padx=10, pady=4)
        ctk.CTkLabel(f_dat, text=f"{donante.contacto}", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=3, column=1, sticky="w", padx=10, pady=4)

        estado = "🟢 APTO" if donante.estado_elegibilidad else "🔴 NO APTO"
        color = C_AZUL if donante.estado_elegibilidad else C_ROJO
        ctk.CTkLabel(modal, text=estado, text_color=color, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

    def cargar_tabla(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        datos = self.sistema.obtener_lista_donantes()
        busqueda = self.ent_buscar.get().strip().lower() if hasattr(self, 'ent_buscar') else ""
        for d in datos:
            if busqueda and busqueda not in str(d["ID"]).lower() and busqueda not in str(d["Nombre"]).lower():
                continue
            self.tree.insert("", "end", values=(d["ID"], d["Nombre"], d["Tipo"], d["Última Donación"], d["Elegible"]))

    def ejecutar_registro(self):
        formulario = {
            'nombre': self.ent_nombre.get(),
            'fecha_nacimiento': self.ent_nacimiento.get(),
            'genero': self.cb_genero.get(),
            'tipo_sangre': self.cb_sangre.get(),
            'factor_rh': self.cb_rh.get(),
            'tipo_donante': self.cb_tipo_donante.get(),
            'peso_kg': self.ent_peso.get(),
            'hemoglobina': self.ent_hemo.get(),
            'contacto': self.ent_contacto.get()
        }
        
        exito, mensaje, id_generado = self.sistema.registrar_nuevo_donante_ui(formulario)
        
        if exito:
            self.cargar_tabla()
            messagebox.showinfo("Registro Exitoso", mensaje)
            
            self.ent_agendar_id.delete(0, 'end')
            self.ent_agendar_id.insert(0, str(id_generado))
            
            self.ent_nombre.delete(0, 'end')
            self.ent_nacimiento.delete(0, 'end')
            self.ent_peso.delete(0, 'end')
            self.ent_hemo.delete(0, 'end')
            self.ent_contacto.delete(0, 'end')
        else:
            messagebox.showerror("Error en el Registro", mensaje)

    def buscar_horarios(self):
        fecha = self.ent_agendar_fecha.get()
        exito, horarios = self.sistema.obtener_horarios_disponibles(fecha)
        if exito:
            if horarios:
                self.cb_horarios.configure(values=horarios)
                self.cb_horarios.set(horarios[0])
            else:
                self.cb_horarios.configure(values=["No hay horarios disponibles"])
                self.cb_horarios.set("No hay horarios disponibles")
                messagebox.showwarning("Horarios Llenos", "No hay lugares disponibles para la fecha seleccionada.")
        else:
            messagebox.showerror("Error", horarios)

    def agendar_cita(self):
        donante = self.ent_agendar_id.get().strip()
        fecha = self.ent_agendar_fecha.get().strip()
        hora = self.cb_horarios.get()
        
        exito, msj = self.sistema.agendar_cita_donante(donante, fecha, hora)
        if exito:
            messagebox.showinfo("Cita Confirmada", msj)
            self.ent_agendar_id.delete(0, 'end')
        else:
            messagebox.showerror("No se pudo agendar", msj)