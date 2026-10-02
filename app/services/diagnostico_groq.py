"""Metadatos permitidos explícitamente: nunca serializar respuestas completas."""

# Solo identificadores conocidos; un valor arbitrario del proveedor/configuración
# podría contener datos sensibles. Se informa además si el modelo coincide.
MODELOS_SEGUROS = frozenset({
    'qwen/qwen3.8-27b',
    'openai/gpt-oss-20b', 'openai/gpt-oss-120b',
    'llama-3.1-8b-instant', 'llama-3.3-70b-versatile',
})
MOTIVOS = frozenset({'stop', 'length', 'tool_calls', 'function_call', 'content_filter'})


def campo(objeto, nombre):
    return objeto.get(nombre) if isinstance(objeto, dict) else getattr(objeto, nombre, None)


def tipo_seguro(valor):
    for tipo in (str, list, dict, int, float, bool, tuple):
        if type(valor) is tipo:
            return tipo.__name__
    return 'NoneType' if valor is None else 'object'


def entero(valor):
    return valor if type(valor) is int and valor >= 0 else None


def estructura_respuesta(respuesta, modelo_solicitado, presupuesto):
    modelo = campo(respuesta, 'model')
    choices = campo(respuesta, 'choices')
    usage = campo(respuesta, 'usage')
    detalles = campo(usage, 'completion_tokens_details')
    diagnostico = {
        'api': 'chat.completions',
        'requested_model': modelo_solicitado if modelo_solicitado in MODELOS_SEGUROS else 'other',
        'returned_model': modelo if isinstance(modelo, str) and modelo in MODELOS_SEGUROS else 'other',
        'model_matches': isinstance(modelo, str) and modelo == modelo_solicitado,
        'max_tokens': presupuesto,
        'choices_type': tipo_seguro(choices),
        'choices_count': len(choices) if isinstance(choices, (list, tuple)) else None,
        'usage_present': usage is not None,
        'prompt_tokens': entero(campo(usage, 'prompt_tokens')),
        'completion_tokens': entero(campo(usage, 'completion_tokens')),
        'total_tokens': entero(campo(usage, 'total_tokens')),
        'reasoning_tokens': entero(campo(detalles, 'reasoning_tokens')),
        'choices': [],
    }
    # Acotar tamaño sin imprimir valores, claves extras ni nombres de tipos externos.
    for opcion in choices[:5] if isinstance(choices, (list, tuple)) else []:
        mensaje = campo(opcion, 'message')
        contenido = campo(mensaje, 'content')
        motivo = campo(opcion, 'finish_reason')
        fields = campo(mensaje, 'model_fields_set')
        recibido = ('content' in mensaje if isinstance(mensaje, dict)
                    else 'content' in fields if isinstance(fields, set) else None)
        item = {
            'finish_reason': motivo if isinstance(motivo, str) and motivo in MOTIVOS else 'other',
            'finish_reason_is_none': motivo is None,
            'message_present': mensaje is not None,
            'message_is_dict': isinstance(mensaje, dict),
            'content_received': recibido,
            'content_type': tipo_seguro(contenido),
            'content_is_none': contenido is None,
            'content_length': len(contenido) if isinstance(contenido, str) else None,
            'content_blank': not contenido.strip() if isinstance(contenido, str) else None,
        }
        for nombre in ('reasoning', 'reasoning_content', 'refusal', 'text', 'output_text'):
            valor = campo(mensaje, nombre)
            item[nombre + '_present'] = valor is not None
            item[nombre + '_length'] = len(valor) if isinstance(valor, str) else None
        tools = campo(mensaje, 'tool_calls')
        item['tool_calls_count'] = len(tools) if isinstance(tools, list) else None
        item['function_call_present'] = campo(mensaje, 'function_call') is not None
        item['audio_present'] = campo(mensaje, 'audio') is not None
        extras = campo(mensaje, 'model_extra')
        item['extra_fields_count'] = len(extras) if isinstance(extras, dict) else None
        diagnostico['choices'].append(item)
    return diagnostico
