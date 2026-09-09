# Avance Patrón de Diseño Factory Method

## 1. Identificación del Avance
* **Patrón de Diseño:** Factory Method (Creacional).
* **Elemento del Sistema:** Jerarquía de Papeletas Electorales (`Ballot`) y Emisores (`BallotCreator`).
* **Ubicación del Código:** `src/modules/voting/ballot_factory.py`.

---

## 2. Justificación y Problema que Resuelve en el Dominio

Un sistema electoral moderno no maneja un único tipo de voto. En una misma plataforma o jornada pueden coexistir distintos tipos de papeletas de votación:
1. **Papeleta por Candidato Nominal:** Contiene identificación del postulante, nombre y partido político.
2. **Papeleta de Referéndum o Consulta Popular:** Contiene el código de la pregunta sometida a votación y la respuesta del ciudadano (SÍ, NO, ABSTENCIÓN).
3. **Papeleta de Voto en Blanco:** Reconocida jurídicamente, sin candidatos asignados pero sujeta a escrutinio formal.

Si el módulo de votación creara estas papeletas directamente mediante condicionales `if/else` o con `new` esparcidos por la lógica de negocio, se violaría el principio **Abierto/Cerrado (OCP)**. Cada vez que se incorporase una nueva modalidad (por ejemplo, voto con lista cerrada preferente), habría que modificar clases existentes y arriesgar la estabilidad del sistema.

El patrón **Factory Method** resuelve este problema definiendo una interfaz común para la creación de un objeto, delegando en subclases creadoras específicas la decisión de qué producto concreto instanciar.

---

## 3. Implementación Técnica en el Código

La implementación separa rigurosamente la jerarquía del **Producto** (`Ballot`) de la jerarquía del **Creador** (`BallotCreator`).

### 3.1 Jerarquía del Producto (`Ballot` y subclases)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class Ballot(ABC):
    """Producto abstracto base para cualquier sufragio emitido."""
    ballot_id: str
    issued_at: datetime

    @abstractmethod
    def get_selection(self) -> str:
        """Devuelve la opción seleccionada de forma legible."""
        pass

@dataclass(frozen=True)
class CandidateBallot(Ballot):
    """Papeleta emitida para un candidato o fórmula nominal."""
    candidate_id: str
    candidate_name: str
    party_name: str

    def get_selection(self) -> str:
        return f"{self.candidate_name} ({self.party_name})"

@dataclass(frozen=True)
class ReferendumBallot(Ballot):
    """Papeleta para consultas populares o referéndums temáticos."""
    question_code: str
    decision: str

    def get_selection(self) -> str:
        return f"[{self.question_code}] {self.decision.upper()}"

@dataclass(frozen=True)
class BlankBallot(Ballot):
    """Papeleta en blanco con validez legal."""
    category: str

    def get_selection(self) -> str:
        return f"VOTO EN BLANCO - {self.category.upper()}"
```

### 3.2 Jerarquía del Creador (`BallotCreator` y subclases)

```python
import uuid

class BallotCreator(ABC):
    """Creador abstracto que define el Factory Method y la lógica de emisión."""

    @abstractmethod
    def create_ballot(self, **kwargs) -> Ballot:
        """Factory Method puro a implementar por cada creador concreto."""
        pass

    def issue_ballot(self, **kwargs) -> Ballot:
        """Método de negocio desacoplado de los detalles de instanciación."""
        ballot = self.create_ballot(**kwargs)
        return ballot

class CandidateBallotCreator(BallotCreator):
    def create_ballot(self, **kwargs) -> CandidateBallot:
        return CandidateBallot(
            ballot_id=str(uuid.uuid4()),
            issued_at=datetime.utcnow(),
            candidate_id=kwargs["candidate_id"],
            candidate_name=kwargs["candidate_name"],
            party_name=kwargs.get("party_name", "Independiente"),
        )

class ReferendumBallotCreator(BallotCreator):
    def create_ballot(self, **kwargs) -> ReferendumBallot:
        return ReferendumBallot(
            ballot_id=str(uuid.uuid4()),
            issued_at=datetime.utcnow(),
            question_code=kwargs["question_code"],
            decision=kwargs["decision"],
        )

class BlankBallotCreator(BallotCreator):
    def create_ballot(self, **kwargs) -> BlankBallot:
        return BlankBallot(
            ballot_id=str(uuid.uuid4()),
            issued_at=datetime.utcnow(),
            category=kwargs.get("category", "General"),
        )
```

---

## 4. Análisis de Ingeniería de Software

### 4.1 Principio Abierto/Cerrado (OCP)
El sistema queda **abierto a la extensión pero cerrado a la modificación**: si el día de mañana la normativa electoral exige un nuevo tipo de tarjetón (ej. voto para consulta indígena), solo se crean dos clases: `IndigenousBallot` y `IndigenousBallotCreator`. No se modifica ni una sola línea del código existente.

### 4.2 Inmutabilidad de los Sufragios
Los productos heredan de `@dataclass(frozen=True)`. Esto asegura que una vez emitido el voto, sus atributos no puedan ser alterados en memoria, alineándose con el principio de integridad del sufragio.

### 4.3 Desacoplamiento de la Operación de Negocio
El método `issue_ballot()` en la clase base abstracta utiliza el producto retornado por `create_ballot()`, operando únicamente contra la abstracción `Ballot`.
