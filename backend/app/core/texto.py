"""Normalização de texto para comparação de busca."""

import unicodedata


def normalizar_busca(texto: str) -> str:
    """Reduz um texto à forma usada nas comparações de busca.

    Remove acentos e unifica a caixa, para que "cancao" encontre "Canção" —
    3.650 títulos do catálogo têm acento, e exigir a digitação exata tornaria
    justamente os títulos em português difíceis de achar.

    A remoção descarta apenas os diacríticos, e não todo caractere fora do
    ASCII. A diferença importa: converter para ASCII à força esvaziaria por
    completo 177 títulos escritos em grego, cirílico e outros alfabetos,
    tornando-os impossíveis de encontrar.
    """

    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(letra for letra in decomposto if not unicodedata.combining(letra))
    return sem_acento.casefold().strip()
