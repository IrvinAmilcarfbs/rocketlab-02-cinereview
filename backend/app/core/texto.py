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


def chave_agrupamento(texto: str) -> str:
    """Reduz um título à forma usada para reconhecer registros repetidos.

    Vai além de ``normalizar_busca`` e descarta tudo que não seja letra ou
    dígito, inclusive os espaços. O motivo é que o TMDB guarda o mesmo filme
    sob grafias que só diferem na pontuação: "Die Hart 2: Die Harter",
    "Die Hart 2 : Die Harter" e "Die Hart 2 - Die Harter" são três registros
    distintos, com identificadores próprios, que descrevem um único filme.

    Descartar os espaços junto com a pontuação evita ter de reduzir as
    sequências de espaço que a remoção deixa para trás, e ainda une variações
    de espaçamento. O resultado não é legível, mas nunca é exibido: serve
    apenas de chave.

    São 86 caracteres de pontuação distintos nos títulos do catálogo, o que
    descarta calcular isto em SQL — daí a coluna derivada.
    """

    return "".join(letra for letra in normalizar_busca(texto) if letra.isalnum())
