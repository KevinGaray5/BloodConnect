import os
import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Importación de tipos para el controlador
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de los estilos
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_AZUL_HOVER, 
    C_TEXTO_OSCURO, C_BLANCO
)

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