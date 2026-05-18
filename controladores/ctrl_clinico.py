"""
Módulo del Controlador Clínico - BloodConnect
Este archivo es el "cerebro" del sistema. Se encarga de conectar la información 
de los pacientes, el inventario de sangre y los registros médicos para coordinar 
las transfusiones, manejar emergencias y registrar todo en la bitácora.
"""

import pandas as pd
from datetime import datetime, date
from typing import Tuple, List, Dict, Optional, Any

from clases.gestion_clinica import MotorCompatibilidad, TipoComponente, Transfusion, SolicitudMedica, NivelTriage
from clases.gestion_identidades import Donante, Trabajador, Paciente
from clases.red_interhospitalaria import Hospital, Transferencia, TipoMovimiento, EstadoLogistico
from clases.gestion_almacen import Inventario, EstadoHemocomponente, Hemocomponente, TipoHemocomponente
from clases.auditoria import GestorDatos, Bitacora, EntidadAfectada, NivelSeveridad

class CtrlClinico:
    def __init__(self, gestor: GestorDatos, inventario: Inventario):
        self.gestor = gestor
        self.inventario = inventario
        # Guarda al usuario que inició sesión para saber quién hace cada acción
        self.usuario_actual: Optional[Trabajador] = None

    def _registrar_auditoria(self, entidad: EntidadAfectada, accion: str, severidad: NivelSeveridad):
        """Guarda un registro de las acciones importantes en el archivo de texto para mantener un historial seguro."""
        try:
            id_usuario = self.usuario_actual.id_global if self.usuario_actual else 0
            id_log = int(datetime.now().strftime("%y%m%d%H%M%S")) 
            registro = Bitacora(id_log, id_usuario, entidad, accion, severidad)
            registro.escribir_entrada_inmutable(self.gestor.ruta_log)
        except Exception as e:
            # Mensaje en consola en caso de que el archivo de logs falle
            print(f"Aviso del sistema: No se pudo guardar el registro de auditoría. Detalle: {e}")

    def _asegurar_paciente_emergencia(self, id_paciente_str: str, grupo: str, rh: str) -> int:
        """
        En una emergencia, a veces no hay tiempo de registrar al paciente o no tiene identificación. 
        Esta función verifica si el paciente existe; si no, crea un perfil temporal (NN) para poder darle sangre de inmediato.
        """
        if id_paciente_str and id_paciente_str.strip():
            try:
                id_pac = int(id_paciente_str.strip())
                df_pac = self.gestor.leer_persistencias("pacientes")
                if df_pac is not None and id_pac in df_pac['id_paciente'].values:
                    return id_pac
            except ValueError:
                pass
                
        # Creación del paciente temporal usando la fecha actual como ID base
        id_global_temp = int(datetime.now().strftime("%y%m%d%H%M%S"))
        nuevo_paciente = Paciente(
            id_global=id_global_temp,
            nombre=f"URGENCIA NN {id_global_temp}",
            fecha_nacimiento="1990-01-01",
            genero="NO ESPECIFICADO",
            tipo_sangre=grupo,
            factor_rh=rh,
            id_paciente=id_global_temp,
            area_internamiento="Urgencias / Trauma",
            diagnostico_ingreso="Hemorragia Masiva (Código Rojo)",
            prioridad_clinica="Rojo"
        )
        nuevo_paciente.registrar_paciente(self.gestor)
        return id_global_temp

    # =========================================================================
    # RUTINA PROGRAMADA
    # =========================================================================
    def procesar_transfusion_rutina(self, id_paciente: Any, tipo_req: str, factor_req: str, unidades_requeridas: int = 1, tipo_componente: Any = "Globulos Rojos", prioridad: Any = "Verde") -> Tuple[bool, str]:
        """
        Maneja las solicitudes de sangre normales (programadas). 
        Verifica permisos, busca bolsas compatibles y las asigna usando la regla de usar primero las más próximas a caducar.
        """
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Médico", "Administrador"]:
            return False, "Permiso denegado: Se requiere rol de Médico o Administrador para solicitar sangre."

        try:
            id_pac_int = int(id_paciente)
            unidades_req_int = int(unidades_requeridas)
            tipo_componente_enum = TipoComponente(tipo_componente.strip().title()) if isinstance(tipo_componente, str) else tipo_componente
            prioridad_enum = NivelTriage[prioridad.strip().upper()] if isinstance(prioridad, str) else prioridad
        except Exception:
            return False, "Error: Los datos ingresados tienen un formato incorrecto."

        try:
            id_sol = int(datetime.now().strftime("%H%M%S"))
            paciente = Paciente.cargar_desde_csv(id_pac_int, self.gestor)
            if not paciente:
                return False, f"El paciente con el número de registro {id_pac_int} no fue encontrado."

            # --- Evaluar y registrar la prioridad de la solicitud ---
            solicitud = SolicitudMedica(id_sol, prioridad_enum, tipo_componente_enum.value, unidades_req_int, id_pac_int)
            aviso_triage = solicitud.clasificar_prioridad()
            self._registrar_auditoria(EntidadAfectada.PACIENTE, aviso_triage, NivelSeveridad.INFO)
            # --------------------------------------------------------

            # Buscar unidades compatibles en el inventario y ordenarlas por fecha de caducidad
            motor = MotorCompatibilidad()
            unidades_aptas = motor.ejecutar_smart_matching(tipo_req, factor_req, tipo_componente_enum, self.inventario.unidades_disponibles)
            unidades_liberadas = motor.aplicar_logica_fifo([u for u in unidades_aptas if u.estado == EstadoHemocomponente.LIBERADA])

            if len(unidades_liberadas) < unidades_req_int:
                return False, f"Inventario insuficiente: Pide {unidades_req_int} bolsas, pero solo tenemos {len(unidades_liberadas)} compatibles."
            
            # Tomar solo las unidades necesarias y procesar la salida
            unidades_elegidas = unidades_liberadas[:unidades_req_int]
            return self._ejecutar_transaccion_atomica(paciente, unidades_elegidas, id_sol, False)

        except Exception as e:
            return False, f"Ocurrió un error al procesar la solicitud de rutina: {e}"

    # =========================================================================
    # EMERGENCIA (CÓDIGO ROJO)
    # =========================================================================
    def procesar_emergencia_primaria(self, id_paciente_str: str, unidades_requeridas: int) -> Tuple[bool, str, str]:
        """
        Acción rápida para emergencias extremas. 
        Salta procesos burocráticos y despacha de inmediato sangre universal (O negativo).
        """
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Médico", "Administrador", "Enfermero", "Laboratorista"]:
            return False, "DENIED", "Su usuario no tiene permisos para autorizar sangre en emergencias."

        try:
            unidades_req_int = int(unidades_requeridas)
        except ValueError:
            return False, "ERROR", "La cantidad de unidades debe ser un número entero."

        try:
            id_pac_real = self._asegurar_paciente_emergencia(id_paciente_str, "O", "-")
            id_sol = int(datetime.now().strftime("%H%M%S"))

            # --- Verificación rápida para saber si tenemos O negativo suficiente ---
            solicitud_urgente = SolicitudMedica(id_sol, NivelTriage.ROJO, TipoComponente.GLOBULOS_ROJOS.value, unidades_req_int, id_pac_real)
            alerta_codigo_rojo = solicitud_urgente.clasificar_prioridad()
            self._registrar_auditoria(EntidadAfectada.SISTEMA, alerta_codigo_rojo, NivelSeveridad.CRITICO)

            if not solicitud_urgente.validar_stock_emergencia(self.inventario.unidades_disponibles):
                return False, "REQUIERE_FALLBACK", f"Aviso de almacén: No hay suficiente sangre O- para cubrir las {unidades_req_int} bolsas pedidas."
            # -----------------------------------------------------------------------

            # Filtrar exclusivamente bolsas tipo O Negativo que estén listas para usar
            motor = MotorCompatibilidad()
            unidades_univ = [u for u in self.inventario.unidades_disponibles if u.tipo_sangre == "O" and u.factor_rh == "-" and u.tipo_componente == TipoHemocomponente.GLOBULOS_ROJOS and u.estado == EstadoHemocomponente.LIBERADA]
            unidades_liberadas = motor.aplicar_logica_fifo(unidades_univ)

            paciente = Paciente.cargar_desde_csv(id_pac_real, self.gestor)
            unidades_elegidas = unidades_liberadas[:unidades_req_int]
            
            exito, msj = self._ejecutar_transaccion_atomica(paciente, unidades_elegidas, id_sol, True)
            return exito, "SUCCESS", msj

        except Exception as e:
            return False, "ERROR", f"Fallo en el proceso de emergencia: {e}"

    def procesar_emergencia_fallback(self, id_paciente_str: str, grupo: str, rh: str, unidades_requeridas: int) -> Tuple[bool, str, str]:
        """
        Plan B para emergencias: Si nos quedamos sin sangre O negativo, esta función 
        intenta despachar el tipo de sangre exacto del paciente.
        """
        try:
            unidades_req_int = int(unidades_requeridas)
            motor = MotorCompatibilidad()
            aptas = motor.ejecutar_smart_matching(grupo, rh, TipoComponente.GLOBULOS_ROJOS, self.inventario.unidades_disponibles)
            liberadas = motor.aplicar_logica_fifo([u for u in aptas if u.estado == EstadoHemocomponente.LIBERADA])

            if len(liberadas) == 0:
                return False, "FAIL", f"Alerta Crítica: No hay sangre O- ni sangre tipo {grupo}{rh} en el refrigerador."

            # En una emergencia, entregamos lo que haya disponible aunque no cubra el total pedido
            unidades_elegidas = liberadas[:unidades_req_int]
            id_pac_real = self._asegurar_paciente_emergencia(id_paciente_str, grupo, rh)
            paciente = Paciente.cargar_desde_csv(id_pac_real, self.gestor)
            
            id_sol = int(datetime.now().strftime("%H%M%S"))
            exito, msj = self._ejecutar_transaccion_atomica(paciente, unidades_elegidas, id_sol, True)
            
            if len(unidades_elegidas) < unidades_req_int:
                msj = f"ENTREGA INCOMPLETA DE EMERGENCIA: Se solicitaron {unidades_req_int} pero solo se entregaron {len(unidades_elegidas)}.\n\n" + msj
                
            return exito, "SUCCESS", msj

        except Exception as e:
            return False, "ERROR", f"Error al intentar buscar sangre alternativa: {e}"

    def procesar_baja_retrospectiva(self, ids_str: str, password_firma: str) -> Tuple[bool, str]:
        """
        Registra en el sistema las bolsas que fueron sacadas corriendo del refrigerador 
        durante una crisis, para cuadrar el inventario una vez que la emergencia pasó.
        """
        if not self.usuario_actual or not self.usuario_actual.autenticar_operacion(password_firma):
            return False, "Su contraseña médica es incorrecta."

        if not ids_str.strip():
            return False, "Debe ingresar al menos el número de una bolsa."

        try:
            lista_ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
            unidades_elegidas = []
            
            for uid in lista_ids:
                unidad = self.inventario.obtener_unidad_por_id(uid)
                if not unidad:
                    return False, f"La bolsa número {uid} no está en nuestro almacén activo."
                if unidad.estado != EstadoHemocomponente.LIBERADA:
                    return False, f"Alerta de Seguridad: La bolsa {uid} no estaba lista para usarse (Estado: {unidad.estado.value})."
                unidades_elegidas.append(unidad)

            # Asignamos estas salidas al paciente temporal
            id_pac_retro = self._asegurar_paciente_emergencia("", "N/A", "")
            paciente = Paciente.cargar_desde_csv(id_pac_retro, self.gestor)
            
            id_sol = int(datetime.now().strftime("%H%M%S"))
            return self._ejecutar_transaccion_atomica(paciente, unidades_elegidas, id_sol, True, es_retrospectivo=True)

        except ValueError:
            return False, "El formato no es válido. Escriba los números separados por comas."
        except Exception as e:
            return False, f"Error al registrar la salida retroactiva: {e}"

    # =========================================================================
    # GUARDADO SEGURO DE DATOS
    # =========================================================================
    def _ejecutar_transaccion_atomica(self, paciente: Paciente, unidades_elegidas: list, id_sol: int, es_emergencia: bool, es_retrospectivo: bool = False) -> Tuple[bool, str]:
        """
        Función de "Todo o Nada". Intenta registrar la transfusión completa; si ocurre algún error, 
        deshace todos los cambios temporales para evitar que el paciente o el inventario queden con datos a medias.
        """
        unidades_procesadas_ok = []
        # Guardamos una foto de cómo estaban las bolsas antes de empezar por si hay que revertir cambios
        snapshot_estados = {u.id_unidad: u.estado for u in unidades_elegidas}
        historial_previo = list(paciente.historial_transfusiones)
        id_medico = self.usuario_actual.id_global

        try:
            for unidad in unidades_elegidas:
                timestamp_str = datetime.now().strftime("%H%M%S")
                id_trans_temporal = abs(hash(f"{timestamp_str}-{unidad.id_unidad}")) % (10 ** 14)
                
                nueva_transfusion = Transfusion(id_trans_temporal, unidad.id_unidad, paciente.id_paciente, id_medico, "Ninguna", datetime.now())

                # --- Verificación final de seguridad antes de autorizar ---
                if not nueva_transfusion.registrar_evento_vena_a_vena(paciente, unidad):
                    motivo_fallo = nueva_transfusion.estado_transfusion.value
                    self._registrar_auditoria(EntidadAfectada.PACIENTE, f"Cuidado al paciente: Cancelada la transfusión de la bolsa {unidad.id_unidad}. Causa: {motivo_fallo}", NivelSeveridad.CRITICO)
                    raise RuntimeError(f"Falla al cruzar datos para la bolsa {unidad.id_unidad}. Detalle: {motivo_fallo}")
                # ----------------------------------------------------------

                nueva_transfusion.registrar_transfusion(self.gestor)
                unidades_procesadas_ok.append(unidad)

            # Si todo salió bien, guardamos definitivamente en los archivos
            self.inventario.guardar_inventario_actualizado(self.gestor)
            paciente.registrar_paciente(self.gestor)
            
            ids_str = ", ".join([str(u.id_unidad) for u in unidades_procesadas_ok])
            detalle_ubicaciones = "\n".join([f"Bolsa: {u.id_unidad} ➔ En: {u.refrigerador_asignado}" for u in unidades_procesadas_ok])
            
            alerta_audit = f"Se completó la solicitud (Folio: {id_sol}) con las bolsas: {ids_str}"
            if es_emergencia: alerta_audit = f"URGENCIA DESPACHADA: {alerta_audit}"
            if es_retrospectivo: alerta_audit += " (Registro posterior a la emergencia)"
                
            self._registrar_auditoria(EntidadAfectada.PACIENTE, alerta_audit, NivelSeveridad.CRITICO)
            
            msj_final = f"Transfusión exitosa: {len(unidades_procesadas_ok)} bolsas asignadas a {paciente.nombre}."
            if not es_retrospectivo:
                msj_final += f"\n\nPuede pasar a recogerlas a:\n{detalle_ubicaciones}"
                
            return True, msj_final

        except Exception as e_transaccional:
            # Reversión de cambios (Rollback): Regresamos todo a su estado original
            for u in unidades_elegidas:
                u.estado = snapshot_estados[u.id_unidad]
            paciente.historial_transfusiones = historial_previo
            self.inventario.guardar_inventario_actualizado(self.gestor)
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Cambios revertidos: Hubo un problema en la solicitud {id_sol}. Error: {e_transaccional}", NivelSeveridad.CRITICO)
            return False, f"Se canceló el proceso para proteger los datos. Causa: {e_transaccional}"

    # =========================================================================
    # REACCIONES ADVERSAS Y RED EXTERNA
    # =========================================================================
    def registrar_reaccion_adversa_transfusion(self, id_transfusion: Any, id_donante: Any, notas: str) -> Tuple[bool, str]:
        """
        Si un paciente se siente mal por la transfusión, anota los síntomas y 
        bloquea inmediatamente al donante de esa sangre para evitar riesgos futuros.
        """
        if not id_transfusion or not notas or not notas.strip(): 
            return False, "Por favor ingrese el número de transfusión y las notas del médico."
        
        try:
            id_t = int(str(id_transfusion).strip())
            df_t = self.gestor.leer_persistencias("transfusiones")
            
            if df_t is None or df_t.empty: 
                return False, "La base de datos está vacía."
                
            mascara = pd.to_numeric(df_t['id_transfusion'], errors='coerce').fillna(0).astype(int) == id_t
            if not mascara.any(): 
                return False, "No encontramos ese folio de transfusión."
                
            # Actualizamos el registro de la transfusión con las notas médicas
            df_t.loc[mascara, 'reacciones_adversas'] = notas.strip().capitalize()
            self.gestor.guardar_cambios_atomicos("transfusiones", df_t)
            
            # --- Buscar y bloquear al donante causante ---
            try:
                id_d = int(str(id_donante).strip())
                donante = Donante.cargar_desde_csv(id_d, self.gestor)
                t_obj = Transfusion(id_t, int(df_t[mascara].iloc[0]['id_unidad']), int(df_t[mascara].iloc[0]['id_paciente']), 1, notas.strip(), datetime.now())
                
                if donante and t_obj.bloquear_donante_por_reaccion(donante):
                    donante.registrar_donante(self.gestor)
                    self._registrar_auditoria(EntidadAfectada.DONANTE, f"Por seguridad, el donante {donante.nombre} fue bloqueado. Razón médica: {notas}", NivelSeveridad.CRITICO)
                    return True, f"Reporte guardado correctamente.\nEl donante {donante.nombre} no podrá volver a donar."
            except ValueError:
                # Caso en que no conocemos al donante (por ejemplo, sangre traída de otro lado)
                return True, "Reporte guardado con éxito.\n(Aviso: No bloqueamos al donante porque su registro no aparece en nuestro sistema local)."
                
            return True, "Reporte guardado. No fue necesario bloquear al donante."
        except Exception as e: 
            return False, str(e)
            
    def obtener_donante_origen_por_unidad(self, id_entrada: Any) -> str:
        """
        Rastrea una bolsa de sangre hacia atrás hasta descubrir quién fue la persona que la donó.
        """
        try:
            def _limpiar_numero(valor):
                try:
                    return str(int(float(valor)))
                except:
                    return str(valor).split('.')[0].strip()

            id_str = _limpiar_numero(id_entrada)
            if not id_str or id_str == "0" or id_str == "nan":
                return "No encontrado"

            id_unidad_fisica = id_str

            # Buscar si el número ingresado es un folio de transfusión
            df_trans = self.gestor.leer_persistencias("transfusiones")
            if df_trans is not None and not df_trans.empty:
                for _, fila in df_trans.iterrows():
                    folio_t = _limpiar_numero(fila.get('id_transfusion', ''))
                    if folio_t == id_str:
                        id_unidad_fisica = _limpiar_numero(fila.get('id_unidad', ''))
                        break

            # Determinar el ID base (madre) quitando el último dígito
            raiz_buscar = id_unidad_fisica[:-1] if len(id_unidad_fisica) >= 2 else id_unidad_fisica

            # Buscar en el historial de cuando se extrajo la sangre
            df_ext = self.gestor.leer_persistencias("extracciones")
            if df_ext is None or df_ext.empty:
                return "No encontrado"

            for _, fila in df_ext.iterrows():
                folio_ext = _limpiar_numero(fila.get('id_extraccion', ''))
                id_donante_encontrado = _limpiar_numero(fila.get('id_donante', ''))
                
                if folio_ext == id_unidad_fisica or folio_ext.startswith(raiz_buscar):
                    return id_donante_encontrado

            return "No encontrado"
            
        except Exception as e:
            print(f"Problema al intentar rastrear la bolsa: {e}")
            return "No encontrado"
        
    def procesar_devolucion_quirofano(self, id_unidad: Any, cadena_frio_intacta: bool, password_medico: str) -> Tuple[bool, str]:
        """
        Maneja la devolución de una bolsa que no se usó en cirugía. 
        Si se calentó (perdió cadena de frío), se va a la basura por norma de salubridad.
        """
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Médico", "Administrador"]: return False, "No tiene permisos para esto."
        if not self.usuario_actual.autenticar_operacion(password_medico): return False, "Contraseña médica incorrecta."
        try:
            id_u = int(id_unidad)
            unidad = self.inventario.obtener_unidad_por_id(id_u)
            if not unidad:
                df = self.gestor.leer_persistencias("inventario")
                f = df[df['id_unidad'] == id_u] if df is not None else pd.DataFrame()
                if not f.empty:
                    p = str(f.iloc[0]['fecha_caducidad']).split('-')
                    unidad = Hemocomponente(int(f.iloc[0]['id_unidad']), TipoHemocomponente(f.iloc[0]['tipo_componente']), str(f.iloc[0]['tipo_sangre']), str(f.iloc[0]['factor_rh']), date(int(p[0]),int(p[1]),int(p[2])), float(f.iloc[0]['temperatura_almacenamiento']), EstadoHemocomponente(f.iloc[0]['estado']), str(f.iloc[0]['refrigerador_asignado']))
                    self.inventario.unidades_disponibles.append(unidad)
            if not unidad: return False, "No pudimos encontrar esa unidad."
            
            # Verificación de la temperatura
            if cadena_frio_intacta:
                unidad.estado = EstadoHemocomponente.LIBERADA; msj = "Bolsa reingresada al inventario (Temperatura correcta)."
            else:
                unidad.estado = EstadoHemocomponente.DESECHADA; msj = "BOLSA DESECHADA: Peligro biológico por pérdida de refrigeración."
            self.inventario.guardar_inventario_actualizado(self.gestor)
            return True, msj
        except Exception as e: return False, str(e)

    def buscar_stock_en_red(self, id_clues: str, nombre_hospital: str, ruta_csv: str, tipo_componente: str, tipo_sangre: str, factor_rh: str) -> Tuple[bool, Any]:
        """Consulta si algún hospital aliado tiene la sangre que necesitamos."""
        try:
            unidades = Hospital(id_clues, nombre_hospital, ruta_csv).consultar_inventario_externo(tipo_componente, tipo_sangre, factor_rh)
            return (True, unidades) if unidades else (False, "El hospital aliado no cuenta con stock disponible.")
        except Exception as e: return False, str(e)
        
    def procesar_ingreso_externo(self, id_envio: int, id_clues: str, nombre_hospital: str, ruta_csv: str, unidades_a_ingresar: list) -> Tuple[bool, str]:
        """Registra las bolsas que nos llegan en ambulancia desde otra clínica."""
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Laboratorista", "Administrador"]: return False, "Permiso denegado para recibir paquetes foráneos."
        try:
            logistica = Transferencia(id_envio, Hospital(id_clues, nombre_hospital, ruta_csv), TipoMovimiento.ENTRADA)
            if logistica.registrar_recepcion_externa(unidades_a_ingresar, self.inventario, self.gestor): return True, logistica.generar_guia_transporte_biologico()
            return False, "Hubo un error al ingresar las bolsas al sistema."
        except Exception as e: return False, str(e)
        
    def procesar_envio_externo(self, id_envio: int, id_clues: str, nombre_hospital: str, ruta_csv: str, ids_unidades_a_enviar: List[int]) -> Tuple[bool, str]:
        """Gestiona la salida de sangre para apoyar a otro hospital y descuenta las bolsas del refri."""
        if not self.usuario_actual or self.usuario_actual.rol.strip().title() not in ["Laboratorista", "Administrador"]: return False, "Permiso denegado para enviar paquetes."
        try:
            logistica = Transferencia(id_envio, Hospital(id_clues, nombre_hospital, ruta_csv), TipoMovimiento.SALIDA)
            uds = []
            for id_u in ids_unidades_a_enviar:
                u = self.inventario.obtener_unidad_por_id(id_u)
                if not u or u.estado != EstadoHemocomponente.LIBERADA: return False, f"Atención: La unidad {id_u} no está lista o tiene problemas."
                uds.append(u)
            for u in uds:
                self.inventario.unidades_disponibles.remove(u); logistica.unidades_a_transferir.append(u)
            
            # --- Actualizar estatus de transporte ---
            logistica.estado_logistico = EstadoLogistico.EN_TRANSITO
            self.inventario.guardar_inventario_actualizado(self.gestor)
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Traslado de apoyo: Paquete {id_envio} está ahora en camino ({logistica.estado_logistico.value}).", NivelSeveridad.INFO)
            # ----------------------------------------

            return True, logistica.generar_guia_transporte_biologico()
        except Exception as e: return False, str(e)

    def obtener_historial_transfusiones_tabla(self) -> List[Dict[str, Any]]:
        """Prepara la lista de todas las transfusiones pasadas para mostrarla ordenada en una tabla."""
        try:
            df = self.gestor.leer_persistencias("transfusiones")
            if df is None or df.empty: return []
            df_p = self.gestor.leer_persistencias("pacientes")
            mapa = dict(zip(df_p['id_paciente'].dropna().astype(int), df_p['nombre'].dropna().astype(str))) if df_p is not None else {}
            h = []
            # Recorrer de la más reciente a la más antigua
            for _, r in df.iloc[::-1].iterrows():
                h.append({"Folio Transfusión": int(r.get('id_transfusion', 0)), "Unidad Despachada": int(r.get('id_unidad', 0)), "Paciente Receptor": mapa.get(int(r.get('id_paciente', 0)), "Paciente Desconocido"), "Fecha y Hora": str(r.get('timestamp_inicio', 'N/A')), "Reacción Adversa": str(r.get('reacciones_adversas', 'Ninguna'))})
            return h
        except Exception: return []