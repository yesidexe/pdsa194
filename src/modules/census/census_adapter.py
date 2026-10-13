"""Módulo para la adaptación de censos electorales heterogéneos mediante el patrón Adapter.

===============================================================================
EXPLICACIÓN PEDAGÓGICA DEL PATRÓN ADAPTER EN ESTE MÓDULO:
===============================================================================
¿Qué problema resuelve?
En la vida real, una plataforma de votación no puede exigir que todas las entidades
(la Registraduría del Estado Civil, una universidad, o un archivo histórico legado)
entreguen sus listas de votantes exactamente con los mismos nombres de columnas o
en el mismo formato técnico.
- La Registraduría puede entregar un archivo plano CSV antiguo con columnas como 'cedula', 'nombres'.
- Una Universidad puede entregar una exportación JSON de su sistema académico con 'codigo', 'estudiante'.
- Un sistema moderno en producción puede conectarse a una base de datos relacional SQL (SQLite).

Si nuestro sistema electoral tuviese que entender cada formato directamente, el código
del núcleo (la urna, las mesas, la cabina) se llenaría de 'if/else' y se rompería cada
vez que una entidad cambie su formato.

¿Cómo lo resuelve el patrón Adapter?
1. Define un contrato único estándar llamado 'Target' (aquí: la interfaz `ICensusRegistry`).
2. El sistema electoral (la fachada y la cabina) SOLO habla con `ICensusRegistry`.
3. Creamos clases 'Adaptadoras' (`JsonCensusAdapter`, `CsvCensusAdapter`, `SqliteCensusAdapter`)
   que reciben el formato extraño o la base de datos externa y traducen todo al
   formato canónico estándar `VoterCensusRecord`.
===============================================================================
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import csv
from dataclasses import dataclass
import io
import json
from typing import Any, Dict, List, Optional

# Importamos la capa de persistencia relacional SQLite local
from src.core.database import CitizenModel, SessionLocal, init_db


@dataclass(frozen=True)
class VoterCensusRecord:
    """Ficha censal canónica e inmutable en el dominio electoral.

    Representa la información oficial estandarizada de un elector,
    independientemente de si provino de un archivo CSV, un JSON o una base de datos SQL.

    Atributos:
        document_id: Número de identificación único (Cédula o Código Estudiantil).
        full_name: Nombre completo y legal del ciudadano/estudiante.
        assigned_station_id: Código de la mesa de votación donde le corresponde sufragar.
        is_eligible: True si tiene plenos derechos políticos; False si está inhabilitado o sancionado.
        source_type: Etiqueta que identifica la fuente de procedencia (para auditoría).
    """
    document_id: str
    full_name: str
    assigned_station_id: str
    is_eligible: bool
    source_type: str


class ICensusRegistry(ABC):
    """Interfaz objetivo (Target) del Patrón Adapter.

    Define el contrato formal que el sistema electoral exige para consultar el censo.
    Cualquier fuente de datos (archivos, APIs o bases de datos) DEBE implementar
    estos métodos para poder ser utilizada en la jornada electoral.
    """

    @abstractmethod
    def is_eligible(self, document_id: str) -> bool:
        """Determina si un ciudadano está facultado legalmente para votar.

        Parámetros:
            document_id: Cédula o código de carnet a verificar.
        Retorna:
            True si existe en el censo y no tiene inhabilitaciones; False en caso contrario.
        """
        pass

    @abstractmethod
    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        """Obtiene la ficha censal canónica de un elector si existe.

        Parámetros:
            document_id: Identificador del votante.
        Retorna:
            Instancia de VoterCensusRecord con los datos estandarizados, o None si no existe.
        """
        pass

    @abstractmethod
    def get_total_registered(self) -> int:
        """Retorna el número total de electores registrados en esta fuente censal."""
        pass


class JsonCensusAdapter(ICensusRegistry):
    """Adaptador concreto para fuentes de datos en formato JSON.

    Toma una carga útil (payload) JSON con claves heterogéneas (por ejemplo
    exportaciones de APIs o servicios web institucionales) y las mapea al dominio.
    """

    def __init__(self, raw_json_payload: str | Dict[str, Any]) -> None:
        """Inicializa el adaptador procesando el texto o diccionario JSON."""
        if isinstance(raw_json_payload, str):
            data = json.loads(raw_json_payload)
        else:
            data = raw_json_payload

        # Diccionario interno en memoria para búsquedas O(1) por documento
        self._records_by_id: Dict[str, VoterCensusRecord] = {}
        self._parse_payload(data)

    def _parse_payload(self, data: Dict[str, Any]) -> None:
        """Traduce los campos heterogéneos del JSON a la entidad canónica VoterCensusRecord."""
        items: List[Dict[str, Any]] = data.get("electores", data.get("estudiantes", data.get("citizens", [])))
        for item in items:
            doc = str(item.get("documento_id", item.get("codigo", item.get("id", "")))).strip()
            name = item.get("nombre_completo", item.get("nombres", item.get("name", "Desconocido"))).strip()
            station = item.get("mesa_asignada", item.get("mesa", item.get("station", "MESA-GENERAL"))).strip()
            eligible = bool(item.get("habilitado", item.get("activo", item.get("eligible", True))))

            if doc:
                self._records_by_id[doc] = VoterCensusRecord(
                    document_id=doc,
                    full_name=name,
                    assigned_station_id=station,
                    is_eligible=eligible,
                    source_type="JSON_ADAPTER",
                )

    def is_eligible(self, document_id: str) -> bool:
        record = self._records_by_id.get(str(document_id).strip())
        return record.is_eligible if record else False

    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        return self._records_by_id.get(str(document_id).strip())

    def get_total_registered(self) -> int:
        return len(self._records_by_id)


class CsvCensusAdapter(ICensusRegistry):
    """Adaptador concreto para archivos tabulares en texto plano CSV.

    Mapea encabezados tradicionales y desordenados (e.g. volcados de Registraduría
    o planillas de Excel exportadas a CSV) al contrato oficial `ICensusRegistry`.
    """

    def __init__(self, csv_content: str, delimiter: str = ",") -> None:
        self._records_by_id: Dict[str, VoterCensusRecord] = {}
        self._parse_csv(csv_content, delimiter)

    def _parse_csv(self, csv_content: str, delimiter: str) -> None:
        """Lee y normaliza las columnas del CSV al modelo canónico."""
        reader = csv.DictReader(io.StringIO(csv_content.strip()), delimiter=delimiter)
        for row in reader:
            normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}

            doc = (
                normalized_row.get("cedula")
                or normalized_row.get("documento")
                or normalized_row.get("document_id")
                or normalized_row.get("identificacion", "")
            )
            name = (
                normalized_row.get("nombre")
                or normalized_row.get("nombre_completo")
                or normalized_row.get("nombres_apellidos")
                or normalized_row.get("full_name", "Desconocido")
            )
            station = (
                normalized_row.get("mesa")
                or normalized_row.get("mesa_asignada")
                or normalized_row.get("station_id", "MESA-GENERAL")
            )
            status_raw = (
                normalized_row.get("habilitado")
                or normalized_row.get("estado")
                or normalized_row.get("eligible", "si")
            ).lower()

            eligible = status_raw in ("si", "sí", "true", "1", "habilitado", "activo")

            if doc:
                self._records_by_id[doc] = VoterCensusRecord(
                    document_id=doc,
                    full_name=name,
                    assigned_station_id=station,
                    is_eligible=eligible,
                    source_type="CSV_ADAPTER",
                )

    def is_eligible(self, document_id: str) -> bool:
        record = self._records_by_id.get(str(document_id).strip())
        return record.is_eligible if record else False

    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        return self._records_by_id.get(str(document_id).strip())

    def get_total_registered(self) -> int:
        return len(self._records_by_id)


class SqliteCensusAdapter(ICensusRegistry):
    """Adaptador concreto para Base de Datos Relacional SQLite (Censo Oficial Registraduría).

    Este adaptador conecta directamente con el motor de base de datos local SQLite
    a través del ORM SQLAlchemy, permitiendo:
    1. Consultar en vivo la habilitación de un elector.
    2. Registrar nuevos votantes en caliente desde el panel administrativo.
    3. Habilitar o inhabilitar judicialmente a un ciudadano.
    4. Garantizar la persistencia permanente de los datos en disco ('e_voting.db').
    """

    def __init__(self, election_type: str = "NATIONAL") -> None:
        """Inicializa el adaptador asegurando la creación de tablas y filtrando por tipo de elección."""
        self.election_type = election_type.upper().strip()
        init_db()

    def is_eligible(self, document_id: str) -> bool:
        """Consulta en la base de datos SQL si el ciudadano existe y está habilitado."""
        session = SessionLocal()
        try:
            citizen = (
                session.query(CitizenModel)
                .filter(
                    CitizenModel.document_id == str(document_id).strip(),
                    CitizenModel.election_type == self.election_type,
                )
                .first()
            )
            return citizen.is_eligible if citizen else False
        finally:
            session.close()

    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        """Recupera la fila de la tabla SQL y la convierte a un VoterCensusRecord inmutable."""
        session = SessionLocal()
        try:
            citizen = (
                session.query(CitizenModel)
                .filter(
                    CitizenModel.document_id == str(document_id).strip(),
                    CitizenModel.election_type == self.election_type,
                )
                .first()
            )
            if not citizen:
                return None
            return VoterCensusRecord(
                document_id=citizen.document_id,
                full_name=citizen.full_name,
                assigned_station_id=citizen.assigned_station_id,
                is_eligible=citizen.is_eligible,
                source_type="SQLITE_DATABASE",
            )
        finally:
            session.close()

    def get_total_registered(self) -> int:
        """Cuenta el número de electores registrados en la base de datos para esta elección."""
        session = SessionLocal()
        try:
            return (
                session.query(CitizenModel)
                .filter(CitizenModel.election_type == self.election_type)
                .count()
            )
        finally:
            session.close()

    def get_all_voters(self, election_type: Optional[str] = None) -> List[VoterCensusRecord]:
        """Devuelve la lista completa de votantes registrados en la base de datos."""
        session = SessionLocal()
        target_type = (election_type or self.election_type).upper().strip()
        try:
            query = session.query(CitizenModel)
            if target_type != "ALL":
                query = query.filter(CitizenModel.election_type == target_type)
            citizens = query.order_by(CitizenModel.id.desc()).all()
            return [
                VoterCensusRecord(
                    document_id=c.document_id,
                    full_name=c.full_name,
                    assigned_station_id=c.assigned_station_id,
                    is_eligible=c.is_eligible,
                    source_type="SQLITE_DATABASE",
                )
                for c in citizens
            ]
        finally:
            session.close()

    def register_voter(
        self,
        document_id: str,
        full_name: str,
        assigned_station_id: str = "MESA-01",
        is_eligible: bool = True,
        election_type: Optional[str] = None,
    ) -> VoterCensusRecord:
        """Inscribe un nuevo ciudadano en la base de datos SQL o actualiza uno existente."""
        session = SessionLocal()
        target_type = (election_type or self.election_type).upper().strip()
        doc = str(document_id).strip()
        try:
            existing = session.query(CitizenModel).filter(CitizenModel.document_id == doc).first()
            if existing:
                existing.full_name = full_name.strip()
                existing.assigned_station_id = assigned_station_id.strip()
                existing.is_eligible = is_eligible
                existing.election_type = target_type
                session.commit()
                return VoterCensusRecord(
                    document_id=existing.document_id,
                    full_name=existing.full_name,
                    assigned_station_id=existing.assigned_station_id,
                    is_eligible=existing.is_eligible,
                    source_type="SQLITE_DATABASE",
                )

            new_citizen = CitizenModel(
                document_id=doc,
                full_name=full_name.strip(),
                assigned_station_id=assigned_station_id.strip(),
                is_eligible=is_eligible,
                election_type=target_type,
            )
            session.add(new_citizen)
            session.commit()
            return VoterCensusRecord(
                document_id=new_citizen.document_id,
                full_name=new_citizen.full_name,
                assigned_station_id=new_citizen.assigned_station_id,
                is_eligible=new_citizen.is_eligible,
                source_type="SQLITE_DATABASE",
            )
        finally:
            session.close()

    def toggle_eligibility(self, document_id: str, is_eligible: bool) -> bool:
        """Modifica el estado de habilitación política de un ciudadano en la base de datos."""
        session = SessionLocal()
        try:
            citizen = (
                session.query(CitizenModel)
                .filter(CitizenModel.document_id == str(document_id).strip())
                .first()
            )
            if not citizen:
                return False
            citizen.is_eligible = is_eligible
            session.commit()
            return True
        finally:
            session.close()
