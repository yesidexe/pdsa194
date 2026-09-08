"""Punto de entrada demostrativo de los patrones creacionales implementados."""
from src.core.config import ElectoralConfigManager
from src.modules.voting.ballot_factory import (
    CandidateBallotCreator,
    ReferendumBallotCreator,
    BlankBallotCreator,
)
from src.modules.election.election_factory import (
    NationalElectionFactory,
    UniversityElectionFactory,
    ElectoralFamilyFactory,
)


def run_singleton_demo() -> None:
    print("=" * 60)
    print("1. DEMOSTRACIÓN PATRÓN SINGLETON")
    print("=" * 60)

    config_a = ElectoralConfigManager(
        institution_name="Registraduría Nacional",
        election_title="Elecciones Presidenciales 2026",
    )
    config_b = ElectoralConfigManager(
        institution_name="Texto Ignorado",
        election_title="Título Ignorado",
    )

    print(f"Instancia A ID: {id(config_a)} | Institución: {config_a.institution_name}")
    print(f"Instancia B ID: {id(config_b)} | Institución: {config_b.institution_name}")
    print(f"¿Son exactamente el mismo objeto en memoria? {'SÍ' if config_a is config_b else 'NO'}")

    config_a.open_voting()
    print(f"Estado tras abrir urna desde A -> config_b.is_open: {config_b.is_open}\n")


def run_factory_method_demo() -> None:
    print("=" * 60)
    print("2. DEMOSTRACIÓN PATRÓN FACTORY METHOD")
    print("=" * 60)

    candidate_creator = CandidateBallotCreator()
    referendum_creator = ReferendumBallotCreator()
    blank_creator = BlankBallotCreator()

    ballot_1 = candidate_creator.issue_ballot(
        candidate_id="CAND-01",
        candidate_name="Dra. Elena Gómez",
        party_name="Movimiento Futuro",
    )
    ballot_2 = referendum_creator.issue_ballot(
        question_code="REF-01",
        decision="SI",
    )
    ballot_3 = blank_creator.issue_ballot(category="Presidencial")

    for b in (ballot_1, ballot_2, ballot_3):
        print(f"[{type(b).__name__}] ID: {b.ballot_id[:8]}... | Opción: {b.get_selection()} | Hora: {b.issued_at.strftime('%H:%M:%S')}")
    print()


def run_abstract_factory_demo() -> None:
    print("=" * 60)
    print("3. DEMOSTRACIÓN PATRÓN ABSTRACT FACTORY")
    print("=" * 60)

    def execute_election_flow(factory: ElectoralFamilyFactory, mock_votes: dict) -> None:
        validator = factory.create_validator()
        header = factory.create_header()
        rule = factory.create_tally_rule()

        print(f"Encabezado Oficial: {header.render_header()}")
        print(f"Tipo de Documento Requerido: {validator.get_document_type()}")
        print(f"Resultado del Escrutinio: {rule.evaluate_winner(mock_votes)}")
        print("-" * 50)

    print("--- Contexto A: Elección Nacional ---")
    national_votes = {"Candidato A": 5200, "Candidato B": 4100, "En Blanco": 300}
    execute_election_flow(NationalElectionFactory(), national_votes)

    print("--- Contexto B: Elección Universitaria ---")
    student_votes = {"Lista Estudiantil 1": 350, "Lista Estudiantil 2": 420, "En Blanco": 30}
    execute_election_flow(UniversityElectionFactory(), student_votes)


if __name__ == "__main__":
    run_singleton_demo()
    run_factory_method_demo()
    run_abstract_factory_demo()
