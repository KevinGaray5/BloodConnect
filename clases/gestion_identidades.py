"""
Módulo de Gestión de Identidades - BloodConnect
Este archivo define a todas las personas que interactúan con el sistema: Donantes, Pacientes y Trabajadores.
Utilizamos herencia (POO) creando una clase padre llamada "Persona" para que todos compartan 
los datos básicos (como nombre o tipo de sangre), manteniendo el código ordenado y sin repeticiones.
"""

from datetime import datetime, date
import pandas as pd
import bcrypt


class Persona:
    """
    Clase base (padre) que agrupa los datos comunes de cualquier individuo en el hospital.
    Sirve como molde para crear perfiles más específicos más adelante.
    """
    
    def __init__(self, id_global: int, nombre: str, fecha_nacimiento: str, genero: str, tipo_sangre: str, factor_rh: str):
        self.id_global = id_global
        self.nombre = nombre.strip().title()
        self.fecha_nacimiento = fecha_nacimiento
        self.genero = genero.strip().upper()
        
        self.tipo_sangre = tipo_sangre
        self.factor_rh = factor_rh

    @property
    def tipo_sangre(self) -> str:
        return self._tipo_sangre

    @tipo_sangre.setter
    def tipo_sangre(self, valor: str):
        # Limpiamos el texto para evitar que espacios extra o minúsculas generen un error
        valor_limpio = valor.strip().upper() if valor else "N/A"
        if valor_limpio not in ["A", "B", "AB", "O", "N/A"]:
            raise ValueError(f"Error en datos: El grupo sanguíneo '{valor}' no es válido. Por favor usa A, B, AB u O.")
        self._tipo_sangre = valor_limpio

    @property
    def factor_rh(self) -> str:
        return self._factor_rh

    @factor_rh.setter
    def factor_rh(self, valor: str):
        valor_limpio = valor.strip() if valor else ""
        if valor_limpio not in ["+", "-", ""]:
            raise ValueError(f"Error en datos: El factor RH '{valor}' no se reconoce. Escribe '+' o '-'.")
        self._factor_rh = valor_limpio

    @property
    def edad(self) -> int:
        """
        Calcula la edad exacta de la persona al día de hoy, basándose en su fecha de nacimiento.
        
        Retorna:
            int: La edad en años enteros.
        """
        try:
            # Convertimos el texto de la fecha a un formato con el que Python pueda hacer operaciones matemáticas
            fecha_nac = datetime.strptime(self.fecha_nacimiento, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Aviso del sistema: La fecha '{self.fecha_nacimiento}' tiene un formato incorrecto. Usa Año-Mes-Día (YYYY-MM-DD).")
            
        hoy = datetime.now()
        # Restamos los años y ajustamos si la persona aún no ha cumplido años en el año en curso
        return hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))

    def obtener_perfil_biologico(self) -> str:
        """
        Crea un pequeño resumen de texto con la información médica más importante, 
        listo para mostrarse rápidamente en la pantalla.
        """
        if self.tipo_sangre == "N/A":
            alerta_sangre = "[FALTA REGISTRAR TIPO DE SANGRE]"
        else:
            alerta_sangre = f"{self.tipo_sangre}{self.factor_rh}"

        return f"Expediente Clínico: {self.nombre} | Edad: {self.edad} años | Perfil Sanguíneo: {alerta_sangre}"


class Donante(Persona):
    """
    Representa a una persona que viene a donar sangre. 
    Hereda de 'Persona', pero incluye validaciones médicas (como peso y hemoglobina) 
    para asegurar que la donación no ponga en riesgo su salud.
    """
    
    def __init__(self, id_global: int, nombre: str, fecha_nacimiento: str, genero: str, tipo_sangre: str, factor_rh: str, ultima_donacion: date, tipo_donante: str, peso_kg: float, hemoglobina: float, contacto: str):
        super().__init__(id_global, nombre, fecha_nacimiento, genero, tipo_sangre, factor_rh)
        
        self.ultima_donacion = ultima_donacion
        self.tipo_donante = tipo_donante
        self.contacto = contacto
        
        self._estado_elegibilidad = False 
        self.peso_kg = peso_kg         
        self.hemoglobina = hemoglobina 

    @property
    def peso_kg(self) -> float:
        return self._peso_kg

    @peso_kg.setter
    def peso_kg(self, valor: float):
        if valor <= 0:
            raise ValueError(f"Alerta médica: El peso ingresado ({valor} kg) no es válido.")
        self._peso_kg = valor

    @property
    def hemoglobina(self) -> float:
        return self._hemoglobina

    @hemoglobina.setter
    def hemoglobina(self, valor: float):
        if valor < 0 or valor > 30: 
            raise ValueError(f"Alerta médica: El nivel de hemoglobina ({valor} g/dL) está fuera de los límites posibles.")
        self._hemoglobina = valor

    @property
    def estado_elegibilidad(self) -> bool:
        return self._estado_elegibilidad

    @estado_elegibilidad.setter
    def estado_elegibilidad(self, valor: bool):
        if not isinstance(valor, bool):
            raise TypeError("Error del sistema: El estado de elegibilidad debe ser estrictamente Verdadero o Falso.")
        self._estado_elegibilidad = valor
        
    @classmethod
    def obtener_todos_los_donantes(cls, gestor_datos) -> list:
        """
        Le pide al gestor de archivos la lista completa de donantes 
        para poder mostrarla en las tablas de la interfaz gráfica.
        """
        df_donantes = gestor_datos.leer_persistencias("donantes")
        
        if df_donantes is not None and not df_donantes.empty:
            # Rellenamos los huecos vacíos para que el programa no colapse al intentar leer celdas sin datos
            df_limpio = df_donantes.fillna("") 
            return df_limpio.to_dict('records')
        
        return []

    @classmethod
    def cargar_desde_csv(cls, id_buscado: int, gestor_datos):
        """
        Busca a un donante específico por su ID y reconstruye su perfil en el programa.
        Incluye protecciones para evitar que datos corruptos en el archivo detengan el sistema.
        """
        df_donantes = gestor_datos.leer_persistencias("donantes")
        
        if df_donantes is not None and not df_donantes.empty:
            filtro = df_donantes[df_donantes['id_global'] == id_buscado]
            
            if not filtro.empty:
                datos = filtro.iloc[0]
                ultima_don = datos.get('ultima_donacion')
                
                # Manejamos los casos donde la fecha viene vacía o dañada desde el archivo
                if pd.isna(ultima_don) or not str(ultima_don).strip():
                    fecha_ultima = None
                else:
                    try:
                        partes = str(ultima_don).split('-')
                        fecha_ultima = date(int(partes[0]), int(partes[1]), int(partes[2]))
                    except (ValueError, IndexError):
                        fecha_ultima = None

                donante_obj = cls(
                    id_global=datos['id_global'],
                    nombre=datos['nombre'],
                    fecha_nacimiento=datos['fecha_nacimiento'],
                    genero=datos['genero'],
                    tipo_sangre=datos['tipo_sangre'],
                    factor_rh=datos['factor_rh'],
                    ultima_donacion=fecha_ultima,
                    tipo_donante=datos.get('tipo_donante', 'Altruista'),
                    peso_kg=datos.get('peso_kg', 50.0),
                    hemoglobina=datos.get('hemoglobina', 14.0),
                    contacto=datos.get('contacto', 'Sin contacto')
                )

                # Evitamos que Pandas confunda una celda vacía con un valor falso o verdadero
                try:
                    estado_csv = datos.get('estado_elegibilidad', False)
                    
                    if pd.isna(estado_csv):
                        donante_obj.estado_elegibilidad = False
                    elif isinstance(estado_csv, str):
                        donante_obj.estado_elegibilidad = estado_csv.strip().lower() in ('true', '1', 'sí', 'si')
                    else:
                        donante_obj.estado_elegibilidad = bool(estado_csv)
                except (TypeError, ValueError):
                    donante_obj.estado_elegibilidad = False
                
                return donante_obj
                    
        return None

    def verificar_intervalo(self) -> bool:
        """
        Revisa que hayan pasado al menos 56 días desde la última donación. 
        Si el donante viene antes de tiempo, el sistema lo rechaza para protegerlo.
        """
        if not self.ultima_donacion:
            return True
            
        hoy = date.today()
        diferencia = hoy - self.ultima_donacion
        dias_pasados = diferencia.days
        
        if dias_pasados >= 56:
            return True
        else:
            dias_faltantes = 56 - dias_pasados
            self.estado_elegibilidad = False
            raise ValueError(f"Por protocolo médico, el donante {self.nombre} debe esperar {dias_faltantes} días más para volver a donar.")

    def evaluar_signos_vitales(self, ta_sistolica: int, ta_diastolica: int, frec_cardiaca: int) -> bool:
        """
        Comprueba que la presión arterial y el pulso estén dentro de un rango seguro 
        antes de proceder con la extracción de sangre.
        """
        if not (90 <= ta_sistolica <= 180) or not (50 <= ta_diastolica <= 100):
            raise ValueError(f"Rechazo clínico: La presión arterial ({ta_sistolica}/{ta_diastolica}) no es segura para donar.")
            
        if not (50 <= frec_cardiaca <= 100):
            raise ValueError(f"Rechazo clínico: La frecuencia cardíaca ({frec_cardiaca} lpm) está fuera de los límites permitidos.")
            
        return True

    def validar_cuestionario_pretriaje(self, respuestas_cuestionario: dict, ta_sistolica: int = 120, ta_diastolica: int = 80, frec_cardiaca: int = 75) -> bool:
        """
        Analiza las respuestas del donante y sus signos vitales para decidir 
        si es seguro que done sangre, siguiendo las normas oficiales de salud.
        """
        self.estado_elegibilidad = False 
        
        # Validaciones de la norma de salud (NOM)
        if self.edad < 18 or self.edad > 65:
            raise ValueError(f"Aviso legal: Por su edad ({self.edad} años), no cumple los requisitos para donar (18-65 años).")

        if self.peso_kg < 50.0:
            raise ValueError(f"Aviso médico: El peso mínimo para donar es de 50 kg (Registrado: {self.peso_kg} kg).")
            
        # Revisamos la presión y el pulso
        self.evaluar_signos_vitales(ta_sistolica, ta_diastolica, frec_cardiaca)

        # La cantidad mínima de hemoglobina varía un poco entre hombres y mujeres
        min_hemo = 13.5 if self.genero.upper() in ["MASCULINO", "M", "HOMBRE"] else 12.5
        if self.hemoglobina < min_hemo:
            raise ValueError(f"Aviso médico: Su nivel de hemoglobina es bajo ({self.hemoglobina} g/dL). El mínimo requerido es {min_hemo} g/dL.")

        # Revisamos factores de riesgo en su historial reciente
        if str(respuestas_cuestionario.get("tatuaje_ultimos_12_meses", "No")).lower() in ["si", "sí", "true"]:
            raise ValueError("Rechazo temporal: Por seguridad, debe esperar 12 meses después de realizarse un tatuaje o perforación.")
            
        if str(respuestas_cuestionario.get("infeccion_reciente", "No")).lower() in ["si", "sí", "true"]:
            raise ValueError("Rechazo temporal: No puede donar si tiene una infección activa o tomó antibióticos recientemente.")

        if str(respuestas_cuestionario.get("cirugia_reciente", "No")).lower() in ["si", "sí", "true"]:
            raise ValueError("Rechazo temporal: No se permite la donación si está en recuperación de una cirugía reciente.")

        if str(respuestas_cuestionario.get("embarazo_lactancia", "No")).lower() in ["si", "sí", "true"]:
            raise ValueError("Rechazo temporal: No es posible donar durante el embarazo o periodo de lactancia.")

        # Por último, verificamos que no haya donado hace muy poco tiempo
        self.verificar_intervalo()

        self.estado_elegibilidad = True
        return True

    def registrar_donante(self, gestor_datos):
        """
        Guarda o actualiza la información del donante en los archivos del sistema.
        Se asegura de que las fechas y los datos se guarden correctamente para que Pandas no falle.
        """
        df_donantes = gestor_datos.leer_persistencias("donantes")
        
        # Nos aseguramos de convertir la fecha en un texto simple para evitar problemas al guardarlo
        fecha_str = ""
        if self.ultima_donacion:
            if isinstance(self.ultima_donacion, date):
                fecha_str = self.ultima_donacion.strftime("%Y-%m-%d")
            else:
                fecha_str = str(self.ultima_donacion).strip()
                
        if df_donantes is not None:
            # Si el donante ya existía, buscamos su fila y actualizamos su información
            if not df_donantes.empty and 'id_global' in df_donantes.columns and self.id_global in df_donantes['id_global'].values:
                mascara = df_donantes['id_global'] == self.id_global
                
                df_donantes.loc[mascara, 'nombre'] = self.nombre
                df_donantes.loc[mascara, 'tipo_sangre'] = self.tipo_sangre
                df_donantes.loc[mascara, 'factor_rh'] = self.factor_rh
                
                df_donantes.loc[mascara, 'contacto'] = self.contacto
                df_donantes.loc[mascara, 'ultima_donacion'] = fecha_str 
                df_donantes.loc[mascara, 'peso_kg'] = self.peso_kg
                df_donantes.loc[mascara, 'hemoglobina'] = self.hemoglobina
                df_donantes.loc[mascara, 'estado_elegibilidad'] = self.estado_elegibilidad
                
            # Si es un donante nuevo, creamos su registro y lo agregamos al archivo
            else:
                nuevo_registro = {
                    'id_global': self.id_global,
                    'nombre': self.nombre,
                    'fecha_nacimiento': self.fecha_nacimiento,
                    'genero': self.genero,
                    'tipo_sangre': self.tipo_sangre,
                    'factor_rh': self.factor_rh,
                    'ultima_donacion': fecha_str, 
                    'tipo_donante': self.tipo_donante,
                    'peso_kg': self.peso_kg,
                    'hemoglobina': self.hemoglobina,
                    'contacto': self.contacto,
                    'estado_elegibilidad': self.estado_elegibilidad
                }
                
                df_nuevo = pd.DataFrame([nuevo_registro])
                df_donantes = pd.concat([df_donantes, df_nuevo], ignore_index=True)

            # Enviamos los cambios para que se guarden en el CSV
            gestor_datos.guardar_cambios_atomicos("donantes", df_donantes)
        else:
            raise RuntimeError("Fallo crítico del sistema: No pudimos acceder al archivo de donantes.")

class Paciente(Persona):
    """
    Representa a la persona internada que necesita recibir sangre.
    Hereda de 'Persona' y añade una lista para recordar exactamente qué bolsas 
    de sangre se le han puesto, asegurando una trazabilidad completa.
    """
    
    def __init__(self, id_global: int, nombre: str, fecha_nacimiento: str, genero: str, tipo_sangre: str, factor_rh: str, id_paciente: int, area_internamiento: str, diagnostico_ingreso: str, prioridad_clinica: str):
        super().__init__(id_global, nombre, fecha_nacimiento, genero, tipo_sangre, factor_rh)
        
        self.id_paciente = id_paciente          
        self.area_internamiento = area_internamiento.strip().title() 
        self.diagnostico_ingreso = diagnostico_ingreso.strip().capitalize()
        self.prioridad_clinica = prioridad_clinica.strip().title()           
        
        self.historial_transfusiones = []

    @classmethod
    def obtener_todos_los_pacientes(cls, gestor_datos) -> list:
        """Extrae la lista completa de pacientes activos para mostrarla en pantalla."""
        df_pacientes = gestor_datos.leer_persistencias("pacientes")
        
        if df_pacientes is not None and not df_pacientes.empty:
            df_limpio = df_pacientes.fillna("")
            return df_limpio.to_dict('records')
            
        return []

    @classmethod
    def cargar_desde_csv(cls, id_buscado: int, gestor_datos):
        """
        Reconstruye la información de un paciente usando su número de identificación.
        Se encarga de convertir el historial de transfusiones (que viene como texto en el CSV) 
        de vuelta a una lista útil en Python.
        """
        df_pacientes = gestor_datos.leer_persistencias("pacientes")
        
        if df_pacientes is not None and not df_pacientes.empty:
            filtro = df_pacientes[df_pacientes['id_paciente'] == id_buscado]
            
            if not filtro.empty:
                datos = filtro.iloc[0]
                
                paciente_recuperado = cls(
                    id_global=datos['id_global'],
                    nombre=datos['nombre'],
                    fecha_nacimiento=datos['fecha_nacimiento'],
                    genero=datos['genero'],
                    tipo_sangre=datos['tipo_sangre'],
                    factor_rh=datos['factor_rh'],
                    id_paciente=datos['id_paciente'],
                    area_internamiento=datos['area_internamiento'],
                    diagnostico_ingreso=datos['diagnostico_ingreso'],
                    prioridad_clinica=datos['prioridad_clinica']
                )
                
                # Transformamos la lista de bolsas que venía separada por comas en el archivo
                historial_str = datos.get('historial_transfusiones')
                
                if pd.isna(historial_str) or not str(historial_str).strip():
                    paciente_recuperado.historial_transfusiones = []
                else:
                    paciente_recuperado.historial_transfusiones = [
                        int(float(x.strip())) for x in str(historial_str).split(',') if x.strip()
                    ]
                    
                return paciente_recuperado
        return None

    def actualizar_historial_transfusional(self, id_unidad: int) -> bool:
        """
        Anota en el expediente médico que el paciente recibió una bolsa nueva.
        Evita que la misma bolsa se registre dos veces por accidente.
        """
        if id_unidad in self.historial_transfusiones:
            raise ValueError(f"Aviso del sistema: La bolsa {id_unidad} ya estaba registrada en el historial del paciente {self.nombre}.")
            
        self.historial_transfusiones.append(id_unidad)
        return True

    def obtener_resumen_clinico(self) -> str:
        """Prepara un reporte ordenado del paciente para imprimir o mostrar en consola."""
        perfil_base = self.obtener_perfil_biologico()
        
        resumen = (f"\n--- REPORTE CLÍNICO - PACIENTE: {self.id_paciente} ---\n"
                   f"{perfil_base}\n"
                   f"Ubicación Asignada: {self.area_internamiento}\n"
                   f"Motivo de Ingreso: {self.diagnostico_ingreso}\n"
                   f"Nivel de Urgencia: {self.prioridad_clinica}\n"
                   f"Bolsas Transfundidas: {len(self.historial_transfusiones)}\n"
                   f"----------------------------------------------------------")
        return resumen

    def registrar_paciente(self, gestor_datos):
        """
        Guarda los datos del paciente. Tiene un trato especial para que la lista 
        de bolsas transfundidas se guarde como un texto simple separado por comas, 
        evitando errores al escribir en el archivo CSV.
        """
        df_pacientes = gestor_datos.leer_persistencias("pacientes")
        
        if df_pacientes is not None:
            # Preparamos la columna para evitar problemas al inyectarle una lista convertida en texto
            if 'historial_transfusiones' in df_pacientes.columns:
                df_pacientes['historial_transfusiones'] = df_pacientes['historial_transfusiones'].astype(object)
                
            if not df_pacientes.empty and 'id_paciente' in df_pacientes.columns and self.id_paciente in df_pacientes['id_paciente'].values:
                mascara = df_pacientes['id_paciente'] == self.id_paciente
                
                df_pacientes.loc[mascara, 'nombre'] = self.nombre
                df_pacientes.loc[mascara, 'tipo_sangre'] = self.tipo_sangre
                df_pacientes.loc[mascara, 'factor_rh'] = self.factor_rh
                
                df_pacientes.loc[mascara, 'area_internamiento'] = self.area_internamiento
                df_pacientes.loc[mascara, 'diagnostico_ingreso'] = self.diagnostico_ingreso
                df_pacientes.loc[mascara, 'prioridad_clinica'] = self.prioridad_clinica
                
                # Convertimos la lista de bolsas en un solo texto (ejemplo: "101,102,103")
                df_pacientes.loc[mascara, 'historial_transfusiones'] = ",".join(map(str, self.historial_transfusiones))
                
            else:
                nuevo_registro = {
                    'id_global': self.id_global,
                    'nombre': self.nombre,
                    'fecha_nacimiento': self.fecha_nacimiento,
                    'genero': self.genero,
                    'tipo_sangre': self.tipo_sangre,
                    'factor_rh': self.factor_rh,
                    'id_paciente': self.id_paciente,
                    'area_internamiento': self.area_internamiento,
                    'diagnostico_ingreso': self.diagnostico_ingreso,
                    'prioridad_clinica': self.prioridad_clinica,
                    'historial_transfusiones': ",".join(map(str, self.historial_transfusiones))
                }
                
                df_nuevo = pd.DataFrame([nuevo_registro])
                df_pacientes = pd.concat([df_pacientes, df_nuevo], ignore_index=True)

            gestor_datos.guardar_cambios_atomicos("pacientes", df_pacientes)
        else:
            raise RuntimeError("Fallo crítico del sistema: No pudimos acceder al archivo de pacientes.")
        
class Trabajador(Persona):
    """
    Representa a los empleados del banco de sangre (como médicos o administradores).
    Su función principal es manejar los roles de acceso y encriptar las contraseñas 
    para mantener el sistema completamente seguro.
    """
    
    def __init__(self, id_global, nombre, fecha_nacimiento, genero, tipo_sangre, factor_rh, cedula_profesional, rol, password_plana):
        super().__init__(id_global, nombre, fecha_nacimiento, genero, tipo_sangre, factor_rh)
        self.cedula_profesional = cedula_profesional
        self.rol = rol.strip().title()
        
        self.password_hash = self._encriptar_password(password_plana)
        self.sesion_iniciada = False

    @classmethod
    def cargar_desde_csv(cls, id_buscado: int, gestor_datos):
        """
        Recupera el perfil de un empleado de forma segura. 
        Evita problemas si hay espacios vacíos en las columnas de la base de datos.
        """
        df_trabajadores = gestor_datos.leer_persistencias("trabajadores")
        
        if df_trabajadores is not None and not df_trabajadores.empty:
            # Limpiamos todo el archivo de valores nulos antes de buscar
            df_limpio = df_trabajadores.fillna("")
            filtro = df_limpio[df_limpio['id_global'] == id_buscado]
            
            if not filtro.empty:
                datos = filtro.iloc[0]
                
                trabajador = cls(
                    id_global=datos['id_global'],
                    nombre=str(datos['nombre']),
                    fecha_nacimiento=str(datos['fecha_nacimiento']),
                    genero=str(datos['genero']),
                    tipo_sangre=str(datos['tipo_sangre']) if datos['tipo_sangre'] else "N/A",
                    factor_rh=str(datos['factor_rh']),
                    cedula_profesional=str(datos['cedula_profesional']),
                    rol=str(datos['rol']),
                    password_plana="temporal" # Dato de relleno temporal que reemplazamos enseguida por la contraseña real
                )
                
                trabajador.password_hash = str(datos['password_hash'])
                return trabajador
                
        return None

    def _encriptar_password(self, password_plana: str) -> str:
        """
        Transforma la contraseña escrita por el empleado en un código ilegible (Hash) 
        usando bcrypt, de modo que ni siquiera nosotros podamos ver sus claves.
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_plana.encode('utf-8'), salt)
        return hashed.decode('utf-8') 

    def iniciar_sesion(self, password_intento: str) -> bool:        
        """
        Compara la contraseña ingresada con la que tenemos guardada de forma segura.
        Si coincide, le da acceso al sistema.
        """
        if bcrypt.checkpw(password_intento.encode('utf-8'), self.password_hash.encode('utf-8')):
            self.sesion_iniciada = True
            return True
        else:
            self.sesion_iniciada = False
            raise PermissionError("Acceso denegado: La contraseña ingresada es incorrecta.")

    @classmethod
    def obtener_todos_los_trabajadores(cls, gestor_datos) -> list:
        """
        Genera la lista de los empleados activos en el hospital. 
        Como medida de seguridad, borra las contraseñas encriptadas de la lista 
        antes de mandarla a la interfaz gráfica.
        """
        df_trabajadores = gestor_datos.leer_persistencias("trabajadores")
        
        if df_trabajadores is not None and not df_trabajadores.empty:
            df_limpio = df_trabajadores.fillna("")
            directorio = df_limpio.to_dict('records')
            
            # Eliminamos los Hashes por seguridad antes de mostrar la información en pantalla
            for trabajador in directorio:
                trabajador.pop('password_hash', None)
                    
            return directorio
        return []

    def registrar_trabajador(self, gestor_datos):
        """
        Guarda al empleado y su contraseña encriptada en la base de datos, 
        asegurándose de no duplicar registros si ya existía en el sistema.
        """
        df_trabajadores = gestor_datos.leer_persistencias("trabajadores")
        
        if df_trabajadores is not None:
            if not df_trabajadores.empty and 'id_global' in df_trabajadores.columns and self.id_global in df_trabajadores['id_global'].values:
                mascara = df_trabajadores['id_global'] == self.id_global
                
                df_trabajadores.loc[mascara, 'nombre'] = self.nombre
                df_trabajadores.loc[mascara, 'tipo_sangre'] = self.tipo_sangre
                df_trabajadores.loc[mascara, 'factor_rh'] = self.factor_rh
                df_trabajadores.loc[mascara, 'rol'] = self.rol
                df_trabajadores.loc[mascara, 'password_hash'] = self.password_hash 
                
            else:
                nuevo_registro = {
                    'id_global': self.id_global,
                    'nombre': self.nombre,
                    'fecha_nacimiento': self.fecha_nacimiento,
                    'genero': self.genero,
                    'tipo_sangre': self.tipo_sangre,
                    'factor_rh': self.factor_rh,
                    'cedula_profesional': self.cedula_profesional,
                    'rol': self.rol,
                    'password_hash': self.password_hash
                }
                
                df_nuevo = pd.DataFrame([nuevo_registro])
                df_trabajadores = pd.concat([df_trabajadores, df_nuevo], ignore_index=True)

            gestor_datos.guardar_cambios_atomicos("trabajadores", df_trabajadores)
        else:
            raise RuntimeError("Fallo crítico del sistema: No pudimos acceder al archivo de trabajadores.")
        
    def autenticar_operacion(self, password_intento: str) -> bool:
        """
        Punto extra de seguridad (Firma Electrónica). 
        Le vuelve a pedir la contraseña al médico antes de que haga un movimiento 
        crítico (como desechar una bolsa de sangre o confirmar una transfusión).
        """
        if not password_intento:
            return False
            
        return bcrypt.checkpw(
            password_intento.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )
    
    def cerrar_sesion(self):
        """
        Cierra la sesión del trabajador, bloqueando sus permisos hasta que vuelva a iniciar sesión.
        """
        self.sesion_iniciada = False
