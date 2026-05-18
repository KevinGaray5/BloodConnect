"""
Módulo del Controlador de Auditoría y Reportes - BloodConnect
Este archivo funciona como el "supervisor" del sistema. Se encarga de vigilar 
y anotar todo lo que pasa (bitácora), rastrear el origen de cualquier bolsa de sangre, 
dibujar las gráficas de inventario y hacer las copias de seguridad de los archivos.
"""

import os
from datetime import datetime, date
from typing import Tuple, Any, Optional
import pandas as pd

from clases.auditoria import GestorDatos, AnalizadorReportes, Bitacora, EntidadAfectada, NivelSeveridad, PROJECT_ROOT 
from clases.gestion_almacen import Inventario, Hemocomponente, TipoHemocomponente, EstadoHemocomponente
from clases.gestion_identidades import Trabajador

class CtrlAuditoria:
    def __init__(self, gestor: GestorDatos, inventario: Inventario):
        self.gestor = gestor
        self.inventario = inventario
        # Guarda el trabajador que está usando el sistema para saber quién hace las consultas o copias
        self.usuario_actual: Optional[Trabajador] = None

    def _registrar_auditoria(self, entidad: EntidadAfectada, accion: str, severidad: NivelSeveridad):
        """Anota silenciosamente en el archivo de texto cualquier acción importante para tener un historial seguro."""
        try:
            id_usuario = self.usuario_actual.id_global if self.usuario_actual else 0
            id_log = int(datetime.now().strftime("%y%m%d%H%M%S")) 
            
            registro = Bitacora(id_log, id_usuario, entidad, accion, severidad)
            registro.escribir_entrada_inmutable(self.gestor.ruta_log)
        except Exception as e:
            # Mensaje en consola si el guardado del historial falla
            print(f"Aviso del sistema: No se pudo escribir en el archivo de bitácora. Detalle: {e}")

    # =========================================================================
    # MÓDULO DE AUDITORÍA, REPORTEO, TRAZABILIDAD Y ALERTAS
    # =========================================================================

    def rastrear_trazabilidad_bolsa(self, id_unidad: Any) -> Tuple[bool, Any]:
        """
        Rastrea la historia completa de una bolsa de sangre (de vena a vena). 
        Busca quién la donó, si se separó en otros componentes y a qué paciente se le administró.
        """
        try:
            id_u_int = int(id_unidad)
        except (ValueError, TypeError):
            return False, "Error: El número de folio a buscar debe contener solo números."

        try:
            id_u_str = str(id_u_int)
            id_madre_str = id_u_str
            es_derivado = False
            bolsa_madre_id = None
            
            # Revisamos si el número de bolsa indica que es un componente separado (terminaciones 1, 2, 3 o 24)
            if id_u_str.endswith("24"): 
                id_madre_str = id_u_str[:-2]
                es_derivado = True
                bolsa_madre_id = int(id_u_str[:-1]) 
            elif id_u_str[-1] in ["1", "2", "3"] and len(id_u_str) > 12: 
                id_madre_str = id_u_str[:-1]
                es_derivado = True
                bolsa_madre_id = int(id_madre_str)

            # Buscamos en el archivo de extracciones cuándo se donó esta sangre
            df_extracciones = self.gestor.leer_persistencias("extracciones")
            fila_extraccion = None
            
            if df_extracciones is not None and not df_extracciones.empty and 'id_extraccion' in df_extracciones.columns:
                filtro_exacto = df_extracciones[df_extracciones['id_extraccion'] == id_u_int]
                if not filtro_exacto.empty:
                    fila_extraccion = filtro_exacto.iloc[0]
                elif es_derivado and int(id_madre_str) in df_extracciones['id_extraccion'].values:
                    fila_extraccion = df_extracciones[df_extracciones['id_extraccion'] == int(id_madre_str)].iloc[0]
                else:
                    for _, row in df_extracciones.iterrows():
                        if id_u_str.startswith(str(row['id_extraccion'])):
                            fila_extraccion = row
                            id_madre_str = str(row['id_extraccion'])
                            es_derivado = (id_madre_str != id_u_str)
                            if es_derivado:
                                bolsa_madre_id = int(id_madre_str) if not id_u_str.endswith("24") else int(id_u_str[:-1])
                            break

            datos_donante = {"nombre": "Expediente no ubicado", "id_global": "N/A", "tipo_sangre": "N/A"}
            fecha_extraccion = "Fecha no registrada"
            
            # Si encontramos cuándo se extrajo, buscamos quién fue la persona que la donó
            if fila_extraccion is not None:
                fecha_extraccion = str(fila_extraccion.get('fecha_hora', 'Fecha no registrada'))
                id_donante = fila_extraccion.get('id_donante')
                
                df_donantes = self.gestor.leer_persistencias("donantes")
                if df_donantes is not None and not df_donantes.empty and 'id_global' in df_donantes.columns:
                    f_don = df_donantes[df_donantes['id_global'] == id_donante]
                    if not f_don.empty:
                        d_row = f_don.iloc[0]
                        datos_donante = {
                            "nombre": str(d_row.get('nombre', 'Desconocido')),
                            "id_global": int(id_donante),
                            "tipo_sangre": f"{d_row.get('tipo_sangre', '')}{d_row.get('factor_rh', '')}"
                        }

            # Preparamos la información de la bolsa actual
            info_unidad = {
                "id_unidad": id_u_int,
                "tipo_componente": "Indeterminado",
                "estado_actual": "Extraviado / Sin registro de inventario",
                "caducidad": "N/A",
                "historial_serologia": "Pendiente de Procesamiento"
            }
            
            # Revisamos en qué estado se encuentra la bolsa en el inventario
            df_inv = self.gestor.leer_persistencias("inventario")
            u_mem = self.inventario.obtener_unidad_por_id(id_u_int)
            
            if u_mem:
                info_unidad["tipo_componente"] = u_mem.tipo_componente.value
                info_unidad["estado_actual"] = u_mem.estado.value
                info_unidad["caducidad"] = str(u_mem.fecha_caducidad)
                if u_mem.estado in [EstadoHemocomponente.LIBERADA, EstadoHemocomponente.TRANSFUNDIDA, EstadoHemocomponente.FRACCIONADA]:
                    info_unidad["historial_serologia"] = "Aprobado (Pruebas negativas a enfermedades)"
                elif u_mem.estado == EstadoHemocomponente.DESECHADA:
                    info_unidad["historial_serologia"] = "Rechazado (No apta para uso médico)"
            elif df_inv is not None and not df_inv.empty and 'id_unidad' in df_inv.columns:
                f_inv = df_inv[df_inv['id_unidad'] == id_u_int]
                if not f_inv.empty:
                    i_row = f_inv.iloc[0]
                    info_unidad["tipo_componente"] = str(i_row.get('tipo_componente', 'Indeterminado'))
                    info_unidad["estado_actual"] = str(i_row.get('estado', 'Indeterminado'))
                    info_unidad["caducidad"] = str(i_row.get('fecha_caducidad', 'N/A'))
                    e_str = info_unidad["estado_actual"].strip().title()
                    if e_str in ["Liberada", "Transfundida", "Fraccionada"]:
                        info_unidad["historial_serologia"] = "Aprobado (Pruebas negativas a enfermedades)"
                    elif e_str == "Desechada":
                        info_unidad["historial_serologia"] = "Rechazado (No apta para uso médico)"

            # Por último, revisamos si la bolsa o sus derivados ya se le transfundieron a un paciente
            receptores = []
            df_trans = self.gestor.leer_persistencias("transfusiones")
            df_pacientes = self.gestor.leer_persistencias("pacientes")
            
            if df_trans is not None and not df_trans.empty and 'id_unidad' in df_trans.columns:
                ids_familia = [
                    int(id_madre_str),
                    int(f"{id_madre_str}1"),
                    int(f"{id_madre_str}2"),
                    int(f"{id_madre_str}3"),
                    int(f"{id_madre_str}24")
                ]
                
                filtro_trans = df_trans[df_trans['id_unidad'].isin(ids_familia)]
                
                for _, t_row in filtro_trans.iterrows():
                    id_pac = t_row.get('id_paciente')
                    nombre_pac = "Paciente no identificado"
                    
                    if df_pacientes is not None and not df_pacientes.empty and 'id_paciente' in df_pacientes.columns:
                        f_pac = df_pacientes[df_pacientes['id_paciente'] == id_pac]
                        if not f_pac.empty:
                            nombre_pac = str(f_pac.iloc[0].get('nombre', 'Desconocido'))
                            
                    receptores.append({
                        "id_transfusion": int(t_row.get('id_transfusion', 0)),
                        "id_unidad_transfundida": int(t_row.get('id_unidad', 0)),
                        "id_paciente": int(id_pac) if pd.notna(id_pac) else "N/A",
                        "nombre_paciente": nombre_pac,
                        "fecha_transfusion": str(t_row.get('timestamp_inicio', 'Desconocida')),
                        "reacciones_adversas": str(t_row.get('reacciones_adversas', 'Ninguna'))
                    })

            dict_trazabilidad = {
                "trazabilidad_isbt_folio": f"ISBT-TRACE-{id_u_int}",
                "timestamp_consulta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "unidad_consultada": info_unidad,
                "es_derivado": es_derivado,
                "bolsa_madre_origen_id": bolsa_madre_id if es_derivado else "N/A (Bolsa Primaria)",
                "evento_extraccion": {
                    "fecha_hora": fecha_extraccion,
                    "donante": datos_donante
                },
                "dictamen_serologico_global": info_unidad["historial_serologia"],
                "receptores_vinculados_familia": receptores
            }
            
            self._registrar_auditoria(EntidadAfectada.HEMOCOMPONENTE, f"Se consultó exitosamente el historial completo de la bolsa {id_u_int}.", NivelSeveridad.INFO)
            return True, dict_trazabilidad

        except Exception as e:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Ocurrió un problema al rastrear la bolsa: {e}", NivelSeveridad.CRITICO)
            return False, f"Tuvimos un problema al reconstruir el historial de la bolsa: {e}"

    def ejecutar_respaldo_seguridad(self) -> Tuple[bool, str]:
        """Hace una copia de seguridad de todos los archivos del sistema para no perder datos en caso de accidente."""
        try:
            rutas_respaldo = self.gestor.respaldar_datos()
            if rutas_respaldo:
                detalle_rutas = "\n".join(rutas_respaldo)
                self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Se creó una copia de seguridad de {len(rutas_respaldo)} archivos.", NivelSeveridad.INFO)
                return True, f"¡Copia de seguridad guardada con éxito!\nArchivos respaldados en:\n{detalle_rutas}"
            else:
                return False, "Aviso: No encontramos archivos de datos para respaldar."
        except Exception as e:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Error al hacer la copia de seguridad: {e}", NivelSeveridad.CRITICO)
            return False, f"Tuvimos un problema al guardar el respaldo: {e}"

    def obtener_historial_auditoria(self, limite: int = 20) -> Tuple[bool, Any]:
        """Lee las líneas más recientes del archivo de texto para mostrar las últimas acciones realizadas en el sistema."""
        try:
            lim_int = int(limite)
            lineas = Bitacora.consultar_historial_auditoria(ruta_archivo=self.gestor.ruta_log, limite=lim_int)
            return True, lineas
        except FileNotFoundError as fnf:
            return False, f"El archivo del historial aún no existe: {fnf}"
        except Exception as e:
            return False, f"Ocurrió un problema técnico al leer el historial: {e}"

    def visualizar_estado_actual(self) -> Optional[str]:
        """Calcula cuánta sangre hay de cada tipo y genera una imagen de gráfica de barras para el reporte."""
        try:
            datos_crudos = self.inventario.calcular_stock_dinamico()
            if not datos_crudos:
                return None

            todos_los_grupos = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
            datos_grafica = {grupo: 0 for grupo in todos_los_grupos}
            
            # Sumamos las cantidades quitando el texto extra para que la gráfica se vea más limpia
            for grupo, cantidad in datos_crudos.items():
                grupo_limpio = grupo.replace("Globulos Rojos ", "").strip()
                if grupo_limpio in datos_grafica:
                    datos_grafica[grupo_limpio] += cantidad
                    
            config = {"color_barras": "crimson", "color_exportacion": "darkred"}
            analizador = AnalizadorReportes(config)
            ruta_imagen = analizador.generar_dashboard_stock(datos_grafica)

            return ruta_imagen

        except ValueError:
            return None
        except IOError as ioe:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Problema al intentar guardar la imagen de la gráfica: {ioe}", NivelSeveridad.ADVERTENCIA)
            return None
        except Exception as e:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Error general al intentar crear la gráfica: {e}", NivelSeveridad.ADVERTENCIA)
            return None
    
    def exportar_etiqueta_fisica_mock(self, id_unidad: Any) -> Tuple[bool, str]:
        """
        Simula la impresión de una etiqueta física con código de barras (norma ISBT 128). 
        Como no tenemos una impresora térmica conectada al proyecto, lo guarda en un archivo de texto como demostración.
        """
        try:
            id_u_int = int(id_unidad)
        except (ValueError, TypeError):
            return False, "Error: El identificador de la bolsa debe ser un número."

        try:
            unidad = self.inventario.obtener_unidad_por_id(id_u_int)
            
            # Si la bolsa no está cargada en memoria, la buscamos directamente en el archivo
            if not unidad:
                df_inv = self.gestor.leer_persistencias("inventario")
                if df_inv is not None and not df_inv.empty and 'id_unidad' in df_inv.columns:
                    filtro = df_inv[df_inv['id_unidad'] == id_u_int]
                    if not filtro.empty:
                        fila = filtro.iloc[0]
                        partes = str(fila['fecha_caducidad']).split('-')
                        fecha_cad = date(int(partes[0]), int(partes[1]), int(partes[2]))
                        unidad = Hemocomponente(
                            id_unidad=int(fila['id_unidad']),
                            tipo_componente=TipoHemocomponente(fila['tipo_componente']),
                            tipo_sangre=str(fila['tipo_sangre']),
                            factor_rh=str(fila['factor_rh']),
                            fecha_caducidad=fecha_cad,
                            temperatura_almacenamiento=float(fila['temperatura_almacenamiento']),
                            estado=EstadoHemocomponente(fila['estado']),
                            refrigerador_asignado=str(fila['refrigerador_asignado'])
                        )

            if not unidad:
                return False, f"Aviso: No encontramos la bolsa número {id_u_int} para imprimir su etiqueta."

            # Armamos el texto que se enviaría a la impresora
            codigo_isbt = f"=W0001 {datetime.now().strftime('%y')} {id_u_int}"
            etiqueta_texto = (
                f"{'='*42}\n"
                f"   ETIQUETA DE BOLSA - ESTÁNDAR ISBT 128\n"
                f"{'='*42}\n"
                f"Folio Interno: {unidad.id_unidad}\n"
                f"Código ISBT Lineal: {codigo_isbt}\n"
                f"Componente: {unidad.tipo_componente.value.upper()}\n"
                f"Grupo y Rh: {unidad.tipo_sangre}{unidad.factor_rh}\n"
                f"Caducidad biológica: {unidad.fecha_caducidad.strftime('%Y-%m-%d')}\n"
                f"Almacenamiento estricto: {unidad.temperatura_almacenamiento} °C\n"
                f"Estado Actual: {unidad.estado.value.upper()}\n"
                f"Impreso en: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"{'='*42}\n\n"
            )

            directorio_salida = os.path.join(PROJECT_ROOT, self.gestor.config["directorios"]["datos"])
            os.makedirs(directorio_salida, exist_ok=True)
            ruta_salida = os.path.join(directorio_salida, "etiquetas_impresas_mock.txt")
            
            with open(ruta_salida, "a", encoding="utf-8") as f:
                f.write(etiqueta_texto)

            self._registrar_auditoria(EntidadAfectada.HEMOCOMPONENTE, f"Se generó el archivo de impresión para la etiqueta de la bolsa {id_u_int}.", NivelSeveridad.INFO)
            return True, f"Etiqueta lista.\nComo no hay impresora conectada, se guardó en:\n{ruta_salida}"

        except Exception as e:
            return False, f"Tuvimos un problema al generar la etiqueta: {e}"