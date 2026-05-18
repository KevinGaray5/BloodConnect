import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from PIL import Image
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Importación del controlador orquestador (Facade)
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# --- CONSTANTES DE COLOR ---
C_FONDO = "#f4f5f7"
C_ROJO = "#7a0000"
C_ROJO_HOVER = "#4d0000"
C_AZUL = "#133357"
C_AZUL_HOVER = "#0d223a"
C_TEXTO_OSCURO = "#333333"
C_BLANCO = "#ffffff"

class FrameDashboard(ctk.CTkFrame):
    """Vista principal: Muestra el estado global, alertas, KPIs y renderiza el dashboard gráfico nativo."""
    def __init__(self, master, sistema: SistemaBloodConnect):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- FILA 0: Header y Botón de Recarga ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.header_frame, text="Panel de Control", font=ctk.CTkFont(size=24, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(self.header_frame, text="🔄 Actualizar Datos", width=150, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.cargar_datos).grid(row=0, column=1, sticky="e", padx=(0, 10))
        ctk.CTkButton(self.header_frame, text="📥 Exportar Reporte", width=180, fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.exportar_reporte_ejecutivo).grid(row=0, column=2, sticky="e")

        # --- FILA 1: Tarjetas de KPIs ---
        self.panel_kpis = ctk.CTkFrame(self, fg_color="transparent")
        self.panel_kpis.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.panel_kpis.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Se inyecta la función lambda con la clave del módulo destino
        self.kpi_citas = self._crear_tarjeta_kpi(self.panel_kpis, "Citas de Hoy", "0", C_AZUL, 0, lambda: self.winfo_toplevel().mostrar_seccion("age"))
        self.kpi_cuarentena = self._crear_tarjeta_kpi(self.panel_kpis, "Sangre en Cuarentena", "0", C_ROJO, 1, lambda: self.winfo_toplevel().mostrar_seccion("alm"))
        self.kpi_pacientes = self._crear_tarjeta_kpi(self.panel_kpis, "Pacientes Registrados", "0", C_AZUL, 2, lambda: self.winfo_toplevel().mostrar_seccion("pac"))
        self.kpi_stock = self._crear_tarjeta_kpi(self.panel_kpis, "Sangre Disponible", "0", C_ROJO, 3, lambda: self.winfo_toplevel().mostrar_seccion("alm"))

        # --- FILA 2: Alertas Críticas y Acciones Rápidas ---
        self.panel_alertas = ctk.CTkFrame(self, fg_color=C_FONDO)
        self.panel_alertas.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        self.panel_alertas.grid_columnconfigure(0, weight=1)

        header_alertas = ctk.CTkFrame(self.panel_alertas, fg_color="transparent")
        header_alertas.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 0))
        header_alertas.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_alertas, text="Alertas de Inventario:", text_color=C_ROJO, font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.btn_solicitar_red = ctk.CTkButton(header_alertas, text="🚑 Solicitar Sangre", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self._ir_a_logistica)
        self.btn_solicitar_red.grid(row=0, column=1, sticky="e")

        self.txt_alertas = ctk.CTkTextbox(self.panel_alertas, height=80, fg_color=C_BLANCO, text_color=C_TEXTO_OSCURO, font=ctk.CTkFont(size=14))
        self.txt_alertas.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 10))

        # --- FILA 3: Gráfica Nativa y Mini-Feed de Auditoría ---
        self.panel_inferior = ctk.CTkFrame(self, fg_color="transparent")
        self.panel_inferior.grid(row=3, column=0, sticky="nsew", padx=20, pady=(5, 20))
        self.panel_inferior.grid_columnconfigure(0, weight=2)
        self.panel_inferior.grid_columnconfigure(1, weight=1)
        self.panel_inferior.grid_rowconfigure(0, weight=1)

        self.panel_grafico = ctk.CTkFrame(self.panel_inferior, fg_color=C_BLANCO)
        self.panel_grafico.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.panel_feed = ctk.CTkFrame(self.panel_inferior, fg_color=C_FONDO)
        self.panel_feed.grid(row=0, column=1, sticky="nsew")
        self.panel_feed.grid_rowconfigure(1, weight=1)
        self.panel_feed.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.panel_feed, text="Actividad Reciente", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w", padx=15, pady=10)
        self.txt_feed = ctk.CTkTextbox(self.panel_feed, font=ctk.CTkFont(size=12), fg_color=C_BLANCO, text_color=C_TEXTO_OSCURO, state="disabled")
        self.txt_feed.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.cargar_datos()

    def _crear_tarjeta_kpi(self, parent, titulo, valor_inicial, color_borde, columna, comando_navegacion):
        frame = ctk.CTkFrame(parent, fg_color=C_BLANCO, border_width=2, border_color=color_borde, cursor="hand2")
        frame.grid(row=0, column=columna, sticky="ew", padx=5)

        lbl_titulo = ctk.CTkLabel(frame, text=titulo, font=ctk.CTkFont(size=14), text_color=C_TEXTO_OSCURO, cursor="hand2")
        lbl_titulo.pack(pady=(10, 0))

        lbl_valor = ctk.CTkLabel(frame, text=valor_inicial, font=ctk.CTkFont(size=28, weight="bold"), text_color=C_TEXTO_OSCURO, cursor="hand2")
        lbl_valor.pack(pady=(0, 10))

        # Vinculación del clic izquierdo a la función de enrutamiento
        frame.bind("<Button-1>", lambda e: comando_navegacion())
        lbl_titulo.bind("<Button-1>", lambda e: comando_navegacion())
        lbl_valor.bind("<Button-1>", lambda e: comando_navegacion())

        # Efecto visual (Hover)
        def on_enter(e): 
            frame.configure(border_color=C_TEXTO_OSCURO) 
            
        def on_leave(e): 
            frame.configure(border_color=color_borde)
        
        # EL FIX: Aplicamos los eventos a la tarjeta y a sus textos internos
        for widget in (frame, lbl_titulo, lbl_valor):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        return lbl_valor
    
    def _ir_a_logistica(self):
        self.winfo_toplevel().mostrar_seccion("log")

    def exportar_reporte_ejecutivo(self):
        try:
            ruta_imagen = self.sistema.visualizar_estado_actual()
            if ruta_imagen and os.path.exists(ruta_imagen):
                messagebox.showinfo("Reporte Exportado", f"El gráfico de inventario ha sido guardado exitosamente en:\n\n{ruta_imagen}")
            else:
                messagebox.showerror("Error", "No se pudo guardar el archivo del reporte.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un problema al crear el reporte: {e}")

    def cargar_datos(self):
        hoy = date.today().strftime("%Y-%m-%d")
        
        # 1. Obtener y filtrar citas programadas
        citas = self.sistema.obtener_agenda_del_dia(hoy)
        citas_programadas = [cita for cita in citas if cita.get("Estado", "").strip().title() == "Programada"]
        self.kpi_citas.configure(text=str(len(citas_programadas)))
        
        # 2. Obtener unidades en cuarentena
        cuarentena = self.sistema.obtener_unidades_cuarentena()
        self.kpi_cuarentena.configure(text=str(len(cuarentena)))
        
        # 3. Obtener pacientes registrados activos
        pacientes = self.sistema.obtener_lista_pacientes()
        self.kpi_pacientes.configure(text=str(len(pacientes)))
        
        # 4. Obtener stock general y filtrar liberado
        inventario = self.sistema.obtener_inventario_general()
        total_liberado = sum(1 for u in inventario if u["Estado"] == "Liberada")
        self.kpi_stock.configure(text=str(total_liberado))

        # 5. Cargar alertas del sistema
        alertas = self.sistema.verificar_alertas_stock()
        self.txt_alertas.configure(state="normal")
        self.txt_alertas.delete("1.0", "end")
        self.txt_alertas.insert("1.0", alertas)
        self.txt_alertas.configure(state="disabled")

        # 6. Cargar feed de auditoría reciente
        exito, logs = self.sistema.obtener_historial_auditoria(limite=5)
        self.txt_feed.configure(state="normal")
        self.txt_feed.delete("1.0", "end")
        if exito and logs:
            self.txt_feed.insert("1.0", "\n\n".join(logs))
        else:
            self.txt_feed.insert("1.0", "No hay eventos recientes.")
        self.txt_feed.configure(state="disabled")

        # 7. Renderizar gráfica de barras nativa
        self._renderizar_grafica_nativa(inventario)

    def _renderizar_grafica_nativa(self, inventario):
        for widget in self.panel_grafico.winfo_children():
            widget.destroy()

        grupos_base = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        conteo_stock = {g: 0 for g in grupos_base}
        
        for u in inventario:
            if u["Estado"] == "Liberada":
                grupo = u["Grupo"]
                if grupo in conteo_stock:
                    conteo_stock[grupo] += 1

        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(5, 3), facecolor=C_BLANCO) 
        ax.set_facecolor(C_BLANCO)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#cccccc')
        ax.spines['left'].set_color('#cccccc')

        ax.bar(conteo_stock.keys(), conteo_stock.values(), color=C_AZUL)
        ax.set_title("Distribución de Sangre Disponible", color=C_TEXTO_OSCURO, pad=10)
        ax.tick_params(colors=C_TEXTO_OSCURO)
        
        from matplotlib.ticker import MaxNLocator
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        canvas = FigureCanvasTkAgg(fig, master=self.panel_grafico)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)

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

class FrameAuditoria(ctk.CTkFrame):
    """Módulo de seguridad, historial del sistema y rastreo de bolsas."""
    def __init__(self, master, sistema):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.sistema = sistema
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        self.tab_bitacora = self.tabview.add("📜 Registro de Actividad")
        self.tab_trazabilidad = self.tabview.add("🔍 Rastreo de Bolsas")
        self.tab_accesos = self.tabview.add("🛡️ Personal y Accesos")

        self._construir_tab_bitacora()
        self._construir_tab_trazabilidad()
        self._construir_tab_accesos()

    def _construir_tab_accesos(self):
        self.tab_accesos.grid_columnconfigure(0, weight=1)
        self.tab_accesos.grid_rowconfigure(1, weight=1)

        h = ctk.CTkFrame(self.tab_accesos, fg_color="transparent")
        h.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(h, text="Lista de Personal Autorizado", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).pack(side="left")

        self.ent_buscar_acc = ctk.CTkEntry(h, placeholder_text="🔍 Filtrar por nombre o matrícula...", width=250)
        self.ent_buscar_acc.pack(side="left", padx=20)
        self.ent_buscar_acc.bind("<KeyRelease>", lambda e: self.cargar_accesos())

        ctk.CTkButton(h, text="🛑 Quitar Acceso", fg_color=C_ROJO, hover_color=C_ROJO_HOVER, command=self.revocar_acceso_mock).pack(side="right", padx=5)

        cols = ("Matrícula", "Nombre", "Cédula Profesional", "Rol Asignado")
        self.tree_acc = ttk.Treeview(self.tab_accesos, columns=cols, show="headings")
        for c in cols:
            self.tree_acc.heading(c, text=c)
            self.tree_acc.column(c, anchor="center")
        self.tree_acc.column("Nombre", anchor="w", width=250)

        self.tree_acc.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.cargar_accesos()

    def cargar_accesos(self):
        for i in self.tree_acc.get_children(): 
            self.tree_acc.delete(i)
            
        trabajadores = self.sistema.obtener_lista_trabajadores()
        q = self.ent_buscar_acc.get().lower()
        
        for t in trabajadores:
            if q and q not in str(t.get('nombre', '')).lower() and q not in str(t.get('id_global', '')):
                continue
            self.tree_acc.insert("", "end", values=(t.get('id_global'), t.get('nombre'), t.get('cedula_profesional'), t.get('rol')))

    def revocar_acceso_mock(self):
        seleccion = self.tree_acc.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Elija un usuario de la lista para quitarle el acceso.")
            return
        matricula = self.tree_acc.item(seleccion[0])['values'][0]
        messagebox.showinfo("Acceso Revocado", f"El usuario con matrícula {matricula} ya no tiene acceso al sistema.")

    def _construir_tab_bitacora(self):
        self.tab_bitacora.grid_columnconfigure(0, weight=1)
        self.tab_bitacora.grid_rowconfigure(1, weight=1)
        
        self.h = ctk.CTkFrame(self.tab_bitacora, fg_color="transparent")
        self.h.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(self.h, text="Historial del Sistema", font=ctk.CTkFont(size=16, weight="bold"), text_color=C_TEXTO_OSCURO).grid(row=0, column=0, sticky="w", padx=(0, 20))
        ctk.CTkButton(self.h, text="📜 Actualizar Historial", command=self.ver_log, fg_color=C_AZUL, hover_color=C_AZUL_HOVER).grid(row=0, column=1, padx=5)
        ctk.CTkButton(self.h, text="💾 Descargar Respaldo", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.respaldo).grid(row=0, column=2, padx=5)

        self.tx = ctk.CTkTextbox(self.tab_bitacora, font=ctk.CTkFont(size=12), text_color=C_TEXTO_OSCURO, fg_color=C_BLANCO)
        self.tx.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        self.ver_log()

    def _construir_tab_trazabilidad(self):
        self.tab_trazabilidad.grid_columnconfigure(0, weight=1)
        self.tab_trazabilidad.grid_rowconfigure(1, weight=1)

        self.panel_busqueda = ctk.CTkFrame(self.tab_trazabilidad, fg_color=C_FONDO)
        self.panel_busqueda.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.panel_busqueda.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(self.panel_busqueda, text="Folio de la Bolsa de Sangre:", text_color=C_TEXTO_OSCURO).grid(row=0, column=0, padx=10, pady=15, sticky="e")
        self.ent_traz_id = ctk.CTkEntry(self.panel_busqueda, width=200, placeholder_text="Ej. 260515210111")
        self.ent_traz_id.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        ctk.CTkButton(self.panel_busqueda, text="🔍 Buscar Historial de la Bolsa", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.ejecutar_trazabilidad).grid(row=0, column=2, padx=10)
        ctk.CTkButton(self.panel_busqueda, text="🖨️ Imprimir Etiqueta", fg_color=C_AZUL, hover_color=C_AZUL_HOVER, command=self.imprimir_etiqueta).grid(row=0, column=3, padx=10, sticky="w")

        self.txt_traz = ctk.CTkTextbox(self.tab_trazabilidad, font=ctk.CTkFont(size=13), text_color=C_TEXTO_OSCURO, fg_color=C_BLANCO)
        self.txt_traz.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.txt_traz.insert("1.0", "MÓDULO DE RASTREO:\nEscriba el folio de la bolsa arriba y presione 'Buscar Historial de la Bolsa' para ver todo su recorrido.")
        self.txt_traz.configure(state="disabled")

    def ver_log(self):
        res, logs = self.sistema.obtener_historial_auditoria(50)
        self.tx.configure(state="normal")
        self.tx.delete("1.0", "end")
        if res: 
            self.tx.insert("1.0", "\n".join(logs))
        else: 
            self.tx.insert("1.0", "No se pudo leer el historial.")
        self.tx.configure(state="disabled")

    def respaldo(self):
        res, msj = self.sistema.ejecutar_respaldo_seguridad()
        messagebox.showinfo("Respaldo Creado", msj)

    def ejecutar_trazabilidad(self):
        id_unidad = self.ent_traz_id.get().strip()
        if not id_unidad:
            messagebox.showwarning("Atención", "Debe ingresar el número de la bolsa que quiere buscar.")
            return

        exito, datos = self.sistema.rastrear_trazabilidad_bolsa(id_unidad)
        
        self.txt_traz.configure(state="normal")
        self.txt_traz.delete("1.0", "end")
        
        if exito:
            u = datos.get("unidad_consultada", {})
            ext = datos.get("evento_extraccion", {})
            don = ext.get("donante", {})
            receptores = datos.get("receptores_vinculados_familia", [])
            
            tipo_origen = "Bolsa Principal" if not datos.get("es_derivado") else "Subcomponente"
            
            rep = []
            rep.append("======================================================================")
            rep.append("                   HISTORIAL COMPLETO DE LA BOLSA                     ")
            rep.append("======================================================================")
            rep.append(f"Folio Buscado: {datos.get('trazabilidad_isbt_folio')}")
            rep.append(f"Fecha de Búsqueda: {datos.get('timestamp_consulta')}")
            rep.append("----------------------------------------------------------------------\n")
            
            rep.append("1. DETALLES DE LA BOLSA")
            rep.append("--------------------------------------------------")
            rep.append(f" ➔ ID de la Bolsa          : {u.get('id_unidad')}")
            rep.append(f" ➔ Componente              : {u.get('tipo_componente')}")
            rep.append(f" ➔ Grupo Sanguíneo         : {don.get('tipo_sangre', 'N/A')}")
            rep.append(f" ➔ Fecha de Caducidad      : {u.get('caducidad')}")
            rep.append(f" ➔ Estado Actual           : {u.get('estado_actual')}")
            rep.append(f" ➔ Tipo de Bolsa           : {tipo_origen}")
            rep.append(f" ➔ ID Bolsa Original       : {datos.get('bolsa_madre_origen_id')}")
            rep.append("")
            
            rep.append("2. INFORMACIÓN DEL DONANTE")
            rep.append("--------------------------------------------------")
            rep.append(f" ➔ Fecha de Donación       : {ext.get('fecha_hora')}")
            rep.append(f" ➔ Nombre del Donante      : {don.get('nombre')}")
            rep.append(f" ➔ ID del Donante          : {don.get('id_global')}")
            rep.append(f" ➔ Grupo Sanguíneo         : {don.get('tipo_sangre')}")
            rep.append("")
            
            rep.append("3. RESULTADOS DE LABORATORIO")
            rep.append("--------------------------------------------------")
            rep.append(f" ➔ Análisis de Infecciones : {datos.get('dictamen_serologico_global')}")
            rep.append("")
            
            rep.append("4. USO DE LA BOLSA O SUS COMPONENTES")
            rep.append("--------------------------------------------------")
            if not receptores:
                rep.append(" ➔ No hay registros de que esta bolsa o sus componentes hayan sido asignados a pacientes.")
            else:
                rep.append(f"Se encontraron {len(receptores)} usos de esta sangre:")
                for idx, r in enumerate(receptores, 1):
                    rep.append(f"\n   [Asignación #{idx}]")
                    rep.append(f"   · Folio de Transfusión  : {r.get('id_transfusion')}")
                    rep.append(f"   · Bolsa Utilizada       : {r.get('id_unidad_transfundida')}")
                    rep.append(f"   · ID del Paciente       : {r.get('id_paciente')}")
                    rep.append(f"   · Nombre del Paciente   : {r.get('nombre_paciente')}")
                    rep.append(f"   · Fecha de Uso          : {r.get('fecha_transfusion')}")
                    rep.append(f"   · Reacciones Adversas   : {r.get('reacciones_adversas')}")
            
            rep.append("\n======================================================================")
            rep.append("                     FIN DEL HISTORIAL                                ")
            rep.append("======================================================================")
            
            self.txt_traz.insert("end", "\n".join(rep))
        else:
            self.txt_traz.insert("end", f"⚠️ --- ERROR AL BUSCAR LA BOLSA ---\n\nDetalle: {datos}")
            
        self.txt_traz.configure(state="disabled")

    def imprimir_etiqueta(self):
        id_unidad = self.ent_traz_id.get().strip()
        if not id_unidad:
            messagebox.showwarning("Atención", "Debe ingresar el ID de la bolsa.")
            return

        exito, msj = self.sistema.exportar_etiqueta_fisica_mock(id_unidad)
        if exito:
            messagebox.showinfo("Impresión", "La etiqueta ha sido enviada a la impresora exitosamente.")
        else:
            messagebox.showerror("Error", msj)

class VentanaPrincipal(ctk.CTk):
    """Ventana principal que controla los menús laterales y muestra las diferentes pantallas."""
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
            ruta_logo = os.path.join("gui_elementos", "logo.png")
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

        self.marcos = {
            "dash": FrameDashboard(self.contenedor, self.sistema), "don": FrameDonantes(self.contenedor, self.sistema),
            "age": FrameAgenda(self.contenedor, self.sistema), "alm": FrameAlmacen(self.contenedor, self.sistema),
            "pac": FramePacientes(self.contenedor, self.sistema), "log": FrameLogistica(self.contenedor, self.sistema),
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
        self.destroy() 
        app_login = VentanaLogin()
        app_login.mainloop()

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
            ruta_logo = os.path.join("gui_elementos", "logo.png")
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