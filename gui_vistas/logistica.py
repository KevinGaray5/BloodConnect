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

class FrameLogistica(ctk.CTkFrame):
    """Módulo Logístico para solicitar o enviar sangre a otros hospitales."""
    def __init__(self, master, sistema):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        # =========================================================================
        # PANEL IZQUIERDO: BÚSQUEDA Y SOLICITUD EN RED
        # =========================================================================
        self.p_in = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.p_in.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        self.p_in.grid_columnconfigure(1, weight=1)
        self.p_in.grid_rowconfigure(6, weight=1) 

        ctk.CTkLabel(self.p_in, text="Solicitar Sangre a Otros Hospitales", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, pady=10)
        
        self.ei_cl = self._c(self.p_in, "CLUES Origen:", 1)
        self.ei_h = self._c(self.p_in, "Hospital Aliado:", 2)

        # --- Filtros de Búsqueda ---
        f_req = ctk.CTkFrame(self.p_in, fg_color="transparent")
        f_req.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        f_req.grid_columnconfigure((0,1,2), weight=1)

        self.cb_i_comp = ctk.CTkComboBox(f_req, values=["Globulos Rojos", "Plasma", "Plaquetas", "Crioprecipitados", "Sangre Entera"])
        self.cb_i_comp.grid(row=0, column=0, padx=2, sticky="ew")
        self.cb_i_sangre = ctk.CTkComboBox(f_req, values=["A", "B", "AB", "O"])
        self.cb_i_sangre.grid(row=0, column=1, padx=2, sticky="ew")
        self.cb_i_rh = ctk.CTkComboBox(f_req, values=["+", "-"])
        self.cb_i_rh.grid(row=0, column=2, padx=2, sticky="ew")

        ctk.CTkButton(self.p_in, text="🔍 Buscar Sangre Disponible", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.buscar_externo).grid(row=4, column=0, columnspan=2, pady=5)

        # --- Tabla de Resultados Externos ---
        cols = ("ID Unidad", "Componente", "Tipo", "Caducidad")
        self.tree_ext = ttk.Treeview(self.p_in, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            self.tree_ext.heading(c, text=c)
            self.tree_ext.column(c, anchor="center", width=100)

        scroll_ext = ttk.Scrollbar(self.p_in, orient="vertical", command=self.tree_ext.yview)
        self.tree_ext.configure(yscrollcommand=scroll_ext.set)
        self.tree_ext.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        scroll_ext.grid(row=5, column=2, sticky="ns", pady=5)

        # --- Solicitud y Recepción ---
        self.btn_solicitar = ctk.CTkButton(self.p_in, text="📤 Enviar Solicitud de Sangre", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_solicitud)
        self.btn_solicitar.grid(row=6, column=0, columnspan=2, pady=(10, 5))

        self.ei_folio = self._c(self.p_in, "Folio de Recepción:", 7)
        self.ei_folio.insert(0, datetime.now().strftime("%H%M%S"))

        ctk.CTkButton(self.p_in, text="📥 Añadir Sangre a Mi Inventario", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_ingreso).grid(row=8, column=0, columnspan=2, pady=(5, 15))

        # =========================================================================
        # PANEL DERECHO: DESPACHO / ENVÍO EXTERNO
        # =========================================================================
        self.p_out = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.p_out.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.p_out.grid_columnconfigure(1, weight=1)
        self.p_out.grid_rowconfigure(5, weight=1) 

        ctk.CTkLabel(self.p_out, text="Enviar Sangre a Otros Hospitales", font=ctk.CTkFont(size=18, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, columnspan=2, pady=10)
        self.eo_id = self._c(self.p_out, "Folio del Envío:", 1)
        self.eo_id.insert(0, datetime.now().strftime("%H%M%S"))
        
        self.eo_cl = self._c(self.p_out, "CLUES Destino:", 2)
        self.eo_h = self._c(self.p_out, "Hospital Destino:", 3)

        # --- TABLA DE INVENTARIO LOCAL ---
        ctk.CTkLabel(self.p_out, text="Unidades Locales Disponibles", font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=4, column=0, columnspan=2, pady=(10, 5), sticky="w", padx=15)
        
        self.tree_local = ttk.Treeview(self.p_out, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            self.tree_local.heading(c, text=c)
            self.tree_local.column(c, anchor="center", width=100)

        scroll_local = ttk.Scrollbar(self.p_out, orient="vertical", command=self.tree_local.yview)
        self.tree_local.configure(yscrollcommand=scroll_local.set)
        self.tree_local.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        scroll_local.grid(row=5, column=2, sticky="ns", pady=5)
        
        self.tree_local.bind("<ButtonRelease-1>", self._on_tree_local_select)

        # --- Despacho ---
        self.eo_ids = self._c(self.p_out, "IDs Unidades a Enviar:", 6)
        self.eo_ids.configure(placeholder_text="Clic en la tabla para rellenar")
        
        ctk.CTkButton(self.p_out, text="Enviar Unidades", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.ejecutar_despacho).grid(row=7, column=0, columnspan=2, pady=(15, 20))
        
        self.cargar_inventario_local()

    def _c(self, c, t, f):
        ctk.CTkLabel(c, text=t, text_color=C_TEXTO_OSCURO).grid(row=f, column=0, sticky="e", padx=10, pady=5)
        e = ctk.CTkEntry(c)
        e.grid(row=f, column=1, sticky="ew", padx=10, pady=5)
        return e

    def _on_tree_local_select(self, event):
        seleccion = self.tree_local.selection()
        ids = []
        for item in seleccion:
            id_u = self.tree_local.item(item)['values'][0]
            ids.append(str(id_u))
            
        self.eo_ids.delete(0, 'end')
        self.eo_ids.insert(0, ", ".join(ids))

    def cargar_inventario_local(self):
        for item in self.tree_local.get_children():
            self.tree_local.delete(item)
            
        inventario = self.sistema.obtener_inventario_general()
        for u in inventario:
            if u["Estado"] == "Liberada":
                self.tree_local.insert("", "end", values=(u["Folio"], u["Componente"], u["Grupo"], u["Caducidad"]))

    def buscar_externo(self):
        clues = self.ei_cl.get().strip()
        hosp = self.ei_h.get().strip()
        ruta_silenciosa = "datos/ext.csv" 
        
        comp = self.cb_i_comp.get()
        sangre = self.cb_i_sangre.get()
        rh = self.cb_i_rh.get()

        if not clues or not hosp:
            messagebox.showwarning("Faltan Datos", "Por favor, indique el CLUES y el nombre del Hospital.")
            return

        res, data = self.sistema.buscar_stock_en_red(clues, hosp, ruta_silenciosa, comp, sangre, rh)

        for i in self.tree_ext.get_children():
            self.tree_ext.delete(i)

        if res:
            for u in data:
                self.tree_ext.insert("", "end", values=(u['id_unidad'], u['tipo_componente'], f"{u['tipo_sangre']}{u['factor_rh']}", u['fecha_caducidad']))
            messagebox.showinfo("Búsqueda Exitosa", f"Se encontraron {len(data)} unidades compatibles en {hosp}.")
        else:
            messagebox.showerror("No se encontraron resultados", data)

    def ejecutar_solicitud(self):
        seleccion = self.tree_ext.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione al menos una unidad de la lista.")
            return
            
        hosp = self.ei_h.get().strip()
        cantidad = len(seleccion)
        
        messagebox.showinfo(
            "Solicitud Enviada", 
            f"Se ha enviado la solicitud al {hosp} para pedir {cantidad} unidades.\n\n"
            f"Cuando lleguen las bolsas físicas, use el botón de 'Añadir Sangre a Mi Inventario'."
        )

    def ejecutar_ingreso(self):
        seleccion = self.tree_ext.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Seleccione al menos una unidad de la lista.")
            return

        unidades_a_ingresar = []
        for item in seleccion:
            valores = self.tree_ext.item(item)['values']
            
            tipo_str = str(valores[2])
            if tipo_str.endswith('+') or tipo_str.endswith('-'):
                tipo_sangre = tipo_str[:-1]
                factor_rh = tipo_str[-1]
            else:
                tipo_sangre = tipo_str
                factor_rh = ""

            unidades_a_ingresar.append({
                'id_unidad': valores[0],
                'tipo_componente': valores[1],
                'tipo_sangre': tipo_sangre,
                'factor_rh': factor_rh,
                'fecha_caducidad': valores[3]
            })

        folio = self.ei_folio.get()
        if not folio:
            messagebox.showwarning("Atención", "Indique el folio de recepción.")
            return

        ruta_silenciosa = "datos/ext.csv" 
        res, msj = self.sistema.procesar_ingreso_externo(int(folio), self.ei_cl.get(), self.ei_h.get(), ruta_silenciosa, unidades_a_ingresar)

        if res:
            messagebox.showinfo("Bolsas Añadidas", msj)
            for i in seleccion:
                self.tree_ext.delete(i)
            self.cargar_inventario_local()
        else:
            messagebox.showerror("Error", msj)

    def ejecutar_despacho(self):
        try:
            texto_ids = self.eo_ids.get()
            if not texto_ids:
                messagebox.showwarning("Atención", "Ingrese los IDs de las bolsas a enviar separados por coma.")
                return
                
            ids = [int(x.strip()) for x in texto_ids.split(",") if x.strip()]
            
            ruta_silenciosa = "datos/ext.csv" 
            res, msj = self.sistema.procesar_envio_externo(int(self.eo_id.get()), self.eo_cl.get(), self.eo_h.get(), ruta_silenciosa, ids)
            
            if res:
                messagebox.showinfo("Envío Exitoso", msj)
                self.eo_ids.delete(0, 'end')
                self.cargar_inventario_local()
            else:
                messagebox.showerror("Error de Envío", msj)
        except ValueError:
            messagebox.showerror("Error", "Los IDs deben ser números separados por comas (ej: 101, 102).")
        except Exception as e: 
            messagebox.showerror("Error", f"Ocurrió un error al enviar: {e}")