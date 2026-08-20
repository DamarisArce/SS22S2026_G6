"""
Configuración central de la Práctica 1.

Las credenciales reales se obtienen desde el archivo .env, que no se
versiona en Git. Las rutas se calculan tomando como base la raíz del proyecto.
"""

from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "resultados"

load_dotenv(ENV_FILE)


def _required_env(name: str) -> str:
    """Obtiene una variable obligatoria o genera un error descriptivo."""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria: {name}"
        )

    return value.strip()


@dataclass(frozen=True)
class Settings:
    """Configuración utilizada por la aplicación ETL."""

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_driver: str
    db_password: str = field(repr=False)

    dataset_path: Path = (
        DATA_DIR / "dataset_vuelos_crudo.csv"
    )


def load_settings() -> Settings:
    """Construye la configuración de la aplicación."""

    try:
        port = int(_required_env("DB_PORT"))
    except ValueError as exc:
        raise RuntimeError(
            "DB_PORT debe contener un número entero."
        ) from exc

    return Settings(
        db_host=_required_env("DB_HOST"),
        db_port=port,
        db_name=_required_env("DB_NAME"),
        db_user=_required_env("DB_USER"),
        db_driver=_required_env("DB_DRIVER"),
        db_password=_required_env("MSSQL_SA_PASSWORD"),
    )


settings = load_settings()
