"""Pruebas del patron «Repeatable Splitting» sobre `pipelines.dataset`.

La propiedad que se defiende aqui no es que el split sea correcto una vez, sino
que siga siendo el mismo cuando el dataset crece o se reordena: ese es el
escenario real del producto, donde un administrador promueve imagenes de
usuarios al dataset de entrenamiento.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone

import pytest

from pipelines.config import TUMOR_CLASSES
from pipelines.dataset import (
    DatasetSnapshot,
    FugaDeDatosError,
    ParticionDataset,
    RegistroImagen,
    SplitConfig,
    asignar_particion,
    guard_antes_de_entrenar,
    particionar,
    verificar_sin_solapamiento,
    verificar_snapshot_consistente,
)

# Composicion real del dataset de BrainNeuroScan.
CONTEO_REAL: dict[str, int] = {
    "glioma": 1621,
    "meningioma": 1645,
    "pituitary": 1757,
    "healthy": 2000,
}

TOLERANCIA_PROPORCION = 0.035
"""Margen frente a `train_fraction`.

Con hashing no se puede exigir exactitud: la desviacion es binomial y con ~1.600
imagenes por clase su desviacion tipica ronda 0,01. 0,035 son ~3 sigmas: lo
bastante estrecho para detectar un sesgo real y lo bastante ancho para no
convertir la prueba en un test de suerte.
"""


def construir_dataset(
    conteos: dict[str, int] | None = None, prefijo: str = "img"
) -> list[RegistroImagen]:
    """Genera registros con identificadores estables y deterministas.

    Los identificadores imitan el hash de contenido que usara el sistema real:
    lo importante es que no lleven informacion de posicion.
    """
    conteos = conteos or CONTEO_REAL
    return [
        RegistroImagen(f"{prefijo}-{clase}-{indice:05d}", clase)
        for clase in TUMOR_CLASSES
        for indice in range(conteos[clase])
    ]


@pytest.fixture(scope="module")
def dataset_real() -> list[RegistroImagen]:
    return construir_dataset()


@pytest.fixture(scope="module")
def particion_real(dataset_real: list[RegistroImagen]) -> ParticionDataset:
    return particionar(dataset_real)


def mapa_de_particiones(particion: ParticionDataset) -> dict[str, str]:
    return {r.identificador: "train" for r in particion.train} | {
        r.identificador: "test" for r in particion.test
    }


def test_el_orden_de_entrada_no_altera_la_particion(
    dataset_real: list[RegistroImagen], particion_real: ParticionDataset
) -> None:
    barajado = list(dataset_real)
    random.Random(20260904).shuffle(barajado)

    assert mapa_de_particiones(particionar(barajado)) == mapa_de_particiones(particion_real)


def test_la_particion_de_una_imagen_no_depende_del_dataset(
    particion_real: ParticionDataset,
) -> None:
    """Particionar un subconjunto da el mismo resultado que particionar el todo."""
    esperado = mapa_de_particiones(particion_real)
    muestra = random.Random(7).sample(list(particion_real.train + particion_real.test), 200)

    obtenido = mapa_de_particiones(particionar(muestra))

    assert obtenido == {r.identificador: esperado[r.identificador] for r in muestra}


def test_anadir_imagenes_no_reasigna_las_existentes(
    dataset_real: list[RegistroImagen], particion_real: ParticionDataset
) -> None:
    """La prueba que da valor al patron: el dataset crece, el split no se mueve."""
    nuevas = construir_dataset({clase: 300 for clase in TUMOR_CLASSES}, prefijo="upload")
    ampliado = particionar(dataset_real + nuevas)

    antes = mapa_de_particiones(particion_real)
    despues = mapa_de_particiones(ampliado)

    reasignadas = [ident for ident, destino in antes.items() if despues[ident] != destino]
    assert reasignadas == []
    assert ampliado.total == len(dataset_real) + len(nuevas)


def test_retirar_imagenes_no_reasigna_las_restantes(
    dataset_real: list[RegistroImagen], particion_real: ParticionDataset
) -> None:
    reducido = particionar(dataset_real[::3])
    antes = mapa_de_particiones(particion_real)

    assert all(
        destino == antes[ident] for ident, destino in mapa_de_particiones(reducido).items()
    )


def test_asignar_particion_es_una_funcion_pura() -> None:
    llamadas = {asignar_particion("img-glioma-00042", "glioma") for _ in range(10)}
    assert len(llamadas) == 1


def test_proporciones_por_clase_dentro_de_la_tolerancia(
    particion_real: ParticionDataset,
) -> None:
    objetivo = SplitConfig().train_fraction

    for clase, proporcion in particion_real.proporcion_train_por_clase().items():
        assert abs(proporcion - objetivo) < TOLERANCIA_PROPORCION, (
            f"{clase}: proporcion de train {proporcion:.4f} lejos de {objetivo}"
        )


def test_proporcion_global_dentro_de_la_tolerancia(particion_real: ParticionDataset) -> None:
    global_train = len(particion_real.train) / particion_real.total
    assert abs(global_train - SplitConfig().train_fraction) < TOLERANCIA_PROPORCION


def test_todas_las_clases_estan_en_ambas_particiones(particion_real: ParticionDataset) -> None:
    for clase, conteo in particion_real.conteos_por_clase().items():
        assert conteo["train"] > 0 and conteo["test"] > 0, f"{clase} falta en alguna particion"
        assert conteo["train"] + conteo["test"] == CONTEO_REAL[clase]


def test_train_y_test_son_disjuntos(particion_real: ParticionDataset) -> None:
    assert not (particion_real.identificadores("train") & particion_real.identificadores("test"))


def test_cambiar_el_salt_produce_otra_particion(dataset_real: list[RegistroImagen]) -> None:
    otra = particionar(dataset_real, SplitConfig(salt="brainneuroscan-split-v2"))
    base = mapa_de_particiones(particionar(dataset_real))
    alternativa = mapa_de_particiones(otra)

    distintos = sum(1 for ident, destino in base.items() if alternativa[ident] != destino)
    # Con dos flujos independientes la discrepancia esperada es 2*p*(1-p) ~ 31%.
    assert 0.20 < distintos / len(base) < 0.45


def test_cambiar_la_fraccion_desplaza_la_frontera(dataset_real: list[RegistroImagen]) -> None:
    mitad = particionar(dataset_real, SplitConfig(train_fraction=0.5))
    assert abs(len(mitad.train) / mitad.total - 0.5) < TOLERANCIA_PROPORCION
    # El split mas pequeno esta contenido en el mas grande: mover el umbral no
    # reordena los buckets, solo cambia donde se corta.
    assert mitad.identificadores("train") <= particionar(dataset_real).identificadores("train")


def test_registro_rechaza_clase_desconocida() -> None:
    with pytest.raises(ValueError, match="clase desconocida"):
        RegistroImagen("img-0001", "astrocitoma")


def test_registro_rechaza_identificador_vacio() -> None:
    with pytest.raises(ValueError, match="identificador"):
        RegistroImagen("", "glioma")


@pytest.mark.parametrize(
    "kwargs",
    [{"salt": ""}, {"train_fraction": 0.0}, {"train_fraction": 1.0}, {"buckets": 10}],
)
def test_split_config_valida_sus_parametros(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SplitConfig(**kwargs)  # type: ignore[arg-type]


def test_identificador_con_dos_clases_es_un_error() -> None:
    with pytest.raises(ValueError, match="dos clases"):
        particionar(
            [RegistroImagen("img-0001", "glioma"), RegistroImagen("img-0001", "healthy")]
        )


def test_la_huella_ignora_el_orden_y_la_fecha(dataset_real: list[RegistroImagen]) -> None:
    barajado = list(dataset_real)
    random.Random(11).shuffle(barajado)

    uno = DatasetSnapshot.desde_particion(
        particionar(dataset_real), creado_en=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    otro = DatasetSnapshot.desde_particion(
        particionar(barajado), creado_en=datetime(2026, 9, 4, tzinfo=timezone.utc)
    )

    assert uno.huella == otro.huella
    assert uno.snapshot_id == otro.snapshot_id
    assert uno.creado_en != otro.creado_en


def test_la_huella_cambia_al_cambiar_el_contenido(dataset_real: list[RegistroImagen]) -> None:
    base = DatasetSnapshot.desde_particion(particionar(dataset_real))

    ampliado = DatasetSnapshot.desde_particion(
        particionar(dataset_real + [RegistroImagen("upload-glioma-99999", "glioma")])
    )
    reetiquetado = DatasetSnapshot.desde_particion(
        particionar(
            [
                RegistroImagen(registro.identificador, "healthy") if indice == 0 else registro
                for indice, registro in enumerate(dataset_real)
            ]
        )
    )
    otro_salt = DatasetSnapshot.desde_particion(
        particionar(dataset_real, SplitConfig(salt="brainneuroscan-split-v2"))
    )

    huellas = {base.huella, ampliado.huella, reetiquetado.huella, otro_salt.huella}
    assert len(huellas) == 4


def test_snapshot_serializa_y_reconstruye(particion_real: ParticionDataset) -> None:
    original = DatasetSnapshot.desde_particion(particion_real)
    documento = json.loads(original.to_json())

    assert documento["conteos"]["glioma"]["train"] + documento["conteos"]["glioma"]["test"] == 1621
    assert documento["total"] == sum(CONTEO_REAL.values())
    assert documento["config"]["salt"] == SplitConfig().salt

    recuperado = DatasetSnapshot.from_json(original.to_json())
    assert recuperado == original
    assert recuperado.huella == original.huella


def test_snapshot_manipulado_es_rechazado(particion_real: ParticionDataset) -> None:
    documento = DatasetSnapshot.desde_particion(particion_real).to_dict()
    documento["test"] = documento["test"][:-1]  # alguien retira una imagen del JSON

    with pytest.raises(ValueError, match="huella inconsistente"):
        DatasetSnapshot.from_dict(documento)


def test_guard_acepta_snapshots_sucesivos(dataset_real: list[RegistroImagen]) -> None:
    """El caso feliz: el dataset crece entre reentrenamientos y no hay fuga."""
    anterior = DatasetSnapshot.desde_particion(particionar(dataset_real))
    nuevas = construir_dataset({clase: 150 for clase in TUMOR_CLASSES}, prefijo="upload")
    actual = DatasetSnapshot.desde_particion(particionar(dataset_real + nuevas))

    assert guard_antes_de_entrenar(actual, [anterior]) is actual


def test_guard_detecta_una_fuga_real(particion_real: ParticionDataset) -> None:
    """Control positivo: si el detector no falla aqui, no vale para nada.

    Se fabrica el escenario exacto que produciria un `random_state`: una imagen
    que estaba en entrenamiento reaparece en prueba en el snapshot siguiente.
    """
    anterior = DatasetSnapshot.desde_particion(particion_real)
    filtrada = anterior.train[0]
    contaminado = DatasetSnapshot(
        snapshot_id="ds-contaminado",
        creado_en="2026-09-04T00:00:00+00:00",
        train=anterior.train[1:],
        test=anterior.test + (filtrada,),
        config=anterior.config,
    )

    with pytest.raises(FugaDeDatosError) as excinfo:
        verificar_sin_solapamiento(anterior, contaminado)
    assert filtrada.identificador in str(excinfo.value)

    with pytest.raises(FugaDeDatosError):
        guard_antes_de_entrenar(contaminado, [anterior])


def test_guard_detecta_la_fuga_en_sentido_inverso(particion_real: ParticionDataset) -> None:
    anterior = DatasetSnapshot.desde_particion(particion_real)
    promovida = anterior.test[0]
    contaminado = DatasetSnapshot(
        snapshot_id="ds-inverso",
        creado_en="2026-09-04T00:00:00+00:00",
        train=anterior.train + (promovida,),
        test=anterior.test[1:],
        config=anterior.config,
    )

    with pytest.raises(FugaDeDatosError, match="test->train"):
        verificar_sin_solapamiento(anterior, contaminado)


def test_guard_detecta_un_snapshot_internamente_incoherente(
    particion_real: ParticionDataset,
) -> None:
    valido = DatasetSnapshot.desde_particion(particion_real)
    incoherente = DatasetSnapshot(
        snapshot_id="ds-incoherente",
        creado_en=valido.creado_en,
        train=valido.train,
        test=valido.test + (valido.train[0],),
        config=valido.config,
    )

    with pytest.raises(FugaDeDatosError, match="ambas particiones"):
        verificar_snapshot_consistente(incoherente)


def test_guard_sin_historico_valida_solo_la_coherencia(
    particion_real: ParticionDataset,
) -> None:
    snapshot = DatasetSnapshot.desde_particion(particion_real)
    assert guard_antes_de_entrenar(snapshot) is snapshot
