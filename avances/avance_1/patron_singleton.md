# Avance Patrón de Diseño Singleton

## 1. Identificación del Avance
* **Patrón de Diseño:** Singleton (Creacional).
* **Elemento del Sistema:** `ElectoralConfigManager` (Núcleo del Dominio).
* **Ubicación del Código:** `src/core/config.py`.

---

## 2. Justificación y Problema que Resuelve en el Dominio

En un sistema de votación electrónica, la jornada electoral cuenta con un conjunto de reglas y estados globales críticos:
* Estado de la urna electoral (si la votación está abierta o cerrada).
* Nombre oficial de la jornada e institución organizadora.
* Límite legal de votos permitidos por ciudadano.

Si los distintos módulos del sistema (como autenticación de votantes, emisión de sufragios o conteo de votos) gestionaran instancias independientes de la configuración, se producirían inconsistencias de estado. Por ejemplo: el módulo de autenticación podría considerar que la urna sigue abierta mientras que el módulo administrativo ya la cerró.

El patrón **Singleton** garantiza la existencia de **una única instancia global** de la configuración electoral en memoria compartida, proporcionando un punto de acceso centralizado y seguro para todos los subsistemas.

---

## 3. Implementación Técnica en el Código

En Python, el control de la instanciación única se implementa interceptando el método especial `__new__`, garantizando además la concurrencia mediante cerrojos de sincronización (`threading.Lock`).

### Fragmento de Código Clave (`src/core/config.py`):

```python
import threading
from typing import Optional

class ElectoralConfigManager:
    """Gestiona la configuración global de la jornada electoral garantizando una única instancia."""

    _instance: Optional["ElectoralConfigManager"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls, *args, **kwargs) -> "ElectoralConfigManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        institution_name: str = "Consejo Nacional Electoral",
        election_title: str = "Elecciones Generales",
        max_votes_per_citizen: int = 1,
    ) -> None:
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self.institution_name = institution_name
                self.election_title = election_title
                self.max_votes_per_citizen = max_votes_per_citizen
                self._is_open: bool = False
                self._initialized = True

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open_voting(self) -> None:
        self._is_open = True

    def close_voting(self) -> None:
        self._is_open = False

    @classmethod
    def reset_for_testing(cls) -> None:
        """Permite reiniciar la instancia en entornos controlados de prueba."""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
```

---

## 4. Análisis de Ingeniería de Software

### 4.1 Seguridad en Hilos (*Thread-Safety*)
Se implementó la técnica de comprobación con doble bloqueo (*Double-Checked Locking*):
1. Se verifica si la variable `_instance` es nula antes de adquirir el cerrojo.
2. Si es nula, se entra al bloque `with cls._lock` y se vuelve a comprobar antes de asignar `super().__new__(cls)`.
3. Esto evita el costo de sincronización en llamadas posteriores una vez creada la instancia.

### 4.2 Control de Re-inicialización
En Python, cada vez que se llama al constructor de clase, `__init__` se invoca de nuevo. Para evitar que llamadas posteriores sobreescriban los datos ya configurados de la elección, se utiliza la bandera `_initialized`.

### 4.3 Relación con Principios SOLID
* **Single Responsibility Principle (SRP):** La clase asume la responsabilidad exclusiva de salvaguardar y exponer los parámetros centrales de la jornada electoral, centralizando su ciclo de vida.
* **Aislamiento para Pruebas (Testability):** Se incorporó el método `reset_for_testing()` para mitigar el acoplamiento global en pruebas automatizadas y asegurar aislamiento entre ejecuciones.
