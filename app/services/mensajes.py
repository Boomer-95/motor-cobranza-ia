"""Normalización SMS local, sin acceso a proveedores ni al historial de IA."""
import string
import re
import unicodedata

SMS_MAX = 150
# Subconjunto GSM-7 básico: cada carácter ocupa un septeto, sin escapes.
SMS_CARACTERES = frozenset(string.ascii_letters + string.digits + " !\"#$%&'()*+,-./:;<=>?@_")


class AdaptacionInvalida(ValueError):
    """El código es fijo y seguro para logs; nunca incluye contenido del proveedor."""
    def __init__(self, codigo):
        self.codigo = codigo
        super().__init__(codigo)


def extraer_adaptacion(respuesta, *, permitir_length=False):
    try:
        opcion = respuesta.choices[0]
        contenido = opcion.message.content
        motivo = opcion.finish_reason
    except (AttributeError, IndexError, TypeError):
        raise AdaptacionInvalida('MalformedResponse') from None
    if motivo != 'stop' and not (permitir_length and motivo == 'length'):
        codigo = 'TokenLimitReached' if motivo == 'length' else 'UnexpectedFinishReason'
        raise AdaptacionInvalida(codigo)
    if not isinstance(contenido, str) or not contenido.strip():
        raise AdaptacionInvalida('EmptyContent')
    return contenido.strip()


def limpiar_formato_sms(texto):
    # Solo contenido; nunca usar el campo separado de razonamiento del modelo.
    # El razonamiento etiquetado, incluso incompleto, no es un mensaje al cliente.
    texto = re.sub(r'<think\b[^>]*>.*?(?:</think\s*>|$)', '', texto,
                   flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r'^\s*```[^\n]*\n|\n?\s*```\s*$', '', texto)
    texto = re.sub(r'^\s*(?:SMS|Mensaje(?:\s+SMS)?)\s*:\s*', '', texto,
                   flags=re.IGNORECASE)
    texto = re.sub(r'^\s*(?:[-*+]\s+|#{1,6}\s+)', '', texto, flags=re.MULTILINE)
    return texto.replace('**', '').replace('__', '').strip().strip('"\'“”‘’`')


def normalizar_sms(texto):
    texto = texto.translate(str.maketrans({
        '“': '"', '”': '"', '‘': "'", '’': "'", '–': '-', '—': '-',
        '…': '...', '€': ' EUR ',
    }))
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(''.join(c if c in SMS_CARACTERES else ' ' for c in texto).split())


def preparar_sms(texto):
    texto = limpiar_formato_sms(texto)
    texto = normalizar_sms(texto)
    if len(texto) > SMS_MAX:
        # Acumular palabras completas; nunca fragmentar números, URLs o palabras.
        palabras = []
        for palabra in texto.split():
            if len(' '.join(palabras + [palabra])) > SMS_MAX:
                break
            palabras.append(palabra)
        texto = ' '.join(palabras)
    if not texto or not any(c.isalnum() for c in texto):
        raise AdaptacionInvalida('NoUsableSmsWords')
    return texto


def adaptar_sms(respuesta):
    """SMS utilizable de stop/length: texto, formato, GSM-7 y palabras completas."""
    texto = extraer_adaptacion(respuesta, permitir_length=True)
    texto = preparar_sms(texto)
    validar_sms(texto)
    return texto


def validar_sms(texto):
    if not texto or len(texto) > SMS_MAX or texto != normalizar_sms(texto):
        raise ValueError('SMS no válido para un segmento')
