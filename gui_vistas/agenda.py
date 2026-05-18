import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime

# Importación del controlador
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de las constantes de estilo
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_AZUL_HOVER, 
    C_TEXTO_OSCURO, C_BLANCO
)

class FrameAgenda(ctk.CTkFrame):
    """Módulo de Agenda de Citas y Proceso de Donación."""
    def __init__(self, master, sistema):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # =========================================================================
        # PANEL IZQUIERDO: AGENDA DE CITAS Y GESTIÓN
        # =========================================================================
        self.panel_visor_agenda = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.panel_visor_agenda.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        self.panel_visor_agenda.grid_rowconfigure(1, weight=1)
        self.panel_visor_agenda.grid_columnconfigure(0, weight=1)
        
        self.header_agenda = ctk.CTkFrame(self.panel_visor_agenda, fg_color="transparent")
        self.header_agenda.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(self.header_agenda, text="Agenda de Citas:", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).pack(side="left", padx=5)
        self.ent_fecha_visor = ctk.CTkEntry(self.header_agenda, placeholder_text="YYYY-MM-DD", width=120)
        self.ent_fecha_visor.pack(side="left", padx=5)
        self.ent_fecha_visor.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ctk.CTkButton(self.header_agenda, text="Buscar Citas", command=self.cargar_agenda, width=100, fg_color=C_AZUL, hover_color=C_AZUL_HOVER).pack(side="left", padx=10)
        
        cols = ("Folio", "Donante", "Hora", "Estado")
        self.t = ttk.Treeview(self.panel_visor_agenda, columns=cols, show="headings")
        for c in cols: 
            self.t.heading(c, text=c)
            self.t.column(c, anchor="center", width=120)
        self.t.column("Donante", anchor="w", width=200)
        
        scroll = ttk.Scrollbar(self.panel_visor_agenda, orient="vertical", command=self.t.yview)
        self.t.configure(yscrollcommand=scroll.set)
        self.t.grid(row=1, column=0, sticky="nsew", padx=(15, 0), pady=(0, 10))
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 15), pady=(0, 10))
        
        self.t.bind("<ButtonRelease-1>", self._on_tree_select)

        # --- SECCIÓN DE ACTUALIZAR CITA ---
        self.panel_gestion_cita = ctk.CTkFrame(self.panel_visor_agenda, fg_color="transparent")
        self.panel_gestion_cita.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 15))

        ctk.CTkLabel(self.panel_gestion_cita, text="Actualizar Cita Seleccionada:", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).pack(anchor="w")

        self.lbl_cita_sel = ctk.CTkLabel(self.panel_gestion_cita, text="Folio: Ninguna cita seleccionada", text_color=C_TEXTO_OSCURO)
        self.lbl_cita_sel.pack(anchor="w", pady=(5, 0))

        self.cb_estado = ctk.CTkComboBox(self.panel_gestion_cita, values=["Programada", "Completada", "Cancelada", "Ausente"])
        self.cb_estado.pack(side="left", pady=10, padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(self.panel_gestion_cita, text="Guardar Estado", command=self.actualizar_estado, fg_color=C_AZUL, hover_color=C_AZUL_HOVER).pack(side="left", pady=10)
        
        # =========================================================================
        # PANEL DERECHO: PROCESO DE DONACIÓN
        # =========================================================================
        self.panel_flujo = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.panel_flujo.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.panel_flujo.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.panel_flujo, text="Proceso de Donación", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=10)
        
        # --- PASO 1: EVALUACIÓN ---
        ctk.CTkLabel(self.panel_flujo, text="— 1. Evaluación Médica —", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=1, column=0, columnspan=2, pady=(5, 5), sticky="w", padx=15)
        
        ctk.CTkLabel(self.panel_flujo, text="ID del Donante:", text_color=C_TEXTO_OSCURO).grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.ent_ext_donante_id = ctk.CTkEntry(self.panel_flujo) 
        self.ent_ext_donante_id.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        
        self.btn_pretriaje = ctk.CTkButton(self.panel_flujo, text="📋 Iniciar Cuestionario Médico", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.abrir_ventana_pretriaje)
        self.btn_pretriaje.grid(row=3, column=0, columnspan=2, pady=(5, 15))

        # --- PASO 2: EXTRACCIÓN ---
        ctk.CTkLabel(self.panel_flujo, text="— 2. Extracción de Sangre —", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=4, column=0, columnspan=2, pady=(5, 5), sticky="w", padx=15)
        
        ctk.CTkLabel(self.panel_flujo, text="Responsable en turno:", text_color=C_TEXTO_OSCURO).grid(row=5, column=0, sticky="e", padx=10, pady=5)
        
        nombre_responsable = self.sistema.usuario_actual.nombre if self.sistema.usuario_actual else "No identificado"
        self.lbl_responsable = ctk.CTkLabel(self.panel_flujo, text=f"Dr./Lic. {nombre_responsable}", text_color=C_AZUL, font=ctk.CTkFont(weight="bold"))
        self.lbl_responsable.grid(row=5, column=1, sticky="w", padx=10, pady=5)

        ctk.CTkLabel(self.panel_flujo, text="Volumen recabado (ml):", text_color=C_TEXTO_OSCURO).grid(row=6, column=0, sticky="e", padx=10, pady=5)
        self.ent_ext_volumen = ctk.CTkEntry(self.panel_flujo)
        self.ent_ext_volumen.grid(row=6, column=1, sticky="ew", padx=10, pady=5)
        self.ent_ext_volumen.insert(0, "450")

        self.btn_donacion = ctk.CTkButton(self.panel_flujo, text="🩸 Registrar Extracción", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.ejecutar_extraccion)
        self.btn_donacion.grid(row=7, column=0, columnspan=2, pady=(5, 15))

        # --- PASO 3: RECUPERACIÓN ---
        ctk.CTkLabel(self.panel_flujo, text="— 3. Recuperación del Donante —", font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=8, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 5))
        
        ctk.CTkLabel(self.panel_flujo, text="Folio de Extracción:", text_color=C_TEXTO_OSCURO).grid(row=9, column=0, sticky="e", padx=10, pady=5)
        self.ent_est_folio = ctk.CTkEntry(self.panel_flujo)
        self.ent_est_folio.grid(row=9, column=1, sticky="ew", padx=10, pady=5)
        
        self.frame_check = ctk.CTkFrame(self.panel_flujo, fg_color="transparent")
        self.frame_check.grid(row=10, column=0, columnspan=2, padx=10, pady=5)
        self.var_mareo = ctk.BooleanVar(value=False)
        self.var_hematoma = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self.frame_check, text="Síncope / Mareo", variable=self.var_mareo, text_color=C_TEXTO_OSCURO).grid(row=0, column=0, padx=5)
        ctk.CTkCheckBox(self.frame_check, text="Hematoma en punción", variable=self.var_hematoma, text_color=C_TEXTO_OSCURO).grid(row=0, column=1, padx=5)

        self.btn_estabilidad = ctk.CTkButton(self.panel_flujo, text="Dar de Alta al Donante", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_estabilidad)
        self.btn_estabilidad.grid(row=11, column=0, columnspan=2, pady=10)

        self.cargar_agenda()

    def _on_tree_select(self, event):
        seleccion = self.t.selection()
        if seleccion:
            item_data = self.t.item(seleccion[0])
            folio = str(item_data['values'][0])
            estado_actual = str(item_data['values'][3])
            
            id_donante = self.sistema.obtener_id_donante_por_cita(folio)
            if id_donante:
                self.ent_ext_donante_id.delete(0, 'end')
                self.ent_ext_donante_id.insert(0, str(id_donante))

            self.lbl_cita_sel.configure(text=f"Folio: {folio}")
            self.cb_estado.set(estado_actual)

    def actualizar_estado(self):
        texto_folio = self.lbl_cita_sel.cget("text")
        if "Ninguna" in texto_folio:
            messagebox.showwarning("Atención", "Por favor, seleccione una cita de la lista.")
            return
            
        folio = texto_folio.replace("Folio: ", "").strip()
        nuevo_estado = self.cb_estado.get()
        
        exito, msj = self.sistema.actualizar_estado_cita(folio, nuevo_estado)
        if exito:
            messagebox.showinfo("Actualización", f"El estado de la cita cambió a {nuevo_estado}.")
            self.cargar_agenda()
        else:
            messagebox.showerror("Error", msj)

    def cargar_agenda(self):
        for i in self.t.get_children(): self.t.delete(i)
        for c in self.sistema.obtener_agenda_del_dia(self.ent_fecha_visor.get()):
            self.t.insert("", "end", values=(c["Folio"], c["Donante"], c["Hora"], c["Estado"]))

    def _sincronizar_cita_inteligente(self, id_donante, nuevo_estado):
        fecha_hoy = self.ent_fecha_visor.get().strip()
        self.sistema.sincronizar_cita_inteligente_controller(id_donante, fecha_hoy, nuevo_estado)
        self.cargar_agenda()

    def abrir_ventana_pretriaje(self):
        usuario = self.sistema.usuario_actual
        if not usuario or usuario.rol.strip().title() not in ["Médico", "Enfermero", "Administrador"]:
            messagebox.showerror("Sin permisos", "Solo el personal médico puede realizar esta evaluación.")
            return

        id_donante = self.ent_ext_donante_id.get().strip()
        if not id_donante:
            messagebox.showwarning("Dato Requerido", "Por favor, ingrese el ID del donante.")
            return

        ventana_modal = ctk.CTkToplevel(self)
        ventana_modal.title("Evaluación Médica")
        ventana_modal.geometry("520x550")
        ventana_modal.grab_set()
        ventana_modal.lift()
        ventana_modal.configure(fg_color=C_FONDO)

        ctk.CTkLabel(ventana_modal, text="Cuestionario Médico Inicial", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).pack(pady=15)

        frame_vitals = ctk.CTkFrame(ventana_modal, fg_color="transparent")
        frame_vitals.pack(pady=10, padx=20, fill="x")
        
        ent_sis = self._crear_campo_pack(frame_vitals, "Tensión Arterial Sistólica (mmHg):", "120")
        ent_dias = self._crear_campo_pack(frame_vitals, "Tensión Arterial Diastólica (mmHg):", "80")
        ent_frec = self._crear_campo_pack(frame_vitals, "Frecuencia Cardíaca (lpm):", "75")

        var_tatuaje = ctk.BooleanVar(); var_infeccion = ctk.BooleanVar()
        var_cirugia = ctk.BooleanVar(); var_embarazo = ctk.BooleanVar()

        ctk.CTkCheckBox(ventana_modal, text="¿Tatuaje o perforación reciente (últimos 12 meses)?", variable=var_tatuaje, text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=40, pady=4)
        ctk.CTkCheckBox(ventana_modal, text="¿Infección activa o uso de antibióticos?", variable=var_infeccion, text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=40, pady=4)
        ctk.CTkCheckBox(ventana_modal, text="¿Cirugía mayor reciente?", variable=var_cirugia, text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=40, pady=4)
        ctk.CTkCheckBox(ventana_modal, text="¿Embarazo o lactancia actual?", variable=var_embarazo, text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=40, pady=4)

        def procesar_dictamen_medico():
            signos = {'ta_sistolica': ent_sis.get(), 'ta_diastolica': ent_dias.get(), 'frec_cardiaca': ent_frec.get()}
            respuestas = {
                "tatuaje_ultimos_12_meses": "Sí" if var_tatuaje.get() else "No",
                "infeccion_reciente": "Sí" if var_infeccion.get() else "No",
                "cirugia_reciente": "Sí" if var_cirugia.get() else "No",
                "embarazo_lactancia": "Sí" if var_embarazo.get() else "No"
            }

            exito, mensaje = self.sistema.evaluar_pretriaje_donante(id_donante, respuestas, signos)
            
            if exito:
                messagebox.showinfo("Evaluación Aprobada", "El donante es apto. Puede continuar con la extracción.")
            else:
                self._sincronizar_cita_inteligente(id_donante, "Cancelada")
                messagebox.showerror("No Apto", f"{mensaje}\n\n[SISTEMA]: La cita ha sido cancelada por seguridad.")
                
            ventana_modal.destroy()

        ctk.CTkButton(ventana_modal, text="Guardar Evaluación", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=procesar_dictamen_medico).pack(pady=20)

    def _crear_campo_pack(self, parent, text, default):
        ctk.CTkLabel(parent, text=text, text_color=C_TEXTO_OSCURO).pack(anchor="w", padx=20)
        ent = ctk.CTkEntry(parent)
        ent.pack(fill="x", padx=20, pady=2)
        ent.insert(0, default)
        return ent

    def ejecutar_extraccion(self):
        usuario = self.sistema.usuario_actual
        if not usuario:
            messagebox.showerror("Sin sesión", "Debe iniciar sesión para realizar esta acción.")
            return

        try:
            id_don = self.ent_ext_donante_id.get().strip()
            vol = self.ent_ext_volumen.get().strip()

            exito, mensaje, folio_extraccion = self.sistema.procesar_donacion_exitosa_ui(id_don, vol)
            
            if exito:
                self.ent_est_folio.delete(0, 'end')
                self.ent_est_folio.insert(0, str(folio_extraccion))

                messagebox.showinfo("Registro Exitoso", f"{mensaje}\n\nEl folio ha sido enviado a la etapa de recuperación.")
            else:
                messagebox.showerror("Atención", mensaje)
        except Exception as e:
            messagebox.showerror("Error", f"Error de captura: {e}")
            
    def ejecutar_estabilidad(self):
        usuario = self.sistema.usuario_actual
        if not usuario or usuario.rol.strip().title() not in ["Médico", "Enfermero", "Administrador"]:
            messagebox.showerror("Sin permisos", "No tiene permisos para dar de alta a los donantes.")
            return

        try:
            folio_ext = self.ent_est_folio.get().strip()
            id_donante_actual = self.ent_ext_donante_id.get().strip() 
            
            if not folio_ext:
                messagebox.showerror("Atención", "Por favor, indique el folio de la extracción.")
                return

            complicaciones = []
            if self.var_mareo.get(): complicaciones.append("Síncope / Mareo")
            if self.var_hematoma.get(): complicaciones.append("Hematoma en punción")
            
            exito, msj = self.sistema.registrar_estabilidad_post_donacion(folio_ext, complicaciones)
            
            if exito:
                if id_donante_actual:
                    self._sincronizar_cita_inteligente(id_donante_actual, "Completada")

                messagebox.showinfo("Alta Exitosa", f"{msj}\n\n[SISTEMA]: El proceso de donación ha finalizado.")
                
                self.ent_est_folio.delete(0, 'end')
                self.ent_ext_donante_id.delete(0, 'end')
                self.var_mareo.set(False); self.var_hematoma.set(False)
            else:
                messagebox.showerror("Error", msj)
        except Exception as e:
            messagebox.showerror("Error", str(e))