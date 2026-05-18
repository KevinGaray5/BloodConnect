"""
Módulo del Controlador de Almacén - BloodConnect
Este archivo es el administrador del inventario. Se encarga de recibir la sangre 
recién donada, mandarla a cuarentena, dividirla en componentes (glóbulos, plasma, etc.) 
y verificar los resultados del laboratorio para saber si la sangre es segura para usarse.
"""

from typing import Tuple, List, Dict, Optional, Any
from datetime import datetime, date, timedelta
import pandas as pd

# Importaciones de modelos de dominio
from clases.gestion_almacen import (
    Extraccion, Hemocomponente, TipoHemocomponente, 
    EstadoHemocomponente, Inventario, PruebaLaboratorio
)
from clases.gestion_identidades import Donante, Trabajador
from clases.auditoria import GestorDatos, Bitacora, EntidadAfectada, NivelSeveridad

class CtrlAlmacen:
    def __init__(self, gestor: GestorDatos):
        self.gestor = gestor
        self.usuario_actual: Optional[Trabajador] = None
        
        # Este controlador es el único que maneja el inventario mientras el programa está abierto
        self.inventario = Inventario(umbral_critico_seguridad=10)
        self.inventario.cargar_inventario_inicial(self.gestor)

    def _registrar_auditoria(self, entidad: EntidadAfectada, accion: str, severidad: NivelSeveridad):
        """Guarda en la bitácora un registro cada vez que movemos, dividimos o desechamos una bolsa de sangre."""
        try:
            id_usuario = self.usuario_actual.id_global if self.usuario_actual else 0
            id_log = int(datetime.now().strftime("%y%m%d%H%M%S")) 
            
            registro = Bitacora(id_log, id_usuario, entidad, accion, severidad)
            registro.escribir_entrada_inmutable(self.gestor.ruta_log)
        except Exception as e:
            # Aviso en consola por si el archivo de historial falla
            print(f"Aviso del sistema: No se pudo guardar el registro del almacén en la bitácora. Detalle: {e}")

    # --- FLUJO DE EXTRACCIÓN ---

    def procesar_donacion_exitosa_ui(self, id_donante_str: Any, volumen_str: Any) -> Tuple[bool, str, int]:
        """
        Funciona como un puente. Recibe los datos de texto directamente desde la pantalla 
        (interfaz gráfica), verifica que sean números válidos y luego llama a la función principal.
        """
        if not self.usuario_actual:
            return False, "Permiso denegado: Primero inicie sesión en el sistema.", 0
            
        try:
            id_don = int(id_donante_str)
            vol = int(volumen_str)
            id_pers = self.usuario_actual.id_global
        except ValueError:
            return False, "Error: El volumen extraído y el número del donante deben ser números enteros.", 0

        donante_obj = Donante.cargar_desde_csv(id_don, self.gestor)
        if not donante_obj:
            return False, f"No encontramos el expediente del donante número {id_don}.", 0

        exito, mensaje = self.procesar_donacion_exitosa(donante_obj, id_pers, vol)
        
        # Extraemos el número de folio de la bolsa para que la pantalla pueda mostrarlo
        folio_numerico = 0
        if exito:
            import re
            match = re.search(r'Unidad (\d+)', mensaje)
            if match:
                folio_numerico = int(match.group(1))

        return exito, mensaje, folio_numerico

    def procesar_donacion_exitosa(self, donante: Donante, personal_id: int, volumen: int) -> Tuple[bool, str]:
        """
        Hace el trabajo pesado cuando alguien dona sangre: crea la bolsa física en el sistema, 
        la manda directo a la zona de cuarentena y le pone una etiqueta de seguimiento.
        Si ocurre un error al guardar los archivos, deshace todo para no dejar registros a medias.
        """
        if not donante or not personal_id:
            return False, "Faltan datos del donante o del médico responsable."

        if not donante.estado_elegibilidad:
            return False, f"Aviso Médico: El donante {donante.nombre} no es apto para donar o no ha pasado su revisión."

        try:
            id_nueva_ext = int(datetime.now().strftime("%y%m%d%H%M%S"))
            
            # Registramos el evento de la extracción
            nueva_extraccion = Extraccion(
                id_extraccion=id_nueva_ext,
                id_donante=donante.id_global,
                volumen_ml=volumen,
                id_personal_responsable=personal_id
            )

            # Creamos la bolsa de Sangre Entera y la mandamos a cuarentena
            nueva_unidad = Hemocomponente(
                id_unidad=id_nueva_ext,
                tipo_componente=TipoHemocomponente.SANGRE_ENTERA,
                tipo_sangre=donante.tipo_sangre,
                factor_rh=donante.factor_rh,
                fecha_caducidad=date.today() + timedelta(days=35),
                temperatura_almacenamiento=4.0,
                estado=EstadoHemocomponente.EN_CUARENTENA,
                refrigerador_asignado="Area-Cuarentena-01"
            )

            # Guardamos cómo estaba el donante antes por si tenemos que revertir cambios
            ultima_donacion_previa = donante.ultima_donacion
            estado_elegibilidad_previo = donante.estado_elegibilidad

            self.inventario.ingresar_unidad(nueva_unidad)

            try:
                # Guardamos la bolsa y el registro de la extracción en los archivos CSV
                self.inventario.guardar_inventario_actualizado(self.gestor)
                nueva_extraccion.registrar_extraccion(self.gestor)

                # Actualizamos al donante para que empiece a contar su tiempo de descanso (56 días)
                donante.ultima_donacion = date.today()
                donante.estado_elegibilidad = False
                donante.registrar_donante(self.gestor)

                etiqueta = nueva_extraccion.generar_etiqueta_trazabilidad()
                
                self._registrar_auditoria(EntidadAfectada.HEMOCOMPONENTE, f"Extracción registrada. Bolsa {id_nueva_ext} etiquetada como: {etiqueta}", NivelSeveridad.INFO)
                return True, (f"Donación registrada con éxito.\nLa bolsa {id_nueva_ext} de {donante.nombre} se mandó a cuarentena.\nEtiqueta de seguimiento: {etiqueta}")

            except Exception as e:
                # Si algo falló al escribir los archivos, revertimos todo a su estado original (Rollback)
                if nueva_unidad in self.inventario.unidades_disponibles:
                    self.inventario.unidades_disponibles.remove(nueva_unidad)
                try:
                    self.inventario.guardar_inventario_actualizado(self.gestor)
                except Exception: pass 

                df_ext = self.gestor.leer_persistencias("extracciones")
                if df_ext is not None and not df_ext.empty and 'id_extraccion' in df_ext.columns:
                    df_ext = df_ext[df_ext['id_extraccion'] != id_nueva_ext]
                    try:
                        self.gestor.guardar_cambios_atomicos("extracciones", df_ext)
                    except Exception: pass
                
                # Devolvemos al donante a su estado anterior
                donante.ultima_donacion = ultima_donacion_previa
                donante.estado_elegibilidad = estado_elegibilidad_previo

                raise IOError(f"Tuvimos un problema guardando los archivos, se canceló el proceso: {e}")

        except ValueError as ve:
            return False, str(ve)
        except Exception as e:
            return False, f"Ocurrió un problema inesperado en el almacén: {e}"

    def registrar_estabilidad_post_donacion(self, id_extraccion: Any, complicaciones: list) -> Tuple[bool, str]:
        """Anota cómo se sintió el donante después de sacarle sangre. Si se mareó o se sintió mal, genera una alerta médica."""
        if not id_extraccion:
            return False, "Necesitamos el número de folio de la extracción."

        try:
            id_ext_int = int(id_extraccion)
            df_extracciones = self.gestor.leer_persistencias("extracciones")
            if df_extracciones is None or df_extracciones.empty or 'id_extraccion' not in df_extracciones.columns:
                return False, "No encontramos la base de datos de las extracciones."

            ids_seguros = pd.to_numeric(df_extracciones['id_extraccion'], errors='coerce').fillna(0).astype(int)
            mascara = ids_seguros == id_ext_int

            if not mascara.any():
                return False, f"El folio de extracción {id_ext_int} no existe en los registros."

            fila = df_extracciones[mascara].iloc[0]
            extraccion_obj = Extraccion(
                id_extraccion=int(fila['id_extraccion']),
                id_donante=int(fila['id_donante']),
                volumen_ml=int(fila['volumen_ml']),
                id_personal_responsable=int(fila['id_personal_responsable']),
                observaciones_clinicas=str(fila['observaciones_clinicas'])
            )

            es_estable = extraccion_obj.registrar_signos_vitales_post_donacion(complicaciones)
            df_extracciones['observaciones_clinicas'] = df_extracciones['observaciones_clinicas'].astype(object)

            df_extracciones.loc[mascara, 'observaciones_clinicas'] = extraccion_obj.observaciones_clinicas
            self.gestor.guardar_cambios_atomicos("extracciones", df_extracciones)

            if es_estable:
                self._registrar_auditoria(EntidadAfectada.DONANTE, f"Donante sin complicaciones (Extracción: {id_ext_int}).", NivelSeveridad.INFO)
                return True, "Revisión finalizada. El donante está estable y puede retirarse."
            else:
                self._registrar_auditoria(EntidadAfectada.DONANTE, f"Paciente con malestares (Ext {id_ext_int}): {extraccion_obj.observaciones_clinicas}", NivelSeveridad.ADVERTENCIA)
                return True, f"¡Atención! El paciente reportó molestias.\nNotas médicas: {extraccion_obj.observaciones_clinicas}"

        except Exception as e:
            return False, f"Ocurrió un problema técnico al registrar los signos vitales: {e}"

    # --- FRACCIONAMIENTO Y SEROLOGÍA ---

    def procesar_fraccionamiento(self, id_unidad: Any) -> Tuple[bool, str]:
        """
        Toma una bolsa de sangre entera y la "mete a la centrifugadora" en el sistema 
        para separarla en tres componentes nuevos: glóbulos rojos, plasma y plaquetas.
        """
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Laboratorista", "Administrador"]:
            return False, "Permiso denegado: Solo los laboratoristas pueden separar la sangre."

        try:
            id_u_int = int(id_unidad)
            unidad_madre = self.inventario.obtener_unidad_por_id(id_u_int)
            
            if not unidad_madre:
                return False, f"No tenemos la bolsa {id_u_int} guardada en el refrigerador."
            if not unidad_madre.verificar_viabilidad():
                return False, f"Aviso de seguridad: La bolsa {id_u_int} está caducada o ya se desechó."

            estado_original = unidad_madre.estado
            subcomponentes = unidad_madre.fraccionar_bolsa_madre()
            
            for sub_unidad in subcomponentes:
                self.inventario.ingresar_unidad(sub_unidad)
            # Quitamos la bolsa entera original porque ya se dividió
            self.inventario.unidades_disponibles.remove(unidad_madre)
            
            try:
                self.inventario.guardar_inventario_actualizado(self.gestor)
            except Exception as e_io:
                # Si no pudimos guardar los cambios, revertimos la separación
                for sub_unidad in subcomponentes:
                    if sub_unidad in self.inventario.unidades_disponibles:
                        self.inventario.unidades_disponibles.remove(sub_unidad)
                self.inventario.unidades_disponibles.append(unidad_madre)
                unidad_madre.estado = estado_original
                raise IOError(f"No pudimos guardar los componentes separados. Todo volvió a la normalidad: {e_io}")

            self._registrar_auditoria(EntidadAfectada.HEMOCOMPONENTE, f"La bolsa {id_u_int} fue separada en {len(subcomponentes)} componentes.", NivelSeveridad.INFO)
            return True, f"Proceso completado: La bolsa {id_u_int} se dividió correctamente."
            
        except ValueError as ve:
            return False, f"El proceso fue rechazado: {ve}"
        except Exception as e:
            return False, f"Error inesperado al intentar separar la sangre: {e}"

    def procesar_extraccion_crioprecipitado(self, id_unidad: Any) -> Tuple[bool, str]:
        """Toma una bolsa de plasma y la somete a un proceso de frío para crear crioprecipitados."""
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Laboratorista", "Administrador"]:
            return False, "Permiso denegado: Se requiere rol de Laboratorista."

        try:
            id_u_int = int(id_unidad)
            unidad_plasma = self.inventario.obtener_unidad_por_id(id_u_int)
            if not unidad_plasma:
                return False, f"La bolsa de plasma {id_u_int} no aparece en el inventario."

            estado_original = unidad_plasma.estado
            crio_unidad = unidad_plasma.extraer_crioprecipitado()
            self.inventario.ingresar_unidad(crio_unidad)
            
            try:
                self.inventario.guardar_inventario_actualizado(self.gestor)
            except Exception as e_io:
                if crio_unidad in self.inventario.unidades_disponibles:
                    self.inventario.unidades_disponibles.remove(crio_unidad)
                unidad_plasma.estado = estado_original
                raise IOError(f"No pudimos guardar el proceso. Los cambios se cancelaron: {e_io}")

            self._registrar_auditoria(EntidadAfectada.HEMOCOMPONENTE, f"Crioprecipitado {crio_unidad.id_unidad} sacado del plasma {id_u_int}.", NivelSeveridad.INFO)
            return True, f"¡Listo! Se extrajo el crioprecipitado {crio_unidad.id_unidad} y se metió al {crio_unidad.refrigerador_asignado}."

        except ValueError as ve:
            return False, f"El sistema rechazó la acción: {ve}"
        except Exception as e:
            return False, f"Hubo un error al extraer los crioprecipitados: {e}"

    def procesar_liberacion_unidad(self, id_unidad: Any, resultados_serologia: dict, password_confirmacion: str) -> Tuple[bool, str]:
        """
        Esta es la prueba de fuego de la sangre. Recibe los resultados de las pruebas de laboratorio 
        (VIH, Hepatitis, etc.). Si todo sale negativo, la bolsa se marca como 'Liberada' y ya se puede usar. 
        Si sale positiva a alguna enfermedad, se bloquea y lanza una alerta roja.
        """
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Laboratorista", "Administrador"]:
            return False, "Solo los laboratoristas pueden liberar o desechar sangre."

        if not self.usuario_actual.autenticar_operacion(password_confirmacion):
            return False, "Seguridad: Su contraseña no coincide."
            
        enfermedades = ['vih', 'hepatitis_b', 'hepatitis_c', 'sifilis', 'chagas']
        if not id_unidad or not all(k in resultados_serologia for k in enfermedades):
            return False, "Debe llenar los resultados de todas las pruebas médicas para poder continuar."

        try:
            id_u_int = int(id_unidad)
            unidad = self.inventario.obtener_unidad_por_id(id_u_int)
            if not unidad or unidad.estado != EstadoHemocomponente.EN_CUARENTENA:
                return False, "Esa bolsa no existe o no se encuentra en la zona de cuarentena."

            def _parse_reactivo(v): return str(v).strip().lower() in ("true", "1", "si", "sí", "positivo", "reactivo")
            
            estado_pre = unidad.estado
            prueba = PruebaLaboratorio(int(datetime.now().strftime("%H%M%S")), id_u_int, self.usuario_actual.id_global)
            prueba.registrar_resultados(
                vih=_parse_reactivo(resultados_serologia['vih']),
                hep_b=_parse_reactivo(resultados_serologia['hepatitis_b']),
                hep_c=_parse_reactivo(resultados_serologia['hepatitis_c']),
                sifilis=_parse_reactivo(resultados_serologia['sifilis']),
                chagas=_parse_reactivo(resultados_serologia['chagas'])
            )

            fue_liberada = unidad.liberar_por_serologia(prueba)
            
            if fue_liberada:
                msj = f"Pruebas limpias. La bolsa {id_u_int} ha sido LIBERADA para transfusiones."
                sev = NivelSeveridad.INFO
            else:
                # --- Sistema de alerta para enfermedades detectadas ---
                marcadores_positivos = [k.replace('_', ' ').title() for k, v in prueba.marcadores.items() if v]
                detalle_infeccion = ", ".join(marcadores_positivos) if marcadores_positivos else "Infección no especificada"
                msj = f"¡ALERTA MÉDICA ROJA! La bolsa {id_u_int} fue RECHAZADA. Salió positiva para: {detalle_infeccion}."
                # ------------------------------------------------------
                sev = NivelSeveridad.CRITICO

            try:
                self.inventario.guardar_inventario_actualizado(self.gestor)
            except Exception as e_io:
                unidad.estado = estado_pre
                return False, f"No pudimos guardar los resultados. El dictamen se canceló: {e_io}"

            self._registrar_auditoria(EntidadAfectada.HEMOCOMPONENTE, msj, sev)
            return True, msj
            
        except Exception as e:
            return False, f"Tuvimos un problema procesando las pruebas: {e}"

    # --- ALERTAS Y PREPARACIÓN DE DATOS PARA LAS TABLAS ---

    def verificar_alertas_stock(self) -> str:
        """
        Revisa cuántas bolsas tenemos listas para usar. Si tenemos menos del mínimo de seguridad 
        establecido, manda una alerta detallando qué grupos sanguíneos nos están faltando.
        """
        try:
            self.inventario.depurar_unidades_caducadas(self.gestor)
            resumen_stock = self.inventario.calcular_stock_dinamico()
            alertas = []
            
            if self.inventario.verificar_alertas_desabasto():
                alertas.append(f"¡ADVERTENCIA! Tenemos menos de {self.inventario.umbral_critico_seguridad} bolsas de sangre en total.\n")

            todos_los_grupos = [
                "Globulos Rojos A+", "Globulos Rojos A-", 
                "Globulos Rojos B+", "Globulos Rojos B-", 
                "Globulos Rojos AB+", "Globulos Rojos AB-", 
                "Globulos Rojos O+", "Globulos Rojos O-"
            ]

            for grupo in todos_los_grupos:
                cantidad = resumen_stock.get(grupo, 0)
                if cantidad < self.inventario.umbral_critico_seguridad:
                    nivel_alerta = "AGOTADO" if cantidad == 0 else "NIVEL BAJO"
                    alertas.append(f"[{nivel_alerta}] {grupo}: Solo quedan {cantidad} bolsas (Mínimo esperado: {self.inventario.umbral_critico_seguridad})")

            return "\n".join(alertas) if alertas else "El inventario del banco de sangre está en niveles excelentes."
        except Exception:
            return "Tuvimos un problema al calcular el resumen del inventario."
        
    def obtener_unidades_cuarentena(self) -> List[Dict[str, Any]]:
        """Prepara la información de las bolsas en espera de resultados para mostrarlas en la tabla de la ventana."""
        try:
            return [{"ID Unidad": u.id_unidad, "Componente": u.tipo_componente.value, "Tipo": f"{u.tipo_sangre}{u.factor_rh}", "Refrigerador": u.refrigerador_asignado} for u in self.inventario.unidades_disponibles if u.estado == EstadoHemocomponente.EN_CUARENTENA]
        except Exception: return []
        
    def obtener_inventario_general(self) -> List[Dict[str, Any]]:
        """Prepara la información de todo el almacén ordenando las bolsas desde la que caduca primero hasta la más nueva."""
        try:
            return [{"Folio": u.id_unidad, "Componente": u.tipo_componente.value, "Grupo": f"{u.tipo_sangre}{u.factor_rh}", "Caducidad": str(u.fecha_caducidad), "Estado": u.estado.value.title(), "Ubicación": u.refrigerador_asignado} for u in sorted(self.inventario.unidades_disponibles, key=lambda x: x.fecha_caducidad)]
        except Exception: return []

    def obtener_historial_extracciones_tabla(self) -> List[Dict[str, Any]]:
        """Acomoda la lista de las personas que han donado para que la interfaz pueda mostrar el historial completo."""
        try:
            df_ext = self.gestor.leer_persistencias("extracciones")
            if df_ext is None or df_ext.empty or 'id_extraccion' not in df_ext.columns: return []
                
            df_donantes = self.gestor.leer_persistencias("donantes")
            mapa_don = dict(zip(df_donantes['id_global'].dropna().astype(int), df_donantes['nombre'].dropna().astype(str))) if df_donantes is not None and not df_donantes.empty else {}

            historial = []
            # Leemos desde la extracción más reciente hasta la más antigua
            for _, fila in df_ext.iloc[::-1].iterrows():
                id_don = int(fila.get('id_donante', 0))
                historial.append({
                    "Folio": int(fila.get('id_extraccion', 0)),
                    "Donante": mapa_don.get(id_don, f"Donante Desconocido (ID: {id_don})"),
                    "Volumen (ml)": int(fila.get('volumen_ml', 0)),
                    "Fecha y Hora": str(fila.get('fecha_hora', 'No registrada')),
                    "Observaciones": str(fila.get('observaciones_clinicas', ''))
                })
            return historial
        except Exception: return []