# Documento de Avance: Patrón de Diseño Builder

## 1. Identificación del Avance
* **Patrón de Diseño:** Builder (Creacional).
* **Elemento del Sistema:** Ensamble de Actas Oficiales de Escrutinio (`ElectoralTallyReport`) mediante `TallyReportBuilder` y `OfficialTallyReportBuilder`.
* **Ubicación del Código:** `src/modules/tally/report_builder.py`.

---

## 2. Justificación y Problema que Resuelve en el Dominio

Al finalizar una jornada de votación electrónica, el sistema debe generar el **Acta Oficial de Escrutinio y Cierre de Urnas**. Este objeto no es una estructura de datos simple; se trata de una entidad compleja compuesta por:
* Metadatos de la jornada (título oficial de la elección y jurisdicción territorial).
* Fecha y hora exacta de emisión.
* Lote de identificadores de las mesas de votación escrutadas y consolidadas.
* Desglose numérico de votos válidos por candidato, votos en blanco y votos nulos.
* Cómputo global y totalizado de sufragios.
* Registro de firmas digitales o códigos de autenticación de los jurados de mesa.
* Sello criptográfico digital (hash SHA-256) generado sobre el contenido del acta para garantizar inmutabilidad.

### El Antipatrón Evitado: Constructor Telescópico (*Telescoping Constructor*)
Si intentáramos construir este objeto directamente mediante el constructor de clase `__init__`, caeríamos en el antipatrón de constructor telescópico:
```python
# ANTIPATRÓN: Parámetros confusos, propensos a error de orden y difíciles de mantener
reporte = ElectoralTallyReport("Elecciones 2026", "Nacional", datetime.now(), ["M-01", "M-02"], {...}, 10, 5, 1200, ["JUR-1", "JUR-2"], "a8fbc...")
```
El cliente se vería forzado a conocer el orden exacto de decenas de argumentos, muchos de ellos opcionales o dependientes de pasos de cálculo intermedios.

El patrón **Builder** separa el proceso de construcción paso a paso de un objeto complejo de su representación final, permitiendo que el mismo proceso de construcción produzca representaciones válidas e inmutables.

---

## 3. Implementación Técnica en el Código

La solución adopta la variante moderna **Fluent Builder** (encadenamiento de métodos) complementada con inmutabilidad en el producto final (`@dataclass(frozen=True)`).

### 3.1 Producto Complejo e Inmutable (`ElectoralTallyReport`)

```python
@dataclass(frozen=True)
class ElectoralTallyReport:
    """Producto complejo e inmutable que representa el acta final de escrutinio."""
    election_title: str
    jurisdiction: str
    generated_at: datetime
    table_ids: List[str]
    candidate_votes: Dict[str, int]
    blank_votes: int
    null_votes: int
    total_votes: int
    officer_signatures: List[str]
    integrity_hash: str

    def to_formatted_summary(self) -> str:
        # Formateo legible y legal del acta para auditoría
        ...
```

### 3.2 Constructor Abstracto y Concreto (`TallyReportBuilder` / `OfficialTallyReportBuilder`)

```python
import hashlib
import json

class TallyReportBuilder(ABC):
    @abstractmethod
    def reset(self) -> "TallyReportBuilder": pass

    @abstractmethod
    def set_header(self, election_title: str, jurisdiction: str) -> "TallyReportBuilder": pass

    @abstractmethod
    def add_table_batch(self, table_ids: List[str]) -> "TallyReportBuilder": pass

    @abstractmethod
    def set_votes(self, candidate_votes: Dict[str, int], blank_votes: int, null_votes: int) -> "TallyReportBuilder": pass

    @abstractmethod
    def add_officer_signature(self, signature_code: str) -> "TallyReportBuilder": pass

    @abstractmethod
    def build(self) -> ElectoralTallyReport: pass


class OfficialTallyReportBuilder(TallyReportBuilder):
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> "OfficialTallyReportBuilder":
        self._election_title = "Jornada Electoral"
        self._jurisdiction = "Nacional"
        self._table_ids = []
        self._candidate_votes = {}
        self._blank_votes = 0
        self._null_votes = 0
        self._officer_signatures = []
        return self

    def set_header(self, election_title: str, jurisdiction: str) -> "OfficialTallyReportBuilder":
        self._election_title = election_title
        self._jurisdiction = jurisdiction
        return self

    def add_table_batch(self, table_ids: List[str]) -> "OfficialTallyReportBuilder":
        self._table_ids.extend(table_ids)
        return self

    def set_votes(self, candidate_votes: Dict[str, int], blank_votes: int, null_votes: int) -> "OfficialTallyReportBuilder":
        self._candidate_votes = dict(candidate_votes)
        self._blank_votes = max(0, blank_votes)
        self._null_votes = max(0, null_votes)
        return self

    def add_officer_signature(self, signature_code: str) -> "OfficialTallyReportBuilder":
        if signature_code not in self._officer_signatures:
            self._officer_signatures.append(signature_code)
        return self

    def build(self) -> ElectoralTallyReport:
        total = sum(self._candidate_votes.values()) + self._blank_votes + self._null_votes
        now = datetime.utcnow()

        # Sellado criptográfico automático del estado final
        payload = {
            "title": self._election_title,
            "jurisdiction": self._jurisdiction,
            "timestamp": now.isoformat(),
            "tables": sorted(self._table_ids),
            "candidate_votes": self._candidate_votes,
            "blank": self._blank_votes,
            "null": self._null_votes,
            "total": total,
            "signatures": self._officer_signatures,
        }
        hash_digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return ElectoralTallyReport(
            election_title=self._election_title,
            jurisdiction=self._jurisdiction,
            generated_at=now,
            table_ids=list(self._table_ids),
            candidate_votes=dict(self._candidate_votes),
            blank_votes=self._blank_votes,
            null_votes=self._null_votes,
            total_votes=total,
            officer_signatures=list(self._officer_signatures),
            integrity_hash=hash_digest,
        )
```

### 3.3 Director de Construcción (`TallyReportDirector`)
Permite automatizar variantes predefinidas del producto, como un boletín preliminar de divulgación rápida:

```python
class TallyReportDirector:
    def __init__(self, builder: TallyReportBuilder) -> None:
        self._builder = builder

    def construct_preliminary_bulletin(
        self, title: str, jurisdiction: str, tables: List[str], votes: Dict[str, int]
    ) -> ElectoralTallyReport:
        return (
            self._builder.reset()
            .set_header(f"Boletín Preliminar - {title}", jurisdiction)
            .add_table_batch(tables)
            .set_votes(candidate_votes=votes, blank_votes=0, null_votes=0)
            .build()
        )
```

---

## 4. Análisis de Ingeniería de Software

### 4.1 Inmutabilidad Garantizada
Al construirse el objeto con `frozen=True`, ninguna propiedad del acta puede modificarse a posteriori en memoria. Si un atacante o error intentara alterar un cómputo, Python generará una excepción inmediata.

### 4.2 Sellado Criptográfico Integrado
El método `build()` calcula de forma determinista el resumen criptográfico SHA-256 de todas las partes ensambladas. El acta nace sellada digitalmente.

### 4.3 Relación con Principios SOLID
* **Single Responsibility Principle (SRP):** El reporte sólo modela los datos consolidados; el constructor se encarga exclusivamente de las reglas de ensamble, validación de rangos y firmado.
* **Open/Closed Principle (OCP):** Es posible introducir nuevos formatos de acta (por ejemplo, `AuditedJsonTallyReportBuilder` o `InternationalTallyReportBuilder`) implementando `TallyReportBuilder` sin alterar el código cliente existente.
