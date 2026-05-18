import customtkinter as ctk
from tkinter import ttk, messagebox

# Importación del controlador
from controladores.sistema_bc_ctrl import SistemaBloodConnect

# Importación de las constantes de estilo
from gui_vistas.tema_gui import (
    C_FONDO, C_ROJO, C_ROJO_HOVER, C_AZUL, C_AZUL_HOVER, 
    C_TEXTO_OSCURO, C_BLANCO
)

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