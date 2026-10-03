"""La utilidad manual tampoco debe imprimir errores sensibles del proveedor."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


def test_ver_modelos_error_sin_filtracion(monkeypatch, capsys):
    import openai
    monkeypatch.setenv('GROQ_API_KEY', 'fixture-no-real')
    sdk = SimpleNamespace(models=SimpleNamespace(list=AsyncMock(
        side_effect=RuntimeError('TOKEN-SENTINELA https://privado.invalid CUERPO-SENTINELA'))),
        close=AsyncMock())
    constructor = Mock(return_value=sdk)
    monkeypatch.setattr(openai, 'AsyncOpenAI', constructor)
    spec = importlib.util.spec_from_file_location('utilidad_modelos_auditada',
        Path(__file__).parents[1] / 'app/ver_modelos.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    constructor.assert_not_called()
    asyncio.run(modulo.main())
    sdk.close.assert_awaited_once()
    salida = capsys.readouterr().out
    assert 'TOKEN-SENTINELA' not in salida
    assert 'https://privado.invalid' not in salida
    assert 'CUERPO-SENTINELA' not in salida
