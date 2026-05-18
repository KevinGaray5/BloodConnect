# 🩸 BloodConnect
### Infraestructura Tecnológica para la Gestión Integral de Hemocomponentes y Redes Interhospitalarias

---

## 🌍 1. Descripción General e Impacto

**BloodConnect** es un sistema de software especializado en el control integral y la gestión optimizada de bancos de sangre y redes interhospitalarias. Diseñado bajo rigurosos estándares de bioseguridad y trazabilidad clínica, el propósito principal de esta plataforma es sistematizar de extremo a extremo el ciclo de vida del hemocomponente, abarcando desde el registro y pre-triaje médico del donante hasta la transfusión segura en el paciente receptor.

Frente a la burocracia operativa y las ineficiencias logísticas que comprometen la atención de urgencias, este software actúa como una infraestructura crítica de apoyo a la decisión médica. Al eliminar las demoras mediante algoritmos de compatibilidad automatizados, proteger estrictamente la cadena de frío y establecer un esquema de auditoría forense inmutable de "vena a vena", BloodConnect garantiza que el recurso vital esté disponible exactamente cuándo y dónde se requiere, transformando la administración de inventarios en una operación ágil que salva vidas.

---

## 🏗️ 2. Arquitectura y Tecnologías

Este sistema ha sido construido bajo los principios de una **Arquitectura Limpia**, fundamentado rígidamente en la Programación Orientada a Objetos (POO) y la implementación del patrón de diseño arquitectónico **Modelo-Vista-Controlador (MVC)**. La estricta separación de responsabilidades (SRP) nos permite desacoplar la interfaz de usuario de las complejas reglas biológicas del negocio, asegurando un entorno tolerante a fallos, altamente escalable y auditable.

Para la persistencia de datos a nivel local, BloodConnect emplea un motor transaccional atómico utilizando archivos CSV y mecanismos de bloqueo concurrente (`.lock`), lo que previene la corrupción de datos ante escrituras simultáneas o interrupciones, permitiendo un *rollback* de seguridad automático.

### 💻 Stack Tecnológico:

* **Python:** Lenguaje principal del motor de negocio y backend.
* **CustomTkinter:** Renderizado de una Interfaz Gráfica de Usuario (GUI) moderna, limpia y responsiva, diseñada específicamente para mitigar la fatiga cognitiva del personal de salud en entornos de alta presión.
* **Pandas:** Vectorización, limpieza y manipulación eficiente de matrices de datos y censos hospitalarios.
* **Matplotlib:** Generación nativa de gráficos estadísticos en tiempo real dentro del panel de control.
* **Bcrypt:** Implementación de algoritmos de hashing seguro para el resguardo de credenciales de acceso institucional.

---

## 🚀 3. Características y Módulos Clave

El sistema fragmenta las responsabilidades hospitalarias en módulos interconectados para maximizar la fluidez operativa:

* 📊 **Panel de Control (Dashboard Dinámico):** Visualización inmediata del balance general operativo mediante indicadores de rendimiento (KPIs), métricas estadísticas de distribución de grupos sanguíneos libres y un *feed* automatizado de alertas de desabasto.
* 👥 **Censo de Donantes y Validación Legal:** Captura segura de historiales físicos y automatización estricta de la veda biológica, bloqueando extracciones que no cumplan el intervalo legal mínimo de 56 días de recuperación.
* 📅 **Agenda Inteligente y Control de Aforo:** Modulación predictiva de citas para evitar la saturación de las salas, integrando la evaluación del cuestionario médico y la captura de signos vitales.
* 🔬 **Laboratorio y Fraccionamiento Molecular:** Bloqueo preventivo en cuarentena para resultados del panel serológico obligatorio. Tras la liberación por firma electrónica, el sistema habilita el fraccionamiento atómico de la sangre entera en concentrados eritrocitarios, plasma y plaquetas con controles térmicos individuales.
* 🚨 **Despacho Clínico y Algoritmos de Emergencia:** Asignación de unidades mediante un motor algorítmico de compatibilidad biológica (*smart matching*) que despacha bajo la lógica FIFO (First In, First Out) para prevenir mermas. Incorpora el protocolo **Break-Glass** para despachar inmediatamente unidades O- universales, saltando trabas burocráticas en códigos rojos.
* 🚑 **Logística de Red Interhospitalaria:** Sincronización cooperativa que utiliza identificadores estándar CLUES para consultar inventarios foráneos en tiempo real, enviar excedentes y autogenerar guías legales de transporte para amparar el traslado biológico.
* 🛡️ **Auditoría Inmutable y Seguridad (RBAC):** Restricción de operaciones críticas según el rol del usuario clínico e inmutabilidad de los logs forenses, permitiendo trazabilidad y simulando la impresión de etiquetas bajo la norma internacional ISBT 128.

---

## 📂 4. Estructura del Proyecto

El código fuente está organizado para facilitar su escalabilidad y la inyección de nuevas dependencias, respetando el paradigma MVC:

```text
BloodConnect/
├── main.py
├── requirements.txt
├── README.md
├── assets/
│   ├── logo.png
├── controladores/
│   ├── ctrl_identidades.py
│   ├── ctrl_agendamiento.py
│   ├── ctrl_almacen.py
│   └── ctrl_autenticacion.py
│   └── ctrl_auditoria.py
│   └── ctrl_clinico.py
│   └── sistema_bc_ctrl.py
├── clases/
│   ├── auditoria.py
│   ├── gestion_agendamineto.py
│   ├── gestion_almacen.py
│   └── gestion_clinica.py
│   └── gestion_identidades.py
│   └── red_interhospitalaria.py
├── gui_vistas/
│   ├── agenda.py
│   ├── almacen.py
│   ├── auditoria.py
│   └── dashboard.py
│   └── donantes.py
│   └── login.py
│   └── logistica.py
│   └── pacientes.py
│   └── tema_gui.py
│   └── ventana_principal.py
└── datos_csv/
    ├── donantes.csv
```

---

## 🛠️ 5. Instalación y Uso

Para desplegar BloodConnect en un entorno local, sigue estas instrucciones desde tu terminal:

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/tu-usuario/BloodConnect.git](https://github.com/tu-usuario/BloodConnect.git) 
   cd BloodConnect
   ```

2. **Crear y activar un entorno virtual (Recomendado):**
   ```bash
   python -m venv venv 
   # En Windows: 
   venv\Scripts\activate 
   # En macOS/Linux: 
   source venv/bin/activate
   ```

3. **Instalar las dependencias:**
   Puedes instalar directamente utilizando el archivo proveído:
   ```bash
   pip install -r requirements.txt
   ```
   *(Las dependencias principales incluyen: `customtkinter`, `pandas`, `matplotlib`, `bcrypt`, `pillow`).*

4. **Ejecutar el sistema:**
   Inicializa la aplicación ejecutando el archivo principal en la raíz del proyecto.
   ```bash
   python main.py
   ```
   > **Nota:** Las credenciales de acceso administrativo por defecto se encuentran documentadas en la guía de usuario interna.

---

## 👨‍💻 6. Autores

* **Sebastián García Parra**
* **Ali Kaled Elías García**
* **Kevin Gamaliel Garay Nolasco**

🎓 **Institución:** Facultad de Ciencias de la Computación (FCC) - Benemérita Universidad Autónoma de Puebla (BUAP).