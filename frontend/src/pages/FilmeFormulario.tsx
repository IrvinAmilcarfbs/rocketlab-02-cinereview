import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ErroApi } from '../api/cliente'
import { useAtualizarFilme, useCriarFilme, useFilme, useGeneros } from '../api/filmes'
import type { FilmeDetalhe, FilmeEntrada, StatusFilme } from '../api/tipos'
import { ListaNomes } from '../components/ListaNomes'
import { Mensagem } from '../components/Mensagem'
import estilos from './FilmeFormulario.module.css'

/** Conjunto fechado, igual ao `Literal` do schema no backend. */
const STATUS: StatusFilme[] = ['Lançado', 'Pós-Produção', 'Em Produção', 'Planejado']

const ANO_MINIMO = 1888
const ANO_MAXIMO = 2100

const VAZIO: FilmeEntrada = {
  titulo: '',
  ano: null,
  sinopse: null,
  duracao_minutos: null,
  status: null,
  poster_url: null,
  generos: [],
  diretores: [],
}

/** Converte a ficha da API no subconjunto que o formulário controla.
 *
 * O que não aparece aqui é justamente o que o `PUT` não toca — e é por isso que
 * a conversão é explícita em vez de um espalhamento do objeto: acrescentar um
 * campo à ficha não deve fazer o formulário passar a sobrescrevê-lo por acidente.
 */
function paraEntrada(filme: FilmeDetalhe): FilmeEntrada {
  return {
    titulo: filme.titulo,
    ano: filme.ano,
    sinopse: filme.sinopse,
    duracao_minutos: filme.duracao_minutos,
    status: STATUS.includes(filme.status as StatusFilme) ? (filme.status as StatusFilme) : null,
    poster_url: filme.poster_url,
    generos: filme.generos.map((genero) => genero.nome),
    diretores: filme.diretores.map((pessoa) => pessoa.nome),
  }
}

/** Valida do lado do cliente o que o backend também valida.
 *
 * A duplicação é proposital: o servidor é a autoridade, mas apontar o erro no
 * campo certo antes de enviar é melhor do que devolver uma mensagem geral depois.
 */
function validar(entrada: FilmeEntrada): Partial<Record<keyof FilmeEntrada, string>> {
  const erros: Partial<Record<keyof FilmeEntrada, string>> = {}

  if (!entrada.titulo.trim()) {
    erros.titulo = 'O título é obrigatório.'
  }
  if (entrada.ano !== null && (entrada.ano < ANO_MINIMO || entrada.ano > ANO_MAXIMO)) {
    erros.ano = `Informe um ano entre ${ANO_MINIMO} e ${ANO_MAXIMO}.`
  }
  if (
    entrada.duracao_minutos !== null &&
    (entrada.duracao_minutos < 1 || entrada.duracao_minutos > 1000)
  ) {
    erros.duracao_minutos = 'Informe a duração em minutos, entre 1 e 1000.'
  }

  return erros
}

/** Lê um campo numérico, tratando o campo vazio como ausência de valor. */
function lerNumero(valor: string): number | null {
  if (valor.trim() === '') {
    return null
  }
  const numero = Number(valor)
  return Number.isFinite(numero) ? numero : null
}

export function FilmeFormulario() {
  const { id } = useParams()
  const edicao = Boolean(id)
  const navegar = useNavigate()

  const generos = useGeneros()
  const existente = useFilme(id ?? '')
  const criar = useCriarFilme()
  const atualizar = useAtualizarFilme(id ?? '')
  const mutacao = edicao ? atualizar : criar

  const [entrada, setEntrada] = useState<FilmeEntrada>(VAZIO)
  const [erros, setErros] = useState<Partial<Record<keyof FilmeEntrada, string>>>({})

  // Na edição, o formulário parte da ficha carregada. O ajuste acontece durante
  // o render, e não num efeito: é o padrão do React para derivar estado de um
  // valor externo, e evita o render intermediário com o formulário em branco.
  const [carregado, setCarregado] = useState<string | null>(null)
  if (edicao && existente.data && carregado !== existente.data.id) {
    setCarregado(existente.data.id)
    setEntrada(paraEntrada(existente.data))
  }

  function alterar<C extends keyof FilmeEntrada>(campo: C, valor: FilmeEntrada[C]) {
    setEntrada((atual) => ({ ...atual, [campo]: valor }))
    // O erro do campo sai de cena assim que o usuário mexe nele: manter a
    // mensagem enquanto ele corrige dá a impressão de que nada mudou.
    setErros((atuais) => ({ ...atuais, [campo]: undefined }))
  }

  function enviar(evento: React.FormEvent) {
    evento.preventDefault()

    const encontrados = validar(entrada)
    if (Object.keys(encontrados).length > 0) {
      setErros(encontrados)
      return
    }

    mutacao.mutate(
      { ...entrada, titulo: entrada.titulo.trim() },
      { onSuccess: (filme) => navegar(`/filmes/${filme.id}`) },
    )
  }

  if (edicao && existente.isPending) {
    return (
      <div className={estilos.pagina}>
        <p className={estilos.aguarde}>Carregando filme…</p>
      </div>
    )
  }

  if (edicao && existente.isError) {
    const naoEncontrado = existente.error instanceof ErroApi && existente.error.status === 404
    return (
      <div className={estilos.pagina}>
        <Mensagem
          tom="erro"
          titulo={naoEncontrado ? 'Filme não encontrado' : 'Não foi possível carregar o filme'}
          descricao={naoEncontrado ? 'Ele pode ter sido removido.' : undefined}
          acao={{ rotulo: 'Voltar ao catálogo', onClick: () => navegar('/') }}
        />
      </div>
    )
  }

  const destinoVoltar = edicao ? `/filmes/${id}` : '/'

  return (
    <div className={estilos.pagina}>
      <Link to={destinoVoltar} className={estilos.voltar}>
        ← {edicao ? 'Voltar ao filme' : 'Voltar ao catálogo'}
      </Link>

      <h1 className={estilos.titulo}>{edicao ? 'Editar filme' : 'Novo filme'}</h1>
      <p className={estilos.subtitulo}>
        {edicao
          ? 'Os campos abaixo substituem os atuais. Notas externas, dados financeiros, elenco e roteiro não são alterados aqui.'
          : 'Preencha as informações do filme. Só o título é obrigatório.'}
      </p>

      {/* `noValidate` desliga as bolhas de validação do navegador: as mensagens
          ficam ao lado do campo, em português e no mesmo estilo do resto. */}
      <form className={estilos.formulario} onSubmit={enviar} noValidate>
        <label className={estilos.campo}>
          <span className={estilos.rotulo}>
            Título <span className={estilos.obrigatorio}>*</span>
          </span>
          <input
            type="text"
            value={entrada.titulo}
            maxLength={500}
            className={estilos.texto}
            aria-invalid={Boolean(erros.titulo)}
            onChange={(evento) => alterar('titulo', evento.target.value)}
          />
          {erros.titulo && <span className={estilos.erroCampo}>{erros.titulo}</span>}
        </label>

        <div className={estilos.linha}>
          <label className={estilos.campo}>
            <span className={estilos.rotulo}>Ano</span>
            <input
              type="number"
              value={entrada.ano ?? ''}
              min={ANO_MINIMO}
              max={ANO_MAXIMO}
              className={estilos.texto}
              aria-invalid={Boolean(erros.ano)}
              onChange={(evento) => alterar('ano', lerNumero(evento.target.value))}
            />
            {erros.ano && <span className={estilos.erroCampo}>{erros.ano}</span>}
          </label>

          <label className={estilos.campo}>
            <span className={estilos.rotulo}>Duração (min)</span>
            <input
              type="number"
              value={entrada.duracao_minutos ?? ''}
              min={1}
              max={1000}
              className={estilos.texto}
              aria-invalid={Boolean(erros.duracao_minutos)}
              onChange={(evento) =>
                alterar('duracao_minutos', lerNumero(evento.target.value))
              }
            />
            {erros.duracao_minutos && (
              <span className={estilos.erroCampo}>{erros.duracao_minutos}</span>
            )}
          </label>

          <label className={estilos.campo}>
            <span className={estilos.rotulo}>Status</span>
            <select
              value={entrada.status ?? ''}
              className={estilos.texto}
              onChange={(evento) =>
                alterar('status', (evento.target.value || null) as StatusFilme | null)
              }
            >
              <option value="">Não informado</option>
              {STATUS.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
        </div>

        {/* Gêneros vêm de uma dimensão de 19 valores. Campo livre criaria "Ação"
            ao lado de "Action", então a escolha é fechada por construção. */}
        <fieldset className={estilos.grupo}>
          <legend className={estilos.rotulo}>Gêneros</legend>
          {generos.isPending ? (
            <p className={estilos.aguarde}>Carregando gêneros…</p>
          ) : generos.isError ? (
            <p className={estilos.erroCampo}>
              Não foi possível carregar os gêneros. Verifique se a API está no ar.
            </p>
          ) : (
            <div className={estilos.fichas}>
              {generos.data.map((genero) => {
                const marcado = entrada.generos.includes(genero.nome)
                return (
                  <button
                    key={genero.id}
                    type="button"
                    className={marcado ? estilos.fichaAtiva : estilos.ficha}
                    aria-pressed={marcado}
                    onClick={() =>
                      alterar(
                        'generos',
                        marcado
                          ? entrada.generos.filter((nome) => nome !== genero.nome)
                          : [...entrada.generos, genero.nome],
                      )
                    }
                  >
                    {genero.nome}
                  </button>
                )
              })}
            </div>
          )}
        </fieldset>

        <ListaNomes
          rotulo="Direção"
          nomes={entrada.diretores}
          onMudar={(nomes) => alterar('diretores', nomes)}
          descricao="Um nome já existente é reaproveitado; um novo é criado."
          placeholder="Nome do diretor"
        />

        <label className={estilos.campo}>
          <span className={estilos.rotulo}>Sinopse</span>
          <textarea
            value={entrada.sinopse ?? ''}
            maxLength={4000}
            rows={5}
            className={estilos.area}
            onChange={(evento) => alterar('sinopse', evento.target.value || null)}
          />
        </label>

        <label className={estilos.campo}>
          <span className={estilos.rotulo}>URL do pôster</span>
          <input
            type="url"
            value={entrada.poster_url ?? ''}
            maxLength={2048}
            placeholder="https://…"
            className={estilos.texto}
            onChange={(evento) => alterar('poster_url', evento.target.value || null)}
          />
        </label>

        {/* Pré-visualização: um endereço errado é muito mais fácil de notar como
            imagem quebrada do que como texto numa caixa. */}
        {entrada.poster_url && (
          <img
            src={entrada.poster_url}
            alt=""
            className={estilos.previa}
            onError={(evento) => {
              evento.currentTarget.style.display = 'none'
            }}
          />
        )}

        {mutacao.isError && (
          <p className={estilos.erroEnvio} role="alert">
            {mutacao.error instanceof Error
              ? mutacao.error.message
              : 'Não foi possível salvar o filme.'}
          </p>
        )}

        <div className={estilos.acoes}>
          <button type="submit" className={estilos.salvar} disabled={mutacao.isPending}>
            {mutacao.isPending ? 'Salvando…' : edicao ? 'Salvar alterações' : 'Cadastrar filme'}
          </button>
          <Link to={destinoVoltar} className={estilos.cancelar}>
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  )
}
