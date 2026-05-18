import customtkinter as ctk
from tkinter import ttk, messagebox

# Importación del controlador
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de las constantes de estilo
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_AZUL_HOVER, 
    C_TEXTO_OSCURO, C_BLANCO
)

class FrameAlmacen(ctk.CTkFrame):
    """Módulo de Control de Inventario y Laboratorio."""
    def __init__(self, master, sistema):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        self.tab_lab = self.tabview.add("🧪 Laboratorio")
        self.tab_inv = self.tabview.add("❄️ Inventario")
        self.tab_ext = self.tabview.add("🩸 Historial")

        self._construir_tab_laboratorio()
        self._construir_tab_inventario()
        self._construir_tab_extracciones()

    # =========================================================================
    # PESTAÑA 1: LABORATORIO Y COMPONENTES
    # =========================================================================
    def _construir_tab_laboratorio(self):
        self.tab_lab.grid_columnconfigure(0, weight=1)
        self.tab_lab.grid_rowconfigure(0, weight=1)

        self.panel_cuarentena = ctk.CTkFrame(self.tab_lab, fg_color="transparent")
        self.panel_cuarentena.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.panel_cuarentena.grid_columnconfigure(0, weight=1)
        self.panel_cuarentena.grid_rowconfigure(1, weight=1)

        self.header_cuarentena = ctk.CTkFrame(self.panel_cuarentena, fg_color="transparent")
        self.header_cuarentena.grid(row=0, column=0, sticky="ew", pady=5)
        ctk.CTkLabel(self.header_cuarentena, text="Sangre en Cuarentena (Pendiente de Análisis)", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w")
        
        ctk.CTkButton(self.header_cuarentena, text="🔄 Actualizar", width=100, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.cargar_cuarentena).grid(row=0, column=1, sticky="e", padx=(20, 0))

        columnas = ("ID Unidad (Folio)", "Componente", "Tipo", "Refrigerador Asignado")
        self.tree_cuarentena = ttk.Treeview(self.panel_cuarentena, columns=columnas, show="headings")
        for col in columnas:
            self.tree_cuarentena.heading(col, text=col)
            self.tree_cuarentena.column(col, anchor="center", width=150)
        
        scroll_c = ttk.Scrollbar(self.panel_cuarentena, orient="vertical", command=self.tree_cuarentena.yview)
        self.tree_cuarentena.configure(yscrollcommand=scroll_c.set)
        self.tree_cuarentena.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        scroll_c.grid(row=1, column=1, sticky="ns", pady=(0, 10))

        self.tree_cuarentena.bind("<ButtonRelease-1>", self._on_tree_cuarentena_select)

        self.panel_acciones = ctk.CTkFrame(self.tab_lab, fg_color=C_FONDO)
        self.panel_acciones.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.panel_acciones.grid_columnconfigure((0, 1), weight=1)

        # Serología
        self.panel_serologia = ctk.CTkFrame(self.panel_acciones, fg_color="transparent")
        self.panel_serologia.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.panel_serologia.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(self.panel_serologia, text="Resultados de Laboratorio", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ctk.CTkLabel(self.panel_serologia, text="ID de la Unidad:", text_color=C_TEXTO_OSCURO).grid(row=1, column=0, sticky="e", padx=5)
        self.ent_sero_id = ctk.CTkEntry(self.panel_serologia, width=120)
        self.ent_sero_id.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=5)

        self.vars = {k: ctk.BooleanVar(value=False) for k in ['vih', 'hepatitis_b', 'hepatitis_c', 'sifilis', 'chagas']}
        ctk.CTkCheckBox(self.panel_serologia, text="Reactivo VIH", variable=self.vars['vih'], text_color=C_TEXTO_OSCURO).grid(row=3, column=0, padx=5, pady=2, sticky="w")
        ctk.CTkCheckBox(self.panel_serologia, text="Reactivo Hep B", variable=self.vars['hepatitis_b'], text_color=C_TEXTO_OSCURO).grid(row=3, column=1, padx=5, pady=2, sticky="w")
        ctk.CTkCheckBox(self.panel_serologia, text="Reactivo Hep C", variable=self.vars['hepatitis_c'], text_color=C_TEXTO_OSCURO).grid(row=3, column=2, padx=5, pady=2, sticky="w")
        ctk.CTkCheckBox(self.panel_serologia, text="Reactivo Sífilis", variable=self.vars['sifilis'], text_color=C_TEXTO_OSCURO).grid(row=4, column=0, padx=5, pady=2, sticky="w")
        ctk.CTkCheckBox(self.panel_serologia, text="Reactivo Chagas", variable=self.vars['chagas'], text_color=C_TEXTO_OSCURO).grid(row=4, column=1, padx=5, pady=2, sticky="w")

        self.ent_sero_pass = ctk.CTkEntry(self.panel_serologia, show="*", width=180, placeholder_text="Contraseña")
        self.ent_sero_pass.grid(row=5, column=1, columnspan=2, sticky="w", padx=5, pady=10)

        self.btn_liberar = ctk.CTkButton(self.panel_serologia, text="Aprobar Unidad", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_liberacion)
        self.btn_liberar.grid(row=6, column=0, columnspan=3, pady=10)

        # Fraccionamiento
        self.panel_fraccionar = ctk.CTkFrame(self.panel_acciones, fg_color="transparent")
        self.panel_fraccionar.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.panel_fraccionar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.panel_fraccionar, text="Separación de Componentes", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.ent_frac_id = ctk.CTkEntry(self.panel_fraccionar, width=200, placeholder_text="ID de la Bolsa Madre / Plasma")
        self.ent_frac_id.grid(row=1, column=0, pady=10, sticky="w")

        self.btn_frac = ctk.CTkButton(self.panel_fraccionar, text="Separar Componentes", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_fraccionamiento)
        self.btn_frac.grid(row=2, column=0, pady=5, sticky="ew")
        
        self.btn_crio = ctk.CTkButton(self.panel_fraccionar, text="Extraer Plasma", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.ejecutar_extraccion_crio)
        self.btn_crio.grid(row=3, column=0, pady=5, sticky="ew")

        self.cargar_cuarentena()

    # =========================================================================
    # PESTAÑA 2: INVENTARIO GENERAL
    # =========================================================================
    def _construir_tab_inventario(self):
        self.tab_inv.grid_columnconfigure(0, weight=1)
        self.tab_inv.grid_rowconfigure(2, weight=1)

        # 1. Cabecera
        header_inv = ctk.CTkFrame(self.tab_inv, fg_color="transparent")
        header_inv.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(header_inv, text="Inventario de Unidades Físicas", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).pack(side="left")
        ctk.CTkButton(header_inv, text="🔄 Actualizar", width=100, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.cargar_inventario).pack(side="right")

        # 2. PANEL DE FILTROS
        self.panel_filtros = ctk.CTkFrame(self.tab_inv, fg_color=C_FONDO, corner_radius=8)
        self.panel_filtros.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipadx=10, ipady=10)
        
        for i in range(5):
            self.panel_filtros.grid_columnconfigure(i, weight=1)

        # Filtros
        ctk.CTkLabel(self.panel_filtros, text="Componente:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w", padx=10, pady=(5,0))
        self.cb_f_comp = ctk.CTkComboBox(self.panel_filtros, values=["Todos", "Sangre Entera", "Globulos Rojos", "Plasma", "Plaquetas", "Crioprecipitados"], command=lambda _: self.cargar_inventario())
        self.cb_f_comp.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,5))

        ctk.CTkLabel(self.panel_filtros, text="Grupo y RH:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=1, sticky="w", padx=10, pady=(5,0))
        self.cb_f_grupo = ctk.CTkComboBox(self.panel_filtros, values=["Todos", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], command=lambda _: self.cargar_inventario())
        self.cb_f_grupo.grid(row=1, column=1, sticky="ew", padx=10, pady=(0,5))

        ctk.CTkLabel(self.panel_filtros, text="Estado:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=2, sticky="w", padx=10, pady=(5,0))
        self.cb_f_estado = ctk.CTkComboBox(self.panel_filtros, values=["Todos", "Liberada", "En Cuarentena", "Desechada", "Fraccionada", "Transfundida"], command=lambda _: self.cargar_inventario())
        self.cb_f_estado.grid(row=1, column=2, sticky="ew", padx=10, pady=(0,5))

        ctk.CTkLabel(self.panel_filtros, text="Buscar Ubicación:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=3, sticky="w", padx=10, pady=(5,0))
        self.ent_f_ubi = ctk.CTkEntry(self.panel_filtros, placeholder_text="Ej: Congelador-A")
        self.ent_f_ubi.grid(row=1, column=3, sticky="ew", padx=10, pady=(0,5))
        self.ent_f_ubi.bind("<KeyRelease>", lambda _: self.cargar_inventario()) 

        ctk.CTkLabel(self.panel_filtros, text="Ordenar por:", font=ctk.CTkFont(size=12, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=4, sticky="w", padx=10, pady=(5,0))
        self.cb_f_orden = ctk.CTkComboBox(self.panel_filtros, values=["Ubicación", "Caducidad", "Grupo Sanguíneo", "Estado"], command=lambda _: self.cargar_inventario())
        self.cb_f_orden.grid(row=1, column=4, sticky="ew", padx=10, pady=(0,5))

        self.cb_f_comp.set("Todos")
        self.cb_f_grupo.set("Todos")
        self.cb_f_estado.set("Todos")
        self.cb_f_orden.set("Ubicación")

        # 3. Tabla Principal
        columnas = ("ID Unidad (Folio)", "Componente", "Grupo", "Caducidad", "Estado", "Ubicación")
        self.tree_inv = ttk.Treeview(self.tab_inv, columns=columnas, show="headings")
        for col in columnas:
            self.tree_inv.heading(col, text=col)
            self.tree_inv.column(col, anchor="center", width=120)
        
        scroll_i = ttk.Scrollbar(self.tab_inv, orient="vertical", command=self.tree_inv.yview)
        self.tree_inv.configure(yscrollcommand=scroll_i.set)
        self.tree_inv.grid(row=2, column=0, sticky="nsew", pady=(0, 0))
        scroll_i.grid(row=2, column=1, sticky="ns", pady=(0, 0))

        self.cargar_inventario()

    # =========================================================================
    # PESTAÑA 3: HISTORIAL
    # =========================================================================
    def _construir_tab_extracciones(self):
        self.tab_ext.grid_columnconfigure(0, weight=1)
        self.tab_ext.grid_rowconfigure(1, weight=1)

        header_ext = ctk.CTkFrame(self.tab_ext, fg_color="transparent")
        header_ext.grid(row=0, column=0, sticky="ew", pady=5)
        ctk.CTkLabel(header_ext, text="Historial de Extracciones de Sangre", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).pack(side="left")
        ctk.CTkButton(header_ext, text="🔄 Actualizar Historial", width=120, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.cargar_extracciones).pack(side="right")

        columnas = ("ID Unidad (Folio)", "Donante", "Volumen (ml)", "Fecha y Hora", "Observaciones")
        self.tree_ext = ttk.Treeview(self.tab_ext, columns=columnas, show="headings")
        for col in columnas:
            self.tree_ext.heading(col, text=col)
            self.tree_ext.column(col, anchor="center", width=120)
        self.tree_ext.column("Donante", width=200, anchor="w")
        self.tree_ext.column("Observaciones", width=250, anchor="w")
        
        scroll_e = ttk.Scrollbar(self.tab_ext, orient="vertical", command=self.tree_ext.yview)
        self.tree_ext.configure(yscrollcommand=scroll_e.set)
        self.tree_ext.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        scroll_e.grid(row=1, column=1, sticky="ns", pady=(10, 0))

        self.cargar_extracciones()

    # =========================================================================
    # EVENTOS Y DATA-BINDING
    # =========================================================================
    def _on_tree_cuarentena_select(self, event):
        seleccion = self.tree_cuarentena.selection()
        if seleccion:
            item_data = self.tree_cuarentena.item(seleccion[0])
            id_bolsa = str(item_data['values'][0])
            
            self.ent_sero_id.delete(0, 'end')
            self.ent_sero_id.insert(0, id_bolsa)
            
            self.ent_frac_id.delete(0, 'end')
            self.ent_frac_id.insert(0, id_bolsa)

    def cargar_cuarentena(self):
        for item in self.tree_cuarentena.get_children():
            self.tree_cuarentena.delete(item)
        unidades = self.sistema.obtener_unidades_cuarentena()
        for u in unidades:
            self.tree_cuarentena.insert("", "end", values=(u["ID Unidad"], u["Componente"], u["Tipo"], u["Refrigerador"]))

    def cargar_inventario(self):
        for item in self.tree_inv.get_children():
            self.tree_inv.delete(item)
            
        inventario_completo = self.sistema.obtener_inventario_general()
        
        f_comp = self.cb_f_comp.get()
        f_grupo = self.cb_f_grupo.get()
        f_estado = self.cb_f_estado.get()
        f_ubi = self.ent_f_ubi.get().strip().lower()
        f_orden = self.cb_f_orden.get()

        inventario_filtrado = []

        for bolsa in inventario_completo:
            if f_comp != "Todos" and bolsa["Componente"] != f_comp:
                continue
            if f_grupo != "Todos" and bolsa["Grupo"] != f_grupo:
                continue
            if f_estado != "Todos" and bolsa["Estado"] != f_estado:
                continue
            if f_ubi and f_ubi not in str(bolsa["Ubicación"]).lower():
                continue
            inventario_filtrado.append(bolsa)

        if "Ubicación" in f_orden:
            inventario_filtrado.sort(key=lambda x: (x["Ubicación"], x["Caducidad"]))
        elif "Caducidad" in f_orden:
            inventario_filtrado.sort(key=lambda x: x["Caducidad"])
        elif "Grupo Sanguíneo" in f_orden:
            inventario_filtrado.sort(key=lambda x: (x["Grupo"], x["Caducidad"]))
        elif "Estado" in f_orden:
            inventario_filtrado.sort(key=lambda x: (x["Estado"], x["Ubicación"]))

        for i in inventario_filtrado:
            self.tree_inv.insert("", "end", values=(i["Folio"], i["Componente"], i["Grupo"], i["Caducidad"], i["Estado"], i["Ubicación"]))

    def cargar_extracciones(self):
        for item in self.tree_ext.get_children():
            self.tree_ext.delete(item)
        extracciones = self.sistema.obtener_historial_extracciones_tabla()
        for ext in extracciones:
            self.tree_ext.insert("", "end", values=(ext["Folio"], ext["Donante"], ext["Volumen (ml)"], ext["Fecha y Hora"], ext["Observaciones"]))

    def ejecutar_liberacion(self):
        id_u = self.ent_sero_id.get()
        pwd = self.ent_sero_pass.get()
        resultados = {k: v.get() for k, v in self.vars.items()}
        
        exito, msj = self.sistema.procesar_liberacion_unidad(id_u, resultados, pwd)
        messagebox.showinfo("Resultados", msj)
        
        if exito:
            self.cargar_cuarentena()
            self.cargar_inventario() 
            self.ent_sero_id.delete(0, 'end')
            self.ent_sero_pass.delete(0, 'end')
            for var in self.vars.values():
                var.set(False)

    def ejecutar_fraccionamiento(self):
        exito, msj = self.sistema.procesar_fraccionamiento(self.ent_frac_id.get())
        messagebox.showinfo("Proceso Completo", msj)
        if exito:
            self.cargar_cuarentena()
            self.cargar_inventario()
            self.ent_frac_id.delete(0, 'end')

    def ejecutar_extraccion_crio(self):
        exito, msj = self.sistema.procesar_extraccion_crioprecipitado(self.ent_frac_id.get())
        messagebox.showinfo("Proceso Completo", msj)
        if exito:
            self.cargar_cuarentena()
            self.cargar_inventario()
            self.ent_frac_id.delete(0, 'end')