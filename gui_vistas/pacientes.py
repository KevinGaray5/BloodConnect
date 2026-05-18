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

class FramePacientes(ctk.CTkFrame):
    """Módulo hospitalario para registrar pacientes y asignarles sangre."""
    def __init__(self, master, sistema):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        self.tab_despacho = self.tabview.add("🏥 Despacho a Pacientes")
        self.tab_farmaco = self.tabview.add("⚠️ Seguimiento y Devoluciones")

        self._construir_tab_despacho()
        self._construir_tab_farmaco()

    # =========================================================================
    # PESTAÑA 1: DESPACHO A PACIENTES
    # =========================================================================
    def _construir_tab_despacho(self):
        self.tab_despacho.grid_columnconfigure(0, weight=1)
        self.tab_despacho.grid_columnconfigure(1, weight=1)
        self.tab_despacho.grid_rowconfigure(0, weight=0)
        self.tab_despacho.grid_rowconfigure(1, weight=0)
        self.tab_despacho.grid_rowconfigure(2, weight=1)

        # ---------------------------------------------------------------------
        # BOTÓN DE EMERGENCIA
        # ---------------------------------------------------------------------
        self.panel_panico_superior = ctk.CTkFrame(self.tab_despacho, fg_color="transparent")
        self.panel_panico_superior.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        self.panel_panico_superior.grid_columnconfigure(0, weight=1)

        self.btn_emergencia = ctk.CTkButton(
            self.panel_panico_superior, 
            text="🚨 Emergencia: Aministrar O- (Donante Universal)", 
            fg_color="#FF0000", 
            hover_color="#CC0000", 
            text_color=C_BLANCO, 
            font=ctk.CTkFont(weight="bold", size=16), 
            height=55, 
            command=self.ejecutar_transfusion_emergencia
        )
        self.btn_emergencia.grid(row=0, column=0, sticky="ew", padx=5)

        # ---------------------------------------------------------------------
        # ADMISIÓN Y ASIGNACIÓN
        # ---------------------------------------------------------------------
        # --- REGISTRAR PACIENTE ---
        self.panel_reg = ctk.CTkFrame(self.tab_despacho, fg_color=C_FONDO)
        self.panel_reg.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        self.panel_reg.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.panel_reg, text="Registrar Paciente", font=ctk.CTkFont(size=15, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=8)

        self.ent_p_expediente = self._crear_campo(self.panel_reg, "Número de Expediente:", 1)
        self.ent_p_nombre = self._crear_campo(self.panel_reg, "Nombre Completo:", 2)
        self.ent_p_nac = self._crear_campo(self.panel_reg, "F. Nacimiento (YYYY-MM-DD):", 3)
        self.ent_p_nac.configure(placeholder_text="Ej: 1985-12-30")
        
        ctk.CTkLabel(self.panel_reg, text="Grupo y RH:", text_color=C_TEXTO_OSCURO).grid(row=4, column=0, sticky="e", padx=10, pady=4)
        f_sangre = ctk.CTkFrame(self.panel_reg, fg_color="transparent")
        f_sangre.grid(row=4, column=1, sticky="ew", padx=10, pady=4)
        f_sangre.grid_columnconfigure((0,1), weight=1)
        
        self.cb_p_sangre = ctk.CTkComboBox(f_sangre, values=["A", "B", "AB", "O"])
        self.cb_p_sangre.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.cb_p_rh = ctk.CTkComboBox(f_sangre, values=["+", "-"])
        self.cb_p_rh.grid(row=0, column=1, sticky="ew")

        self.ent_p_diag = self._crear_campo(self.panel_reg, "Diagnóstico:", 5)
        
        ctk.CTkLabel(self.panel_reg, text="Prioridad:", text_color=C_TEXTO_OSCURO).grid(row=6, column=0, sticky="e", padx=10, pady=4)
        self.cb_p_prio = ctk.CTkComboBox(self.panel_reg, values=["Verde", "Amarillo", "Rojo"])
        self.cb_p_prio.grid(row=6, column=1, sticky="ew", padx=10, pady=4)
        
        self.btn_reg_p = ctk.CTkButton(self.panel_reg, text="Guardar Paciente", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_registro_paciente)
        self.btn_reg_p.grid(row=7, column=0, columnspan=2, pady=(10, 10))

        # --- ASIGNAR SANGRE ---
        self.panel_trans = ctk.CTkFrame(self.tab_despacho, fg_color=C_FONDO)
        self.panel_trans.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        self.panel_trans.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.panel_trans, text="Asignar Sangre a Paciente", font=ctk.CTkFont(size=15, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=8)
        
        self.ent_t_pac_id = self._crear_campo(self.panel_trans, "Expediente del Paciente:", 1)
        self.ent_t_pac_id.configure(placeholder_text="Seleccione un paciente de la lista")
        
        self.ent_t_unid = self._crear_campo(self.panel_trans, "Unidades a asignar:", 2)
        self.ent_t_unid.insert(0, "1")

        ctk.CTkLabel(self.panel_trans, text="Componente Requerido:", text_color=C_TEXTO_OSCURO).grid(row=3, column=0, sticky="e", padx=10, pady=4)
        self.f_t_req = ctk.CTkFrame(self.panel_trans, fg_color="transparent")
        self.f_t_req.grid(row=3, column=1, sticky="ew", padx=10, pady=4)
        self.f_t_req.grid_columnconfigure((0,1), weight=1)
        self.cb_t_sangre = ctk.CTkComboBox(self.f_t_req, values=["A", "B", "AB", "O"])
        self.cb_t_sangre.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.cb_t_rh = ctk.CTkComboBox(self.f_t_req, values=["+", "-"])
        self.cb_t_rh.grid(row=0, column=1, sticky="ew")
        
        self.cb_t_comp = ctk.CTkComboBox(self.panel_trans, values=["Globulos Rojos", "Plasma", "Plaquetas", "Crioprecipitados"])
        self.cb_t_comp.grid(row=4, column=1, padx=10, pady=4, sticky="ew")
        
        self.cb_t_triage = ctk.CTkComboBox(self.panel_trans, values=["VERDE", "AMARILLO"])
        self.cb_t_triage.grid(row=5, column=1, padx=10, pady=4, sticky="ew")

        self.btn_transfundir = ctk.CTkButton(self.panel_trans, text="Asignar Unidad", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_transfusion_rutina)
        self.btn_transfundir.grid(row=6, column=0, columnspan=2, pady=(38, 10))

        # ---------------------------------------------------------------------
        # TABLA DE PACIENTES
        # ---------------------------------------------------------------------
        self.panel_directorio = ctk.CTkFrame(self.tab_despacho, fg_color=C_FONDO)
        self.panel_directorio.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=(5, 10))
        self.panel_directorio.grid_columnconfigure(0, weight=1)
        self.panel_directorio.grid_rowconfigure(1, weight=1)

        header_dir = ctk.CTkFrame(self.panel_directorio, fg_color="transparent")
        header_dir.grid(row=0, column=0, sticky="ew", padx=10, pady=2)
        ctk.CTkLabel(header_dir, text="Lista de Pacientes Registrados", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).pack(side="left")
        
        ctk.CTkButton(header_dir, text="🔄 Actualizar", width=120, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.cargar_directorio).pack(side="right")
        ctk.CTkButton(header_dir, text="🖨️ Imprimir Historial", width=170, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.imprimir_resumen_paciente).pack(side="right", padx=10)
        ctk.CTkButton(header_dir, text="🛑 Dar de Alta", width=130, fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.dar_alta_hospitalaria).pack(side="right", padx=5)
        
        cols_dir = ("Expediente", "Nombre", "Tipo", "Área", "Prioridad")
        self.tree_dir = ttk.Treeview(self.panel_directorio, columns=cols_dir, show="headings")
        for c in cols_dir: 
            self.tree_dir.heading(c, text=c)
            self.tree_dir.column(c, anchor="center", width=110)
        self.tree_dir.column("Nombre", anchor="w", width=250)

        scroll_dir = ttk.Scrollbar(self.panel_directorio, orient="vertical", command=self.tree_dir.yview)
        self.tree_dir.configure(yscrollcommand=scroll_dir.set)
        self.tree_dir.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 5))
        scroll_dir.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 5))

        self.tree_dir.bind("<ButtonRelease-1>", self._on_tree_paciente_select)
        self.cargar_directorio()

    def imprimir_resumen_paciente(self):
        seleccion = self.tree_dir.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Por favor, seleccione un paciente de la lista para imprimir su historial.")
            return
            
        id_paciente = self.tree_dir.item(seleccion[0])['values'][0]
        resumen = self.sistema.obtener_resumen_paciente(id_paciente)
        
        if not resumen: 
            messagebox.showerror("Error", "No se encontró el historial del paciente.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Imprimir Historial del Paciente")
        modal.geometry("520x380")
        modal.grab_set(); modal.lift()
        modal.configure(fg_color=C_FONDO)

        ctk.CTkLabel(modal, text="Historial del Paciente", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).pack(pady=(10, 5))

        txt = ctk.CTkTextbox(modal, font=ctk.CTkFont(size=12), fg_color=C_BLANCO, text_color=C_TEXTO_OSCURO)
        txt.pack(fill="both", expand=True, padx=20, pady=(5, 15))
        txt.insert("1.0", resumen)
        txt.configure(state="disabled")

    # =========================================================================
    # PESTAÑA 2: SEGUIMIENTO Y DEVOLUCIONES
    # =========================================================================
    def _construir_tab_farmaco(self):
        self.tab_farmaco.grid_columnconfigure(0, weight=1)
        self.tab_farmaco.grid_columnconfigure(1, weight=1)
        self.tab_farmaco.grid_columnconfigure(2, weight=1)
        self.tab_farmaco.grid_rowconfigure(1, weight=1)

        # 1. Devolución Regular
        f_dev = ctk.CTkFrame(self.tab_farmaco, fg_color=C_FONDO)
        f_dev.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        f_dev.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(f_dev, text="Devolver Sangre No Utilizada", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self.ent_dev_id = self._crear_campo(f_dev, "ID de la Unidad:", 1)
        self.var_frio = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_dev, text="Cadena de Frío Intacta", variable=self.var_frio, text_color=C_TEXTO_OSCURO).grid(row=2, column=0, columnspan=2, pady=5)
        self.ent_dev_pwd = self._crear_campo(f_dev, "Contraseña Médico:", 3)
        self.ent_dev_pwd.configure(show="*")
        ctk.CTkButton(f_dev, text="Confirmar Devolución", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_devolucion).grid(row=4, column=0, columnspan=2, pady=10)

        # 2. Baja Retrospectiva (Emergencia)
        f_baja = ctk.CTkFrame(self.tab_farmaco, fg_color=C_FONDO)
        f_baja.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        f_baja.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(f_baja, text="Registrar Uso de Emergencia", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_ROJO).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self.ent_baja_ids = self._crear_campo(f_baja, "IDs (ej: 101,102):", 1)
        self.ent_baja_pwd = self._crear_campo(f_baja, "Contraseña Médico:", 2)
        self.ent_baja_pwd.configure(show="*")
        ctk.CTkLabel(f_baja, text="Usar solo si las bolsas físicas ya fueron\nutilizadas sin registrar el sistema.", font=ctk.CTkFont(size=11), text_color=C_TEXTO_OSCURO).grid(row=3, column=0, columnspan=2, pady=5)
        ctk.CTkButton(f_baja, text="Registrar Uso", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.ejecutar_baja_retrospectiva).grid(row=4, column=0, columnspan=2, pady=10)

        # 3. Farmacovigilancia
        f_reaccion = ctk.CTkFrame(self.tab_farmaco, fg_color=C_FONDO)
        f_reaccion.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        f_reaccion.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(f_reaccion, text="Registrar Reacción Adversa", text_color=C_ROJO, font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self.ent_rea_trans = self._crear_campo(f_reaccion, "Folio Transfusión:", 1)
        
        ctk.CTkLabel(f_reaccion, text="ID del Donante:", text_color=C_TEXTO_OSCURO).grid(row=2, column=0, sticky="e", padx=10, pady=2)
        self.ent_rea_donante = ctk.CTkEntry(f_reaccion, text_color=C_TEXTO_OSCURO, font=ctk.CTkFont(weight="bold"))
        self.ent_rea_donante.grid(row=2, column=1, sticky="ew", padx=10, pady=2)
        
        ctk.CTkLabel(f_reaccion, text="Notas Médicas:", text_color=C_TEXTO_OSCURO).grid(row=3, column=0, sticky="ne", padx=10, pady=2)
        self.txt_rea_notas = ctk.CTkTextbox(f_reaccion, height=40, fg_color=C_BLANCO, text_color=C_TEXTO_OSCURO)
        self.txt_rea_notas.grid(row=3, column=1, sticky="ew", padx=10, pady=2)
        
        ctk.CTkButton(f_reaccion, text="Registrar Alerta y Bloquear Donante", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.ejecutar_reaccion).grid(row=4, column=0, columnspan=2, pady=10)

        # --- TABLA INFERIOR ---
        self.panel_tabla_p = ctk.CTkFrame(self.tab_farmaco, fg_color=C_FONDO)
        self.panel_tabla_p.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=5, pady=(10, 10))
        self.panel_tabla_p.grid_columnconfigure(0, weight=1)
        self.panel_tabla_p.grid_rowconfigure(1, weight=1)
        
        header_hist = ctk.CTkFrame(self.panel_tabla_p, fg_color="transparent")
        header_hist.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(header_hist, text="Registro de Sangre Asignada", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).pack(side="left")

        columnas = ("Folio Transfusión", "Unidad Despachada", "Paciente Receptor", "Fecha y Hora", "Reacción Adversa")
        self.tree_p = ttk.Treeview(self.panel_tabla_p, columns=columnas, show="headings")
        for col in columnas: 
            self.tree_p.heading(col, text=col)
            self.tree_p.column(col, anchor="center", width=150)
        self.tree_p.column("Paciente Receptor", anchor="w", width=200)
        
        scroll = ttk.Scrollbar(self.panel_tabla_p, orient="vertical", command=self.tree_p.yview)
        self.tree_p.configure(yscrollcommand=scroll.set)
        self.tree_p.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scroll.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))

        self.tree_p.bind("<ButtonRelease-1>", self._on_tree_transfusion_select)
        self.cargar_tabla_transfusiones()

    # =========================================================================
    # HELPERS
    # =========================================================================
    def _crear_campo(self, c, e, f):
        ctk.CTkLabel(c, text=e, text_color=C_TEXTO_OSCURO).grid(row=f, column=0, sticky="e", padx=5, pady=2)
        ent = ctk.CTkEntry(c)
        ent.grid(row=f, column=1, sticky="ew", padx=5, pady=2)
        return ent

    def _on_tree_paciente_select(self, event):
        seleccion = self.tree_dir.selection()
        if seleccion:
            item_data = self.tree_dir.item(seleccion[0])['values']
            
            self.ent_t_pac_id.delete(0, 'end')
            self.ent_t_pac_id.insert(0, str(item_data[0]))
            
            tipo_str = str(item_data[2])
            if tipo_str.endswith('+') or tipo_str.endswith('-'):
                sangre = tipo_str[:-1]
                rh = tipo_str[-1]
            else:
                sangre = tipo_str
                rh = ""
            
            self.cb_t_sangre.set(sangre)
            self.cb_t_rh.set(rh)
            
            prioridad = str(item_data[4]).strip().upper()
            if "ROJO" in prioridad: 
                self.cb_t_triage.set("ROJO")
            elif "AMARILLO" in prioridad: 
                self.cb_t_triage.set("AMARILLO")
            else: 
                self.cb_t_triage.set("VERDE")
            
            self.ent_t_unid.delete(0, 'end')
            self.ent_t_unid.insert(0, "1")

    def _on_tree_transfusion_select(self, event):
        seleccion = self.tree_p.selection()
        if seleccion:
            item_data = self.tree_p.item(seleccion[0])
            self.ent_rea_trans.delete(0, 'end')
            self.ent_rea_trans.insert(0, str(item_data['values'][0]))
            
            id_donante_origen = self.sistema.obtener_donante_origen_por_unidad(str(item_data['values'][1]))
            self.ent_rea_donante.delete(0, 'end')
            self.ent_rea_donante.insert(0, id_donante_origen if id_donante_origen else "No encontrado")

    # =========================================================================
    # CONTROLADORES DE EVENTOS
    # =========================================================================
    def cargar_directorio(self):
        for item in self.tree_dir.get_children(): self.tree_dir.delete(item)
        for p in self.sistema.obtener_lista_pacientes():
            self.tree_dir.insert("", "end", values=(p["Expediente"], p["Nombre"], p["Tipo"], p["Área"], p["Prioridad"]))

    def cargar_tabla_transfusiones(self):
        for item in self.tree_p.get_children(): self.tree_p.delete(item)
        for h in self.sistema.obtener_historial_transfusiones_tabla():
            self.tree_p.insert("", "end", values=list(h.values()))

    def ejecutar_registro_paciente(self):
        try:
            id_global_auto = int(datetime.now().strftime("%y%m%d%H%M%S"))
            datos = {
                'id_global': id_global_auto,
                'id_paciente': self.ent_p_expediente.get(),
                'nombre': self.ent_p_nombre.get(), 
                'fecha_nacimiento': self.ent_p_nac.get(),
                'genero': "NO ESPECIFICADO", 
                'tipo_sangre': self.cb_p_sangre.get(), 
                'factor_rh': self.cb_p_rh.get(),
                'area_internamiento': "General", 
                'diagnostico_ingreso': self.ent_p_diag.get(), 
                'prioridad_clinica': self.cb_p_prio.get()
            }
            exito, msj = self.sistema.registrar_nuevo_paciente(datos)
            if exito:
                messagebox.showinfo("Paciente Registrado", msj)
                self.cargar_directorio() 
                self.ent_p_expediente.delete(0, 'end'); self.ent_p_nombre.delete(0, 'end')
                self.ent_p_nac.delete(0, 'end'); self.ent_p_diag.delete(0, 'end')
            else:
                messagebox.showerror("Error", msj)
        except Exception as e: messagebox.showerror("Error", str(e))

    def ejecutar_transfusion_emergencia(self):
        paciente_id = self.ent_t_pac_id.get().strip()
        unidades_str = self.ent_t_unid.get().strip() or "1"
        
        exito, codigo, msj = self.sistema.procesar_emergencia_primaria(paciente_id, int(unidades_str))
        
        if exito:
            messagebox.showwarning("Emergencia Atendida", msj)
            self.cargar_tabla_transfusiones()
            self.ent_t_pac_id.delete(0, 'end')
        else:
            if codigo == "REQUIERE_FALLBACK":
                self.abrir_modal_fallback(paciente_id, unidades_str, msj)
            else:
                messagebox.showerror("Fallo en Emergencia", msj)

    def abrir_modal_fallback(self, paciente_id, unidades_str, alerta_previa):
        modal = ctk.CTkToplevel(self)
        modal.title("Emergencia - Sangre O- Agotada")
        modal.geometry("450x350")
        modal.grab_set(); modal.lift()
        modal.configure(fg_color=C_FONDO)
        
        ctk.CTkLabel(modal, text="¡No hay Sangre O- Disponible!", text_color=C_ROJO, font=ctk.CTkFont(size=22, weight="bold")).pack(pady=10)
        ctk.CTkLabel(modal, text=alerta_previa, text_color=C_ROJO).pack(pady=5)
        ctk.CTkLabel(modal, text="Por favor ingrese el grupo sanguíneo exacto del paciente:", text_color=C_TEXTO_OSCURO).pack(pady=10)
        
        f = ctk.CTkFrame(modal, fg_color="transparent")
        f.pack(pady=10)
        cb_sangre = ctk.CTkComboBox(f, values=["A", "B", "AB", "O"]); cb_sangre.grid(row=0, column=0, padx=5)
        cb_rh = ctk.CTkComboBox(f, values=["+", "-"]); cb_rh.grid(row=0, column=1, padx=5)
        
        def procesar_fallback():
            res, code, m2 = self.sistema.procesar_emergencia_fallback(paciente_id, cb_sangre.get(), cb_rh.get(), int(unidades_str))
            if res:
                messagebox.showwarning("Unidad Asignada", m2)
                self.cargar_tabla_transfusiones()
                self.ent_t_pac_id.delete(0, 'end')
                modal.destroy()
            else:
                messagebox.showerror("Sin unidades disponibles", m2)
                
        ctk.CTkButton(modal, text="Buscar Unidad Compatible", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, height=40, command=procesar_fallback).pack(pady=20)

    def ejecutar_transfusion_rutina(self):
        try:
            res, msj = self.sistema.procesar_transfusion_rutina(
                id_paciente=self.ent_t_pac_id.get(),
                tipo_req=self.cb_t_sangre.get(), factor_req=self.cb_t_rh.get(),
                unidades=int(self.ent_t_unid.get()),
                tipo_comp=self.cb_t_comp.get(),
                prioridad=self.cb_t_triage.get()
            )
            if res:
                messagebox.showinfo("Asignación Exitosa", msj)
                self.ent_t_pac_id.delete(0, 'end')
            else:
                messagebox.showerror("No se pudo asignar", msj)
            self.cargar_tabla_transfusiones()
        except Exception as e: 
            messagebox.showerror("Error", str(e))

    def ejecutar_baja_retrospectiva(self):
        res, msj = self.sistema.procesar_baja_retrospectiva(self.ent_baja_ids.get(), self.ent_baja_pwd.get())
        if res:
            messagebox.showinfo("Uso Registrado", msj)
            self.ent_baja_ids.delete(0, 'end'); self.ent_baja_pwd.delete(0, 'end')
            self.cargar_tabla_transfusiones()
        else: 
            messagebox.showerror("Error", msj)

    def ejecutar_devolucion(self):
        res, msj = self.sistema.procesar_devolucion_quirofano(self.ent_dev_id.get(), self.var_frio.get(), self.ent_dev_pwd.get())
        if res:
            messagebox.showinfo("Devolución Exitosa", msj)
            self.ent_dev_id.delete(0, 'end'); self.ent_dev_pwd.delete(0, 'end')
        else: 
            messagebox.showerror("Error", msj)

    def ejecutar_reaccion(self):
        res, msj = self.sistema.registrar_reaccion_adversa_transfusion(self.ent_rea_trans.get(), self.ent_rea_donante.get(), self.txt_rea_notas.get("1.0", "end-1c"))
        if res:
            messagebox.showwarning("Alerta Registrada", msj)
            self.cargar_tabla_transfusiones()
            self.ent_rea_trans.delete(0, 'end'); self.ent_rea_donante.delete(0, 'end'); self.txt_rea_notas.delete("1.0", "end")
        else: 
            messagebox.showerror("Error", msj)

    def dar_alta_hospitalaria(self):
        seleccion = self.tree_dir.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione un paciente de la lista para darlo de alta.")
            return
            
        valores = self.tree_dir.item(seleccion[0])['values']
        id_paciente = valores[0]
        nombre_paciente = valores[1]
        
        confirmar = messagebox.askyesno(
            "Confirmar Alta", 
            f"¿Desea dar de alta al paciente {nombre_paciente} (Expediente: {id_paciente})?\n\nEl paciente saldrá de la lista, pero su historial de transfusiones se conservará."
        )
        
        if confirmar:
            exito, msj = self.sistema.dar_alta_paciente(id_paciente, "Alta Médica")
            if exito:
                messagebox.showinfo("Alta Exitosa", msj)
                self.cargar_directorio()
                self.ent_t_pac_id.delete(0, 'end')
            else:
                messagebox.showerror("Error", msj)