"""
Módulo de Gestión de Almacén e Inventario - BloodConnect
Este archivo es el encargado de administrar el "refrigerador virtual" del laboratorio. 
Controla todo el ciclo de vida de una bolsa de sangre: desde que se le extrae al donante, 
su separación en diferentes componentes, la espera de los resultados de laboratorio 
y su desecho automático si llega a caducar.
"""

from datetime import datetime, date, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any
import pandas as pd


class EstadoHemocomponente(Enum):
    """
    Define las etapas por las que pasa una bolsa de sangre. 
    Ayuda a prevenir errores graves, como intentar transfundir una bolsa 
    que todavía está 'En Cuarentena' esperando resultados de laboratorio.
    """
    EN_CUARENTENA = "En Cuarentena"
    LIBERADA = "Liberada"
    DESECHADA = "Desechada"
    FRACCIONADA = "Fraccionada"
    TRANSFUNDIDA = "Transfundida"


class TipoHemocomponente(Enum):
    """Catálogo exacto de los productos sanguíneos que maneja el inventario."""
    SANGRE_ENTERA = "Sangre Entera"
    GLOBULOS_ROJOS = "Globulos Rojos"
    PLASMA = "Plasma"
    PLAQUETAS = "Plaquetas"
    CRIOPRECIPITADOS = "Crioprecipitados"


class Extraccion:
    """
    Representa el momento en que un donante da sangre. 
    Guarda los datos de la donación para asegurar que siempre sepamos 
    de dónde salió una bolsa específica (trazabilidad).
    """
    
    def __init__(self, id_extraccion: int, id_donante: int, volumen_ml: int, id_personal_responsable: int, observaciones_clinicas: str = ""):
        self.id_extraccion = id_extraccion
        self.id_donante = id_donante
        
        # Validación de seguridad para proteger al donante
        if not (400 <= volumen_ml <= 500):
            raise ValueError(f"Aviso médico: El volumen extraído ({volumen_ml} ml) está fuera del rango permitido por seguridad (400-500 ml).")
        
        self.volumen_ml = volumen_ml
        self.fecha_hora = datetime.now() 
        self.observaciones_clinicas = observaciones_clinicas.strip()
        self.id_personal_responsable = id_personal_responsable

    def registrar_extraccion(self, gestor_datos: Any) -> bool:
        """
        Guarda el registro de la extracción en los archivos del sistema, 
        verificando primero que el donante realmente exista.
        """
        # Nos aseguramos de no guardar una extracción de un donante fantasma
        if not gestor_datos.existe_id_en_archivo("donantes", "id_global", self.id_donante):
            raise ValueError(f"Error de registro: No se encontró al donante con número {self.id_donante} en el sistema.")
    
        df_extracciones = gestor_datos.leer_persistencias("extracciones")

        if df_extracciones is None:
            raise IOError(f"Aviso del sistema: No se pudo conectar con el archivo de extracciones. Operación {self.id_extraccion} cancelada.")

        # Preparamos los datos de la extracción para guardarlos ordenadamente
        nuevo_registro = {
            'id_extraccion': self.id_extraccion,
            'id_donante': self.id_donante,
            'volumen_ml': self.volumen_ml,
            'fecha_hora': self.fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
            'observaciones_clinicas': self.observaciones_clinicas,
            'id_personal_responsable': self.id_personal_responsable
        }
        
        # Agregamos la nueva fila y guardamos los cambios de manera segura
        df_nuevo = pd.DataFrame([nuevo_registro])
        df_extracciones = pd.concat([df_extracciones, df_nuevo], ignore_index=True)
        gestor_datos.guardar_cambios_atomicos("extracciones", df_extracciones)
        
        return True

    def generar_etiqueta_trazabilidad(self) -> str:
        """
        Crea un código único (ideal para imprimir en código de barras) 
        juntando la fecha, el número de donación y el ID del donante.
        """
        año_mes = self.fecha_hora.strftime("%Y%m")
        return f"EXT-{año_mes}-{self.id_extraccion}-{self.id_donante}"

    def registrar_signos_vitales_post_donacion(self, complicaciones: Optional[List[str]] = None) -> bool:
        """
        Anota si el donante se mareó o sintió mal después de dar sangre, 
        para tenerlo en cuenta en su expediente.
        """
        if complicaciones and len(complicaciones) > 0:
            notas_adicionales = ", ".join(complicaciones).capitalize()
            self.observaciones_clinicas = f"Precaución post-donación: {notas_adicionales}. El donante requiere reposo."
            return False
        
        self.observaciones_clinicas = "Extracción completada con éxito. Donante estable."
        return True


class Hemocomponente:
    """
    Representa una bolsa física de sangre en el refrigerador. 
    Protege sus datos importantes (como la caducidad y su estado) para evitar 
    que alguien los modifique por error y cause un accidente médico.
    """
    
    def __init__(self, id_unidad: int, tipo_componente: TipoHemocomponente, tipo_sangre: str, factor_rh: str, fecha_caducidad: date, temperatura_almacenamiento: float, estado: EstadoHemocomponente, refrigerador_asignado: str):
        self.id_unidad = id_unidad                           
        self.tipo_componente = tipo_componente               
        self.tipo_sangre = tipo_sangre.strip().upper()                       
        self.factor_rh = factor_rh.strip()                           
        
        self._fecha_caducidad = fecha_caducidad               
        # Por seguridad, toda bolsa nueva entra bloqueada ("En Cuarentena") hasta que el laboratorio la apruebe
        self._estado: EstadoHemocomponente = EstadoHemocomponente.EN_CUARENTENA 
        
        self.estado = estado                                 
        
        self.temperatura_almacenamiento = temperatura_almacenamiento 
        self.refrigerador_asignado = refrigerador_asignado.strip()   

    @property
    def estado(self) -> EstadoHemocomponente:
        return self._estado

    @estado.setter
    def estado(self, nuevo_estado: EstadoHemocomponente):
        # Evitamos que se le asigne un estado inventado o en formato de texto normal
        if not isinstance(nuevo_estado, EstadoHemocomponente):
            raise TypeError(f"Error interno: El estado asignado no es válido. Se recibió '{type(nuevo_estado).__name__}'.")
        self._estado = nuevo_estado

    @property
    def fecha_caducidad(self) -> date:
        return self._fecha_caducidad

    @fecha_caducidad.setter
    def fecha_caducidad(self, nueva_fecha: date):
        # Medida de seguridad: Nadie puede ponerle a una bolsa una fecha de caducidad que ya pasó
        if nueva_fecha < date.today():
            raise ValueError("Alerta de seguridad: No se puede asignar una fecha de caducidad en el pasado.")
        self._fecha_caducidad = nueva_fecha

    def _generar_id_derivado(self, sufijo: int) -> int:
        """
        Crea un número de identificación único para las bolsas hijas (cuando separamos la sangre).
        Le agrega ceros a la izquierda para mantener un formato ordenado y evitar confusiones.
        """
        return int(f"{self.id_unidad:0>12}{sufijo}")

    def fraccionar_bolsa_madre(self) -> List['Hemocomponente']:
        """
        Simula el proceso de la centrífuga. Toma una bolsa de 'Sangre Entera' y la divide 
        en tres bolsas nuevas: Glóbulos Rojos, Plasma y Plaquetas, calculando la nueva caducidad de cada una.
        """
        if self.estado == EstadoHemocomponente.FRACCIONADA:
            raise ValueError(f"Aviso del sistema: La bolsa {self.id_unidad} ya fue separada anteriormente.")
            
        if self.tipo_componente != TipoHemocomponente.SANGRE_ENTERA:
            raise ValueError(f"Operación inválida: Solo se puede fraccionar 'Sangre Entera'. Tipo actual: '{self.tipo_componente.value}'.")
            
        # Solo podemos fraccionar bolsas que ya pasaron las pruebas de laboratorio
        if self.estado != EstadoHemocomponente.LIBERADA:
            raise ValueError(f"Alerta de bioseguridad: La bolsa debe estar 'Liberada' para separarse. Estado actual: {self.estado.value}.")

        # Calculamos cuándo se extrajo la sangre originalmente para calcular las nuevas fechas de caducidad
        fecha_extraccion = self.fecha_caducidad - timedelta(days=35)
        hoy = date.today()
        
        # Creamos las tres bolsas hijas con sus propias reglas de temperatura y caducidad
        id_rojos = self._generar_id_derivado(1)
        caducidad_rojos = max(hoy, fecha_extraccion + timedelta(days=42))
        globulos_rojos = Hemocomponente(id_rojos, TipoHemocomponente.GLOBULOS_ROJOS, self.tipo_sangre, self.factor_rh, caducidad_rojos, 4.0, EstadoHemocomponente.LIBERADA, "Ref-01")
        
        id_plasma = self._generar_id_derivado(2)
        caducidad_plasma = max(hoy, fecha_extraccion + timedelta(days=365))
        plasma = Hemocomponente(id_plasma, TipoHemocomponente.PLASMA, self.tipo_sangre, self.factor_rh, caducidad_plasma, -20.0, EstadoHemocomponente.LIBERADA, "Congelador-A")
        
        id_plaquetas = self._generar_id_derivado(3)
        caducidad_plaquetas = max(hoy, fecha_extraccion + timedelta(days=5))
        plaquetas = Hemocomponente(id_plaquetas, TipoHemocomponente.PLAQUETAS, self.tipo_sangre, self.factor_rh, caducidad_plaquetas, 22.0, EstadoHemocomponente.LIBERADA, "Agitador-01")
        
        # Marcamos la bolsa original como procesada
        self.estado = EstadoHemocomponente.FRACCIONADA
        return [globulos_rojos, plasma, plaquetas]
        
    def extraer_crioprecipitado(self) -> 'Hemocomponente':
        """
        Toma una bolsa de Plasma y le extrae un componente especial llamado Crioprecipitado, 
        creando una nueva bolsa en el sistema para este producto.
        """
        if self.estado == EstadoHemocomponente.FRACCIONADA:
            raise ValueError(f"Aviso del sistema: La bolsa de plasma {self.id_unidad} ya fue procesada.")
            
        if self.tipo_componente != TipoHemocomponente.PLASMA:
            raise ValueError(f"Operación inválida: Los crioprecipitados solo se pueden extraer del '{TipoHemocomponente.PLASMA.value}'.")
            
        if self.estado != EstadoHemocomponente.LIBERADA:
            raise ValueError(f"Alerta de bioseguridad: El plasma debe estar 'Liberado' para procesarlo. Estado actual: {self.estado.value}.")

        id_crio = self._generar_id_derivado(4)
        
        crio = Hemocomponente(
            id_unidad=id_crio,
            tipo_componente=TipoHemocomponente.CRIOPRECIPITADOS,
            tipo_sangre=self.tipo_sangre,
            factor_rh=self.factor_rh,
            fecha_caducidad=self.fecha_caducidad,
            temperatura_almacenamiento=-20.0,
            estado=EstadoHemocomponente.LIBERADA, 
            refrigerador_asignado="Congelador-Crio-A"
        )
        
        self.estado = EstadoHemocomponente.FRACCIONADA
        return crio
    
    def liberar_por_serologia(self, dictamen_laboratorio: Any) -> bool:
        """
        Recibe los resultados del laboratorio. Si todo está limpio, 
        desbloquea la bolsa para que pueda ser transfundida a un paciente.
        """
        if self.estado == EstadoHemocomponente.FRACCIONADA:
            raise ValueError(f"Aviso: La bolsa {self.id_unidad} ya está separada. Aplique los resultados a las bolsas hijas.")
            
        # Le preguntamos a la prueba de laboratorio si aprobó o no
        if dictamen_laboratorio.emitir_dictamen_seguridad():
            self.estado = EstadoHemocomponente.LIBERADA
            return True
        else:
            self.estado = EstadoHemocomponente.DESECHADA
            return False

    def verificar_viabilidad(self) -> bool:
        """
        Revisa automáticamente si la bolsa ya caducó según la fecha de hoy. 
        Si ya pasó su tiempo, la marca como 'Desechada' para que nadie la use.
        """
        if self.estado in [EstadoHemocomponente.DESECHADA, EstadoHemocomponente.FRACCIONADA, EstadoHemocomponente.TRANSFUNDIDA]:
            return False
            
        if date.today() > self.fecha_caducidad:
            self.estado = EstadoHemocomponente.DESECHADA 
            return False
            
        return True


class Inventario:
    """
    Actúa como el cerebro del almacén. Mantiene en la memoria temporal la lista 
    de todas las bolsas disponibles y se encarga de guardar los cambios en los archivos.
    """
    
    def __init__(self, umbral_critico_seguridad: int):
        self.unidades_disponibles: List[Hemocomponente] = [] 
        self.umbral_critico_seguridad = umbral_critico_seguridad 

    def cargar_inventario_inicial(self, gestor_datos: Any) -> int:
        """
        Carga las bolsas guardadas en el archivo CSV a la memoria del programa.
        Está diseñado para no colapsar: si una fila en el archivo está rota, la ignora y sigue cargando el resto.
        """
        df_inventario = gestor_datos.leer_persistencias("inventario")

        if df_inventario is None or df_inventario.empty:
            return 0

        unidades_cargadas = 0
        errores_carga = []
        registros_inventario = df_inventario.to_dict('records')
        
        for fila in registros_inventario:
            # Intentamos leer las fechas y los textos evitando que un dato mal escrito rompa todo el sistema
            try:
                partes_fecha = str(fila.get('fecha_caducidad', '')).split('-')
                fecha_cad = date(int(partes_fecha[0]), int(partes_fecha[1]), int(partes_fecha[2]))
                
                estado_enum = EstadoHemocomponente(str(fila.get('estado', '')).strip())
                tipo_enum = TipoHemocomponente(str(fila.get('tipo_componente', '')).strip())
                
            except (ValueError, IndexError, TypeError) as e:
                id_u = fila.get('id_unidad', 'Desconocida')
                errores_carga.append(f"Se ignoró la unidad {id_u} por tener un formato incorrecto: {e}")
                continue  

            # Reconstruimos la bolsa en el programa
            try:
                unidad_recuperada = Hemocomponente(
                    id_unidad=int(fila.get('id_unidad', 0)),
                    tipo_componente=tipo_enum,
                    tipo_sangre=str(fila.get('tipo_sangre', 'N/A')).strip().upper(),
                    factor_rh=str(fila.get('factor_rh', '')).strip(),
                    fecha_caducidad=fecha_cad,
                    temperatura_almacenamiento=float(fila.get('temperatura_almacenamiento', 4.0)),
                    estado=estado_enum,
                    refrigerador_asignado=str(fila.get('refrigerador_asignado', 'Pendiente')).strip()
                )
                
                self.unidades_disponibles.append(unidad_recuperada)
                unidades_cargadas += 1
            except Exception as e:
                id_u = fila.get('id_unidad', 'Desconocida')
                errores_carga.append(f"Error al intentar cargar la unidad {id_u}: {e}")
                continue

        # Mostramos advertencias en consola si encontramos filas defectuosas en el archivo
        if errores_carga:
            print(f"Aviso del sistema: Se terminó de cargar el inventario, pero se omitieron {len(errores_carga)} bolsas por tener datos dañados en el archivo.")
            
        return unidades_cargadas
    
    def obtener_unidad_por_id(self, id_unidad: int) -> Optional[Hemocomponente]:
        """Busca una bolsa específica por su número dentro del refrigerador virtual."""
        for unidad in self.unidades_disponibles:
            if unidad.id_unidad == id_unidad:
                return unidad
        return None

    def ingresar_unidad(self, nueva_unidad: Hemocomponente) -> bool:
        """
        Mete una bolsa nueva al inventario, comprobando primero 
        que no exista otra bolsa con ese mismo número de serie.
        """
        for unidad_existente in self.unidades_disponibles:
            if unidad_existente.id_unidad == nueva_unidad.id_unidad:
                raise ValueError(f"Error de datos: La bolsa {nueva_unidad.id_unidad} ya se encuentra registrada en el almacén.")
                
        self.unidades_disponibles.append(nueva_unidad)
        return True

    def depurar_unidades_caducadas(self, gestor_datos: Any) -> int:
        """
        Rutina de limpieza automática. Revisa todo el almacén y tira a la basura virtual 
        ("Desechada") cualquier bolsa que ya se haya pasado de su fecha.
        """
        caducadas_detectadas = 0
        
        for unidad in self.unidades_disponibles:
            estado_previo = unidad.estado 
            if not unidad.verificar_viabilidad() and estado_previo != EstadoHemocomponente.DESECHADA:
                caducadas_detectadas += 1

        # Si se desecharon bolsas, actualiza los archivos para que quede registro
        if caducadas_detectadas > 0:
            self.guardar_inventario_actualizado(gestor_datos)

        return caducadas_detectadas

    def calcular_stock_dinamico(self) -> Dict[str, int]:
        """Cuenta exactamente cuántas bolsas listas para usarse ('Liberadas') tenemos de cada tipo de sangre."""
        conteo = {}
        
        for unidad in self.unidades_disponibles:
            if unidad.estado == EstadoHemocomponente.LIBERADA:
                clave_inventario = f"{unidad.tipo_componente.value} {unidad.tipo_sangre}{unidad.factor_rh}"
                conteo[clave_inventario] = conteo.get(clave_inventario, 0) + 1
                
        return conteo

    def verificar_alertas_desabasto(self) -> bool:
        """Comprueba si la cantidad total de sangre lista para usarse bajó del límite de seguridad del hospital."""
        total_liberadas = sum(1 for unidad in self.unidades_disponibles if unidad.estado == EstadoHemocomponente.LIBERADA)
        return total_liberadas < self.umbral_critico_seguridad
        
    def guardar_inventario_actualizado(self, gestor_datos: Any) -> bool:
        """Toma todo el inventario actual y lo sobreescribe en el archivo CSV para guardar los cambios."""
        # Convertimos nuestra lista de bolsas en el formato de diccionario que requiere Pandas
        datos_inventario = [
            {
                'id_unidad': unidad.id_unidad,
                'tipo_componente': unidad.tipo_componente.value,
                'tipo_sangre': unidad.tipo_sangre,
                'factor_rh': unidad.factor_rh,
                'fecha_caducidad': unidad.fecha_caducidad.strftime("%Y-%m-%d"),
                'temperatura_almacenamiento': unidad.temperatura_almacenamiento,
                'estado': unidad.estado.value,
                'refrigerador_asignado': unidad.refrigerador_asignado
            }
            for unidad in self.unidades_disponibles
        ]
            
        df_actualizado = pd.DataFrame(datos_inventario)
        
        # Medida de protección: Si el almacén está vacío, guardamos las columnas de todos modos para no perder la estructura del archivo
        if df_actualizado.empty:
            df_actualizado = pd.DataFrame(columns=[
                'id_unidad', 'tipo_componente', 'tipo_sangre', 'factor_rh', 
                'fecha_caducidad', 'temperatura_almacenamiento', 'estado', 'refrigerador_asignado'
            ])
            
        gestor_datos.guardar_cambios_atomicos("inventario", df_actualizado)
        return True


class PruebaLaboratorio:
    """
    Representa el panel de pruebas que se le hace a la sangre (VIH, Hepatitis, etc.).
    Una vez registrados los resultados, no se pueden modificar para evitar fraudes.
    """
    
    def __init__(self, id_prueba: int, id_unidad: int, id_laboratorista: int):
        self.id_prueba = id_prueba
        self.id_unidad = id_unidad
        self.id_laboratorista = id_laboratorista
        self.fecha_analisis = datetime.now()
        
        # Guardamos los resultados de forma privada para que no se puedan cambiar por fuera
        self._marcadores: Dict[str, Optional[bool]] = {
            "VIH": None,
            "Hepatitis_B": None,
            "Hepatitis_C": None,
            "Sifilis": None,
            "Chagas": None
        }

    @property
    def marcadores(self) -> dict:
        return self._marcadores.copy()

    def registrar_resultados(self, vih: bool, hep_b: bool, hep_c: bool, sifilis: bool, chagas: bool):
        """Anota los resultados. Exige que todo sea Verdadero (Enfermo) o Falso (Sano)."""
        if not all(isinstance(resultado, bool) for resultado in [vih, hep_b, hep_c, sifilis, chagas]):
            raise TypeError("Error médico: Los resultados de laboratorio deben ser valores de Verdadero o Falso.")
            
        self._marcadores["VIH"] = vih
        self._marcadores["Hepatitis_B"] = hep_b
        self._marcadores["Hepatitis_C"] = hep_c
        self._marcadores["Sifilis"] = sifilis
        self._marcadores["Chagas"] = chagas
        
    def emitir_dictamen_seguridad(self) -> bool:
        """
        Revisa los resultados finales. Si falta alguna prueba o si tan solo una 
        sale positiva, la bolsa reprueba y debe desecharse automáticamente.
        """
        # Verificamos que no se haya olvidado realizar ninguna prueba
        if None in self._marcadores.values():
            raise ValueError("Alerta médica: El panel está incompleto. Deben procesarse todos los reactivos antes de dar un dictamen.")
            
        # Si algún valor es True (Salió positivo a una enfermedad), reprueba inmediatamente
        if any(self._marcadores.values()):
            return False
            
        # Si todas son False (negativo), la sangre es segura
        return True