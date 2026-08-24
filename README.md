# Plataforma de Votación Electrónica

<p align="center">
  <img src="https://media.giphy.com/media/26FPJGjhefSJuaRhu/giphy.gif" alt="Voting Animation" width="350"/>
</p>
<!-- Nota: Puedes cambiar la URL del src por el GIF que prefieras -->

## 1. Contextualización del Tema

### 1.1 ¿Qué es una Plataforma de Votación Electrónica?
Una plataforma de votación electrónica es un sistema de información diseñado para registrar, procesar, tabular y auditar sufragios de manera digital, ya sea en puestos de votación presenciales (mediante dispositivos de registro directo o DRE) o de forma remota a través de redes seguras.

A nivel global, la adopción del voto electrónico busca mejorar la eficiencia en la tabulación de resultados, reducir el uso de papel, eliminar errores humanos en el escrutinio de mesas y permitir la entrega de resultados preliminares en tiempos reducidos. Países como Estonia han consolidado modelos de voto por internet, mientras que otros como Brasil utilizan urnas electrónicas presenciales con respaldo digital.

### 1.2 El Dilema Central del Voto Digital
En la ingeniería de software, diseñar un sistema electoral representa uno de los desafíos más complejos debido a que exige satisfacer dos propiedades fundamentales que son naturalmente opuestas:
1. **Secreto del Voto (Anonimato):** Nadie (ni los administradores del sistema, ni los auditores, ni otros votantes) debe poder asociar la identidad de un ciudadano con su elección específica.
2. **Integridad y Verificabilidad (Auditabilidad):** Cada voto emitido debe ser registrado exactamente como el votante lo expresó, sin alteraciones, y debe ser posible auditar que el conteo final corresponde con la totalidad de los votos emitidos.

Adicionalmente, se deben mitigar riesgos como la coerción, el fraude informático, la suplantación de identidad, la denegación de servicio (DoS) y la pérdida de confianza de los participantes.

---

## 2. Objetivos del Proyecto

### 2.1 Objetivo General
Desarrollar una aplicación prototipo para una **Plataforma de Votación Electrónica** que permita simular un proceso electoral básico, aplicando patrones de diseño de software para estructurar de manera modular y ordenada la autenticación de votantes, la emisión anónima del voto, el conteo automatizado y el registro de auditoría.

### 2.2 Objetivos Específicos
1. **Modelar los requerimientos y el diseño del sistema:** Identificar los actores, flujos principales y casos de uso del proceso de votación, plasmándolos mediante diagramas UML para guiar la construcción del software.
2. **Implementar el control de acceso y validación de votantes:** Desarrollar un mecanismo para autenticar a los electores y verificar que solo puedan ejercer su derecho al voto una única vez.
3. **Garantizar el secreto y la privacidad del voto:** Diseñar la lógica de emisión de papeletas digitales de forma que la identidad del usuario no quede vinculada a la opción seleccionada.
4. **Construir el motor de conteo automatizado:** Desarrollar el módulo encargado de registrar, tabular y totalizar los votos emitidos para presentar los resultados del escrutinio de manera precisa.
5. **Crear un registro de eventos y auditoría:** Implementar un sistema de registro cronológico (*logs*) para rastrear eventos clave (apertura de votación, emisión de votos, cierre de jornada y emisión de resultados), permitiendo verificar la transparencia del proceso.
6. **Aplicar patrones de diseño de software:** Incorporar patrones de diseño para organizar el código de manera modular, facilitando su comprensión, mantenimiento y extensibilidad.
