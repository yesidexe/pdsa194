# Documento de Avance: Patrón de Diseño Prototype

## 1. Identificación del Avance
* **Patrón de Diseño:** Prototype (Creacional).
* **Elemento del Sistema:** Replicación de Mesas y Estaciones de Votación (`VotingStation`) mediante la interfaz genérica `Prototype` y catálogo `StationPrototypeRegistry`.
* **Ubicación del Código:** `src/modules/election/station_prototype.py`.

---

## 2. Justificación y Problema que Resuelve en el Dominio

En un despliegue electoral (ya sea a nivel universitario con decenas de mesas, o municipal/nacional con miles de mesas), cada **Mesa o Estación de Votación (`VotingStation`)** comparte una arquitectura operativa base:
* Mismo puesto de votación y código de zona.
* Mismo conjunto de tipos de tarjetones habilitados (presidencial, legislativo, consultas o voto en blanco).
* Mismas políticas de seguridad y estado inicial de habilitación.

Sin embargo, cada mesa física individual debe tener sus propios atributos únicos:
* Identificador unívoco de mesa (ej. `MESA-01`, `MESA-02`).
* Código de hardware o terminal biométrica asignada.
* Lista de jurados asignados para la custodia de la mesa.

### Problema de Creación Directa desde Cero
Instanciar repetidamente cada mesa invocando constructores completos con todas las listas y parámetros de configuración:
1. Consume recursos innecesarios recreando estructuras idénticas en memoria.
2. Es propenso a errores humanos de configuración en listas de tarjetones autorizados.
3. Acopla el código de despliegue con la clase concreta de la estación.

El patrón **Prototype** resuelve este problema permitiendo **clonar objetos existentes** para producir réplicas independientes y parametrizables, sin acoplarse a su implementación interna.

---

## 3. Implementación Técnica en el Código

### 3.1 La Interfaz Genérica `Prototype`

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar("T", bound="Prototype")

class Prototype(ABC, Generic[T]):
    """Interfaz genérica que formaliza la operación de clonación."""
    @abstractmethod
    def clone(self) -> T:
        """Retorna una copia profunda e independiente del objeto."""
        pass
```

### 3.2 Entidad Clonable con Copia Profunda (`VotingStation`)

```python
import copy
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class VotingStation(Prototype["VotingStation"]):
    """Representa una mesa de votación parametrizable y clonable."""
    station_id: str
    polling_place: str
    zone_code: str
    allowed_ballot_types: List[str] = field(default_factory=list)
    hardware_terminal_code: Optional[str] = None
    is_active: bool = True
    assigned_officers: List[str] = field(default_factory=list)

    def clone(self) -> "VotingStation":
        """Genera una copia profunda asegurando total independencia de colecciones mutables."""
        return copy.deepcopy(self)

    def assign_station(
        self,
        new_station_id: str,
        new_terminal_code: str,
        new_officers: Optional[List[str]] = None,
    ) -> "VotingStation":
        """Personaliza la estación clonada con identificadores únicos."""
        self.station_id = new_station_id
        self.hardware_terminal_code = new_terminal_code
        if new_officers is not None:
            self.assigned_officers = list(new_officers)
        return self
```

### 3.3 Catálogo de Prototipos (`StationPrototypeRegistry`)
Permite registrar mesas plantilla según la sede y despachar copias listas para personalizar:

```python
from typing import Dict

class StationPrototypeRegistry:
    """Registro de catálogo para almacenar y clonar plantillas de estaciones."""

    def __init__(self) -> None:
        self._prototypes: Dict[str, VotingStation] = {}

    def register_prototype(self, prototype_key: str, station: VotingStation) -> None:
        self._prototypes[prototype_key] = station

    def get_clone(self, prototype_key: str) -> VotingStation:
        if prototype_key not in self._prototypes:
            raise KeyError(f"Plantilla prototipo '{prototype_key}' no registrada en el catálogo.")
        return self._prototypes[prototype_key].clone()
```

---

## 4. Análisis de Ingeniería de Software

### 4.1 Análisis Crítico: *Shallow Copy* vs *Deep Copy*
En Python, una copia superficial (`copy.copy`) copia los campos del objeto pero mantiene la misma referencia en memoria para colecciones mutables como listas y diccionarios (`allowed_ballot_types`, `assigned_officers`). 
* **Riesgo electoral:** Si se usara copia superficial, agregar un jurado a la Mesa 2 modificaría automáticamente la lista de jurados de la Mesa 1 y de la plantilla prototipo, generando una falla crítica de integridad de datos.
* **Solución aplicada:** Se utiliza estrictamente `copy.deepcopy(self)`, lo que asegura que cada clon posea su propio espacio en memoria completamente aislado.

### 4.2 Relación con Principios SOLID
* **Single Responsibility Principle (SRP):** Cada estación sabe cómo duplicarse a sí misma de manera segura; el registro (`StationPrototypeRegistry`) se enfoca exclusivamente en la administración de las plantillas.
* **Open/Closed Principle (OCP):** Nuevos tipos de estaciones o configuraciones de mesas pueden incorporarse y registrarse en tiempo de ejecución sin alterar el código del motor electoral.
