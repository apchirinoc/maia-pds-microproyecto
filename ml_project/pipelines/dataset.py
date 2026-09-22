"""Particion determinista del dataset y congelado de snapshots.

Patron «Repeatable Splitting» (Machine Learning Design Patterns, cap. 6).

El motivo de que este modulo exista es una fuga de datos latente del producto:
la plataforma permite que un administrador promueva imagenes cargadas por
usuarios al dataset de entrenamiento. Con un `train_test_split(random_state=..)`
la particion se recalcula sobre la lista completa cada vez, asi que al crecer el
dataset una imagen que estuvo en entrenamiento puede aparecer en prueba en el
snapshot siguiente. Las metricas se inflan sin que nada falle de forma visible.

La solucion es no derivar la particion del orden ni del tamano de la lista, sino
del identificador estable de cada imagen: `bucket = sha256(salt|clase|id) % N`.
La pertenencia de una imagen a train o test es entonces una funcion pura de su
identificador y del `salt`, reproducible en cualquier maquina, en cualquier
momento y con cualquier subconjunto del dataset.

El `salt` forma parte de la definicion del split: cambiarlo es declarar un split
nuevo, no reproducir el anterior.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal

from pipelines.config import TUMOR_CLASSES

Particion = Literal["train", "test"]

PARTICIONES: Final[tuple[Particion, ...]] = ("train", "test")

DEFAULT_SALT: Final[str] = "brainneuroscan-split-v1"
"""Salt por defecto del split productivo.

Se versiona en el nombre a proposito: si alguna vez hay que rebarajar el
dataset, se publica `-v2` y queda constancia de que las metricas anteriores y
las nuevas no son comparables.
"""

DEFAULT_TRAIN_FRACTION: Final[float] = 0.81
DEFAULT_BUCKETS: Final[int] = 1_000_000


class FugaDeDatosError(RuntimeError):
    """Una imagen aparece en entrenamiento de un snapshot y en prueba de otro.

    Es un error de integridad del experimento, no una condicion recuperable:
    cualquier metrica calculada sobre esa combinacion de snapshots esta
    contaminada y el entrenamiento debe detenerse.
    """


@dataclass(frozen=True)
class SplitConfig:
    """Definicion completa y serializable de un split.

    Dos ejecuciones con el mismo `SplitConfig` producen exactamente la misma
    particion; con configuraciones distintas producen splits distintos y la
    huella lo hace evidente. Por eso viaja dentro del snapshot: sin ella, la
    particion no es reproducible aunque se conserven los identificadores.
    """

    salt: str = DEFAULT_SALT
    train_fraction: float = DEFAULT_TRAIN_FRACTION
    buckets: int = DEFAULT_BUCKETS

    def __post_init__(self) -> None:
        if not self.salt:
            raise ValueError("salt no puede estar vacio")
        if not 0.0 < self.train_fraction < 1.0:
            raise ValueError("train_fraction debe estar en el intervalo abierto (0, 1)")
        if self.buckets < 100:
            raise ValueError("buckets debe ser al menos 100 para aproximar la fraccion")

    @property
    def umbral(self) -> int:
        """Primer bucket que ya pertenece a prueba.

        Se calcula a partir de la fraccion para que la frontera entre
        particiones sea un entero fijo y no dependa de aritmetica en coma
        flotante repetida imagen a imagen.
        """
        return round(self.train_fraction * self.buckets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "salt": self.salt,
            "train_fraction": self.train_fraction,
            "buckets": self.buckets,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SplitConfig:
        return cls(
            salt=str(data["salt"]),
            train_fraction=float(data["train_fraction"]),
            buckets=int(data["buckets"]),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def fingerprint(self) -> str:
        """Huella corta de la definicion del split.

        Permite comparar de un vistazo si dos snapshots comparten reglas de
        particion sin inspeccionar campo por campo.
        """
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class RegistroImagen:
    """Par (identificador estable, clase) que entra en la particion.

    El identificador debe ser estable de por vida: el hash de los bytes de la
    imagen o el UUID de la fila en Postgres. Nunca la ruta del fichero ni el
    indice en una lista, porque ambos cambian al reorganizar el dataset y con
    ellos cambiaria la particion.
    """

    identificador: str
    clase: str

    def __post_init__(self) -> None:
        if not self.identificador:
            raise ValueError("identificador no puede estar vacio")
        if self.clase not in TUMOR_CLASSES:
            raise ValueError(
                f"clase desconocida: {self.clase!r}; se esperaba una de {TUMOR_CLASSES}"
            )


def bucket_estable(identificador: str, clase: str, config: SplitConfig | None = None) -> int:
    """Mapea una imagen a un bucket uniforme en [0, buckets).

    La clase entra en el material hasheado a proposito: da a cada clase su
    propio flujo pseudoaleatorio independiente, que es la forma de estratificar
    sin romper el determinismo. Ver `particionar` para el razonamiento completo.
    """
    cfg = config or SplitConfig()
    material = f"{cfg.salt}|{clase}|{identificador}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    # 8 bytes bastan: 2**64 es varios ordenes de magnitud mayor que `buckets`,
    # asi que el sesgo del modulo es despreciable frente al ruido binomial.
    return int.from_bytes(digest[:8], "big") % cfg.buckets


def asignar_particion(
    identificador: str, clase: str, config: SplitConfig | None = None
) -> Particion:
    """Decide la particion de una sola imagen, sin ver el resto del dataset.

    Que la decision no dependa de los demas registros es precisamente lo que
    hace que anadir imagenes nuevas no reasigne las existentes.
    """
    cfg = config or SplitConfig()
    return "train" if bucket_estable(identificador, clase, cfg) < cfg.umbral else "test"


@dataclass(frozen=True)
class ParticionDataset:
    """Resultado de particionar una coleccion de registros."""

    train: tuple[RegistroImagen, ...]
    test: tuple[RegistroImagen, ...]
    config: SplitConfig = field(default_factory=SplitConfig)

    @property
    def total(self) -> int:
        return len(self.train) + len(self.test)

    def identificadores(self, particion: Particion) -> frozenset[str]:
        registros = self.train if particion == "train" else self.test
        return frozenset(registro.identificador for registro in registros)

    def conteos_por_clase(self) -> dict[str, dict[str, int]]:
        """Conteos (clase x particion) para todas las clases del catalogo.

        Incluye las clases con cero imagenes para que la ausencia de una clase
        sea visible en el snapshot en lugar de pasar desapercibida.
        """
        conteos = {clase: {"train": 0, "test": 0} for clase in TUMOR_CLASSES}
        for nombre in PARTICIONES:
            registros = self.train if nombre == "train" else self.test
            for registro in registros:
                conteos[registro.clase][nombre] += 1
        return conteos

    def proporcion_train_por_clase(self) -> dict[str, float]:
        """Fraccion de entrenamiento observada en cada clase presente."""
        proporciones: dict[str, float] = {}
        for clase, conteo in self.conteos_por_clase().items():
            presentes = conteo["train"] + conteo["test"]
            if presentes:
                proporciones[clase] = conteo["train"] / presentes
        return proporciones


def particionar(
    registros: Iterable[RegistroImagen], config: SplitConfig | None = None
) -> ParticionDataset:
    """Reparte los registros en train/test de forma estratificada y repetible.

    Como se combinan estratificacion y hashing determinista: en lugar de contar
    cuantas imagenes lleva cada clase -lo que haria depender la decision del
    resto del dataset y reasignaria imagenes al crecer-, se hashea *dentro* de
    cada clase incluyendo la clase en el material del hash. Cada clase recibe
    asi un flujo uniforme e independiente sobre el mismo umbral, de modo que la
    fraccion de entrenamiento converge a `train_fraction` clase por clase y una
    mala racha en una clase no arrastra a las demas.

    Se renuncia a que las proporciones sean exactas -imposible sin mirar el
    conjunto completo- a cambio de que la asignacion de cada imagen sea fija.
    La desviacion es la del muestreo binomial: con ~1.600 imagenes por clase,
    del orden de un punto porcentual.

    La salida se ordena por identificador para que la huella del snapshot no
    dependa del orden de entrada.
    """
    cfg = config or SplitConfig()
    unicos: dict[str, RegistroImagen] = {}
    for registro in registros:
        previo = unicos.get(registro.identificador)
        if previo is not None and previo.clase != registro.clase:
            raise ValueError(
                f"identificador {registro.identificador!r} aparece con dos clases: "
                f"{previo.clase!r} y {registro.clase!r}"
            )
        unicos[registro.identificador] = registro

    train: list[RegistroImagen] = []
    test: list[RegistroImagen] = []
    for registro in sorted(unicos.values(), key=lambda item: item.identificador):
        destino = asignar_particion(registro.identificador, registro.clase, cfg)
        (train if destino == "train" else test).append(registro)

    return ParticionDataset(train=tuple(train), test=tuple(test), config=cfg)


def _huella_contenido(
    train: Sequence[RegistroImagen], test: Sequence[RegistroImagen], config: SplitConfig
) -> str:
    """SHA-256 sobre la composicion exacta del dataset.

    Se hashea la terna (particion, clase, identificador) ordenada mas la
    definicion del split: dos snapshots con la misma huella contienen las
    mismas imagenes, en las mismas clases y bajo las mismas reglas. Cualquier
    imagen anadida, retirada o reetiquetada cambia la huella, que es lo que
    convierte al snapshot en una referencia citable desde un run de MLflow.
    """
    lineas = sorted(
        f"{nombre}\t{registro.clase}\t{registro.identificador}"
        for nombre, registros in (("train", train), ("test", test))
        for registro in registros
    )
    hasher = hashlib.sha256()
    hasher.update(config.to_json().encode("utf-8"))
    for linea in lineas:
        hasher.update(b"\n")
        hasher.update(linea.encode("utf-8"))
    return hasher.hexdigest()


@dataclass(frozen=True)
class DatasetSnapshot:
    """Composicion congelada del dataset en un instante concreto.

    Corresponde a una fila de `dataset_snapshots` en Postgres. Guarda los
    identificadores ademas de los conteos porque el guard anti-fuga necesita
    comparar pertenencias imagen a imagen entre snapshots; con conteos
    agregados la fuga seria indetectable.
    """

    snapshot_id: str
    creado_en: str
    train: tuple[RegistroImagen, ...]
    test: tuple[RegistroImagen, ...]
    config: SplitConfig = field(default_factory=SplitConfig)

    @classmethod
    def desde_particion(
        cls,
        particion: ParticionDataset,
        snapshot_id: str | None = None,
        creado_en: datetime | None = None,
    ) -> DatasetSnapshot:
        """Congela una particion.

        Si no se da `snapshot_id` se deriva de la huella del contenido: el
        mismo dataset produce siempre el mismo identificador aunque se congele
        en fechas distintas, y dos datasets distintos nunca lo comparten.
        """
        huella = _huella_contenido(particion.train, particion.test, particion.config)
        momento = creado_en or datetime.now(timezone.utc)
        return cls(
            snapshot_id=snapshot_id or f"ds-{huella[:12]}",
            creado_en=momento.astimezone(timezone.utc).isoformat(),
            train=tuple(particion.train),
            test=tuple(particion.test),
            config=particion.config,
        )

    @property
    def huella(self) -> str:
        """SHA-256 del contenido; no incluye ni la fecha ni el identificador."""
        return _huella_contenido(self.train, self.test, self.config)

    @property
    def total(self) -> int:
        return len(self.train) + len(self.test)

    def identificadores(self, particion: Particion) -> frozenset[str]:
        registros = self.train if particion == "train" else self.test
        return frozenset(registro.identificador for registro in registros)

    def conteos_por_clase(self) -> dict[str, dict[str, int]]:
        return ParticionDataset(self.train, self.test, self.config).conteos_por_clase()

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "creado_en": self.creado_en,
            "config": self.config.to_dict(),
            "conteos": self.conteos_por_clase(),
            "total": self.total,
            "huella": self.huella,
            "train": [[r.identificador, r.clase] for r in self.train],
            "test": [[r.identificador, r.clase] for r in self.test],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DatasetSnapshot:
        """Reconstruye un snapshot y verifica que no haya sido manipulado.

        La huella se recalcula sobre el contenido en lugar de confiar en la que
        venga en el JSON: un snapshot editado a mano deja de ser una referencia
        valida para un experimento.
        """
        snapshot = cls(
            snapshot_id=str(data["snapshot_id"]),
            creado_en=str(data["creado_en"]),
            train=tuple(RegistroImagen(str(i), str(c)) for i, c in data["train"]),
            test=tuple(RegistroImagen(str(i), str(c)) for i, c in data["test"]),
            config=SplitConfig.from_dict(data["config"]),
        )
        esperada = data.get("huella")
        if esperada is not None and esperada != snapshot.huella:
            raise ValueError(
                f"huella inconsistente para {snapshot.snapshot_id}: "
                f"declarada {esperada}, recalculada {snapshot.huella}"
            )
        return snapshot

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> DatasetSnapshot:
        return cls.from_dict(json.loads(raw))


def verificar_sin_solapamiento(anterior: DatasetSnapshot, actual: DatasetSnapshot) -> None:
    """Comprueba que ninguna imagen cruce la frontera train/test entre snapshots.

    Es el control del patron: si el hashing determinista funciona esta funcion
    nunca dispara, pero cuando alguien reintroduce un `random_state` o
    reetiqueta una imagen, la fuga se detecta aqui y no en unas metricas
    sospechosamente buenas.
    """
    cruces = {
        "train->test": anterior.identificadores("train") & actual.identificadores("test"),
        "test->train": anterior.identificadores("test") & actual.identificadores("train"),
    }
    detalles = [
        f"{sentido}: {len(ids)} imagenes ({', '.join(sorted(ids)[:5])}"
        f"{', ...' if len(ids) > 5 else ''})"
        for sentido, ids in cruces.items()
        if ids
    ]
    if detalles:
        raise FugaDeDatosError(
            f"Fuga entre snapshots {anterior.snapshot_id} y {actual.snapshot_id} -> "
            + "; ".join(detalles)
        )


def verificar_snapshot_consistente(snapshot: DatasetSnapshot) -> None:
    """Comprueba la coherencia interna: nada puede estar en train y en test.

    Un snapshot construido a mano -importado o migrado desde un split antiguo-
    puede violar esto aunque la funcion de hashing sea correcta.
    """
    solapadas = snapshot.identificadores("train") & snapshot.identificadores("test")
    if solapadas:
        raise FugaDeDatosError(
            f"El snapshot {snapshot.snapshot_id} tiene {len(solapadas)} imagenes "
            f"en ambas particiones: {', '.join(sorted(solapadas)[:5])}"
        )


def guard_antes_de_entrenar(
    actual: DatasetSnapshot, historicos: Iterable[DatasetSnapshot] = ()
) -> DatasetSnapshot:
    """Guard a ejecutar al inicio del entrenamiento; devuelve el snapshot validado.

    Se coloca antes de cargar una sola imagen para que un dataset contaminado
    aborte el run en segundos, en lugar de producir un modelo con metricas
    infladas que alguien acabara promoviendo a champion.
    """
    verificar_snapshot_consistente(actual)
    for previo in historicos:
        verificar_snapshot_consistente(previo)
        verificar_sin_solapamiento(previo, actual)
    return actual
