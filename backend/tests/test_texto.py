"""Testes das reduções de título usadas pela busca e pelo agrupamento."""

from app.core.texto import chave_agrupamento, normalizar_busca


def test_normalizar_remove_acento_e_caixa() -> None:
    assert normalizar_busca("Canção Da Chuva") == "cancao da chuva"
    assert normalizar_busca("  ALIEN  ") == "alien"


def test_normalizar_preserva_alfabetos_nao_latinos() -> None:
    """Converter para ASCII à força esvaziaria 177 títulos do catálogo.

    Um título reduzido a string vazia seria impossível de encontrar, então a
    normalização descarta diacríticos e nada além deles.
    """

    assert normalizar_busca("Ελλάδα") != ""
    assert normalizar_busca("Москва") != ""


def test_normalizar_preserva_pontuacao() -> None:
    """A busca casa substring: tirar pontuação aqui mudaria o que o usuário acha."""

    assert normalizar_busca("100% Wolf") == "100% wolf"


def test_chave_descarta_pontuacao_e_espacos() -> None:
    variantes = ("Die Hart 2: Die Harter", "Die Hart 2 : Die Harter", "Die Hart 2 - Die Harter")

    assert {chave_agrupamento(titulo) for titulo in variantes} == {"diehart2dieharter"}


def test_chave_separa_titulos_com_palavras_diferentes() -> None:
    assert chave_agrupamento("Die Hart: Die Harter") != chave_agrupamento("Die Hart 2: Die Harter")


def test_chave_preserva_alfabetos_nao_latinos() -> None:
    assert chave_agrupamento("Ελλάδα") != ""
