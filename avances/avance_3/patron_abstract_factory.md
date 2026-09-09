# Avance Patrón de Diseño Abstract Factory

## 1. Identificación del Avance
* **Patrón de Diseño:** Abstract Factory (Creacional).
* **Elemento del Sistema:** Familias de Componentes Electorales (`ElectoralFamilyFactory`).
* **Ubicación del Código:** `src/modules/election/election_factory.py`.

---

## 2. Justificación y Problema que Resuelve en el Dominio

Un proceso electoral no consiste únicamente en la emisión aislada de un voto; comprende una serie de componentes dependientes que deben guardar coherencia jurídica y operativa entre sí según la jurisdicción o modalidad de la elección:
1. **Validación de Identidad (`CredentialValidator`):** Un voto nacional requiere cédula de ciudadanía, mientras que una elección universitaria requiere código o carnet estudiantil.
2. **Encabezado Institucional de la Papeleta (`BallotHeader`):** Cada tipo de elección requiere un membrete oficial específico (Registraduría Nacional vs Consejo Superior Universitario).
3. **Regla de Escrutinio (`TallyRule`):** Una elección presidencial puede exigir una mayoría absoluta (>50%) o determinar balotaje (segunda vuelta), mientras que una elección universitaria se rige habitualmente por mayoría simple (pluralidad de votos).

Si el sistema permitiera instanciar estos componentes de forma arbitraria y cruzada (por ejemplo, validar un carnet estudiantil en una papeleta con el escudo nacional y reglas de mayoría absoluta presidencial), se generarían incongruencias lógicas y jurídicas graves.

El patrón **Abstract Factory** proporciona una interfaz única para crear **familias completas de objetos relacionados o dependientes** sin especificar sus clases concretas, garantizando que todos los elementos utilizados pertenezcan a la misma modalidad electoral.

---

## 3. Implementación Técnica en el Código

### 3.1 Productos Abstractos y Familias Concretas

```python
from abc import ABC, abstractmethod
from typing import Dict

# --- Producto A: Validador de Credencial ---
class CredentialValidator(ABC):
    @abstractmethod
    def validate_credential(self, document_id: str) -> bool:
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        pass

class NationalCitizenValidator(CredentialValidator):
    def validate_credential(self, document_id: str) -> bool:
        return document_id.isdigit() and 6 <= len(document_id) <= 10

    def get_document_type(self) -> str:
        return "Cédula de Ciudadanía (C.C.)"

class StudentCodeValidator(CredentialValidator):
    def validate_credential(self, document_id: str) -> bool:
        return len(document_id) >= 5 and any(c.isdigit() for c in document_id)

    def get_document_type(self) -> str:
        return "Código de Carnet Estudiantil"


# --- Producto B: Encabezado de Papeleta ---
class BallotHeader(ABC):
    @abstractmethod
    def render_header(self) -> str:
        pass

class NationalBallotHeader(BallotHeader):
    def render_header(self) -> str:
        return "REPÚBLICA DE COLOMBIA - REGISTRADURÍA NACIONAL DEL ESTADO CIVIL"

class UniversityBallotHeader(BallotHeader):
    def render_header(self) -> str:
        return "UNIVERSIDAD DE INVESTIGACIÓN Y DESARROLLO - CONSEJO SUPERIOR"


# --- Producto C: Regla de Escrutinio ---
class TallyRule(ABC):
    @abstractmethod
    def evaluate_winner(self, votes_summary: Dict[str, int]) -> str:
        pass

class AbsoluteMajorityTallyRule(TallyRule):
    def evaluate_winner(self, votes_summary: Dict[str, int]) -> str:
        total = sum(votes_summary.values())
        if total == 0:
            return "Sin votos registrados"
        for option, count in votes_summary.items():
            if count > total / 2:
                return f"Ganador directo por Mayoría Absoluta (>50%): {option}"
        return "No hay mayoría absoluta: Requiere Segunda Vuelta (Balotaje)"

class SimplePluralityTallyRule(TallyRule):
    def evaluate_winner(self, votes_summary: Dict[str, int]) -> str:
        if not votes_summary:
            return "Sin votos registrados"
        winner = max(votes_summary, key=votes_summary.get)
        return f"Ganador electo por Mayoría Simple: {winner} ({votes_summary[winner]} votos)"
```

### 3.2 Fábrica Abstracta y Fábricas Concretas

```python
class ElectoralFamilyFactory(ABC):
    """Interfaz de la fábrica abstracta para familias de componentes electorales."""

    @abstractmethod
    def create_validator(self) -> CredentialValidator:
        pass

    @abstractmethod
    def create_header(self) -> BallotHeader:
        pass

    @abstractmethod
    def create_tally_rule(self) -> TallyRule:
        pass

class NationalElectionFactory(ElectoralFamilyFactory):
    """Produce exclusivamente la familia nacional de componentes."""
    def create_validator(self) -> CredentialValidator:
        return NationalCitizenValidator()

    def create_header(self) -> BallotHeader:
        return NationalBallotHeader()

    def create_tally_rule(self) -> TallyRule:
        return AbsoluteMajorityTallyRule()

class UniversityElectionFactory(ElectoralFamilyFactory):
    """Produce exclusivamente la familia universitaria de componentes."""
    def create_validator(self) -> CredentialValidator:
        return StudentCodeValidator()

    def create_header(self) -> BallotHeader:
        return UniversityBallotHeader()

    def create_tally_rule(self) -> TallyRule:
        return SimplePluralityTallyRule()
```

---

## 4. Análisis de Ingeniería de Software

### 4.1 Coherencia de Productos
El mayor beneficio de Abstract Factory en este dominio es garantizar que nunca se mezclen productos de ámbitos distintos. El cliente simplemente solicita una `ElectoralFamilyFactory` y recibe objetos que están garantizados para operar en armonía conceptual y técnica.

### 4.2 Diferencia Formal con Factory Method
| Criterio | Factory Method | Abstract Factory |
| :--- | :--- | :--- |
| **Alcance** | Crea **un solo producto** (`Ballot`). | Crea **familias completas de productos relacionados** (`Validator`, `Header`, `TallyRule`). |
| **Mecanismo** | Herencia de clases (`create_ballot`). | Composición de interfaces a nivel de objeto. |
| **Extensibilidad** | Se extiende añadiendo una subclase creadora. | Se extiende añadiendo una nueva fábrica de familia completa. |

### 4.3 Relación con SOLID
* **Open/Closed Principle (OCP):** Es posible introducir una nueva modalidad electoral (por ejemplo, `UnionElectionFactory` para sindicatos) implementando la interfaz abstracta, sin modificar el código que consume los componentes.
* **Dependency Inversion Principle (DIP):** El subsistema que orquesta la votación depende únicamente de la abstracción `ElectoralFamilyFactory` y de las interfaces abstractas de cada producto, nunca de sus clases concretas.
