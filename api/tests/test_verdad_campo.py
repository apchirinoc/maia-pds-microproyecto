"""Circuito de verdad de campo y persistencia de clasificaciones.

Estas pruebas **escriben**. Cada una restaura el estado que encontró, para que
la base siga sirviendo la línea base documentada (120 cargas · 56 confirmadas ·
44 aciertos) a las demás pruebas y a la demostración.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import construir_app, requiere_postgres

pytestmark = requiere_postgres


@pytest_asyncio.fixture
async def cliente_pg() -> AsyncIterator[AsyncClient]:
    app = construir_app("postgres")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://pruebas"
    ) as cliente:
        yield cliente


@pytest_asyncio.fixture(autouse=True)
async def sin_residuo() -> AsyncIterator[None]:
    """Retira lo que la prueba haya creado, incluso si falló.

    Va en el desmontaje y no al final de cada prueba a propósito: una prueba que
    falla a mitad se salta su propia limpieza y deja residuo que rompe la
    ejecución siguiente. Ese fallo en cascada ya ocurrió una vez.
    """
    yield
    await _retirar_cargas_de_prueba()
    await _retirar_confirmaciones_de_prueba()


@pytest_asyncio.fixture
async def cabeceras_pg(cliente_pg: AsyncClient) -> dict[str, str]:
    respuesta = await cliente_pg.post(
        "/api/v1/auth/login", json={"username": "demo", "password": "demo"}
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['accessToken']}"}


async def _buscar_carga(cliente: AsyncClient, cabeceras: dict[str, str], *, confirmada: bool):
    """Devuelve la primera carga con —o sin— diagnóstico confirmado."""
    for pagina in range(1, 10):
        respuesta = await cliente.get(
            f"/api/v1/uploads?page={pagina}&pageSize=25", headers=cabeceras
        )
        assert respuesta.status_code == 200, respuesta.text
        for registro in respuesta.json()["items"]:
            if (registro["groundTruth"] is not None) == confirmada:
                return registro
    pytest.fail(f"No se encontró ninguna carga con confirmada={confirmada}")


async def _resumen(cliente: AsyncClient, cabeceras: dict[str, str]) -> dict:
    respuesta = await cliente.get("/api/v1/uploads/summary", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["groundTruth"]


async def _restaurar(
    cliente: AsyncClient, cabeceras: dict[str, str], registro: dict
) -> None:
    """Devuelve la carga a su diagnóstico original.

    No hay endpoint para retirar una confirmación —y no debería haberlo: un
    diagnóstico no se «desregistra»—, así que se vuelve a registrar el valor
    previo. La confirmación intermedia queda en la tabla con borrado lógico,
    que es exactamente el historial que el esquema pretende conservar.
    """
    original = registro["groundTruth"]
    if original is None:
        return
    respuesta = await cliente.post(
        f"/api/v1/uploads/{registro['id']}/ground-truth",
        json={
            "diagnosis": original["diagnosis"],
            "confirmedBy": original["confirmedBy"],
            "source": original["source"],
        },
        headers=cabeceras,
    )
    assert respuesta.status_code == 200, respuesta.text


async def test_registrar_verdad_campo_sobre_carga_sin_confirmar(
    cliente_pg: AsyncClient, cabeceras_pg: dict[str, str]
) -> None:
    antes = await _resumen(cliente_pg, cabeceras_pg)
    carga = await _buscar_carga(cliente_pg, cabeceras_pg, confirmada=False)

    respuesta = await cliente_pg.post(
        f"/api/v1/uploads/{carga['id']}/ground-truth",
        json={
            "diagnosis": "glioma",
            "confirmedBy": "prueba@hospital.example",
            "source": "histopathology",
        },
        headers=cabeceras_pg,
    )
    assert respuesta.status_code == 200, respuesta.text
    devuelto = respuesta.json()
    assert devuelto["groundTruth"]["diagnosis"] == "glioma"
    assert devuelto["groundTruth"]["source"] == "histopathology"

    despues = await _resumen(cliente_pg, cabeceras_pg)
    assert despues["confirmedUploads"] == antes["confirmedUploads"] + 1
    assert despues["coverage"] > antes["coverage"]

    # Restauración por SQL: la API no expone —ni debe exponer— forma de retirar
    # una confirmación. Ver la nota al final del archivo.
    await _limpiar_confirmacion(carga["id"])
    final = await _resumen(cliente_pg, cabeceras_pg)
    assert final["confirmedUploads"] == antes["confirmedUploads"]


async def test_registrar_sustituye_la_confirmacion_vigente(
    cliente_pg: AsyncClient, cabeceras_pg: dict[str, str]
) -> None:
    """El índice único parcial impide dos confirmaciones vigentes a la vez."""
    antes = await _resumen(cliente_pg, cabeceras_pg)
    carga = await _buscar_carga(cliente_pg, cabeceras_pg, confirmada=True)
    original = carga["groundTruth"]["diagnosis"]
    distinto = "healthy" if original != "healthy" else "glioma"

    respuesta = await cliente_pg.post(
        f"/api/v1/uploads/{carga['id']}/ground-truth",
        json={
            "diagnosis": distinto,
            "confirmedBy": "correccion@hospital.example",
            "source": "histopathology",
        },
        headers=cabeceras_pg,
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["groundTruth"]["diagnosis"] == distinto

    # El número de confirmadas NO cambia: se sustituyó, no se añadió.
    intermedio = await _resumen(cliente_pg, cabeceras_pg)
    assert intermedio["confirmedUploads"] == antes["confirmedUploads"]

    await _restaurar(cliente_pg, cabeceras_pg, carga)
    final = await _resumen(cliente_pg, cabeceras_pg)
    assert final == antes


async def test_registrar_sobre_carga_inexistente_devuelve_404(
    cliente_pg: AsyncClient, cabeceras_pg: dict[str, str]
) -> None:
    respuesta = await cliente_pg.post(
        "/api/v1/uploads/upl_inexistente/ground-truth",
        json={
            "diagnosis": "glioma",
            "confirmedBy": "prueba@hospital.example",
            "source": "specialist_review",
        },
        headers=cabeceras_pg,
    )
    assert respuesta.status_code == 404


async def test_clasificar_persiste_la_carga_y_su_prediccion(
    cliente_pg: AsyncClient, cabeceras_pg: dict[str, str]
) -> None:
    antes = await _resumen(cliente_pg, cabeceras_pg)

    respuesta = await cliente_pg.post(
        "/api/v1/classifications",
        data={"countryCode": "CO", "hint": "glioma", "explain": "true"},
    )
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()
    assert resultado["predictedClass"] == "glioma"
    assert resultado["explanation"]["method"] == "occlusion"
    assert set(resultado["confidenceByClass"]) == {
        "glioma",
        "meningioma",
        "pituitary",
        "healthy",
    }
    assert abs(sum(resultado["confidenceByClass"].values()) - 100) < 0.5

    despues = await _resumen(cliente_pg, cabeceras_pg)
    assert despues["totalUploads"] == antes["totalUploads"] + 1

    await _retirar_cargas_de_prueba()
    final = await _resumen(cliente_pg, cabeceras_pg)
    assert final["totalUploads"] == antes["totalUploads"]


async def test_clasificar_rechaza_un_pais_desconocido(cliente_pg: AsyncClient) -> None:
    respuesta = await cliente_pg.post(
        "/api/v1/classifications", data={"countryCode": "ZZ", "explain": "false"}
    )
    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# Restauración del estado
#
# Se hace por SQL y no por API a propósito: la API no expone —ni debe exponer—
# forma de retirar una confirmación ni de borrar una carga. Son operaciones de
# mantenimiento de la prueba, no del dominio.
# ---------------------------------------------------------------------------


async def _sql(sentencia: str) -> None:
    """Ejecuta la sentencia con la misma conexión que usa la aplicación.

    Antes se invocaba `docker exec` contra un contenedor con el nombre escrito
    a mano. Eso ataba las pruebas a una forma concreta de desplegar la base: al
    levantarla con otra orquestación el contenedor cambia de nombre y la
    restauración fallaba. Usar la configuración del propio API funciona sea cual
    sea el despliegue.

    Es asíncrona porque las pruebas ya corren dentro de un bucle de eventos:
    abrir otro desde dentro lo rompe.
    """
    from sqlalchemy import text

    from app.db.session import get_sessionmaker

    async with get_sessionmaker()() as sesion:
        await sesion.execute(text(sentencia))
        await sesion.commit()


async def _limpiar_confirmacion(public_id: str) -> None:
    await _sql(
        "UPDATE ground_truth_diagnoses SET deleted_at = now() "
        "WHERE deleted_at IS NULL AND confirmed_by = 'prueba@hospital.example' "
        f"AND upload_id = (SELECT id FROM uploads WHERE public_id = '{public_id}')"
    )


async def _retirar_confirmaciones_de_prueba() -> None:
    """Retira las confirmaciones firmadas por las direcciones de prueba."""
    await _sql(
        "UPDATE ground_truth_diagnoses SET deleted_at = now() "
        "WHERE deleted_at IS NULL AND confirmed_by IN "
        "('prueba@hospital.example', 'correccion@hospital.example')"
    )


async def _retirar_cargas_de_prueba() -> None:
    await _sql(
        "UPDATE uploads SET deleted_at = now() "
        "WHERE deleted_at IS NULL AND public_id NOT LIKE 'upl_9f%'"
    )
