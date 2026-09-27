import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { useAvaliacoes, useFilme, useRemoverFilme } from '../api/filmes'
import type { MetricasFilme } from '../api/tipos'
import { Estrelas } from '../components/Estrelas'
import { ListaAvaliacoes } from '../components/ListaAvaliacoes'
import { ListaCreditos } from '../components/ListaCreditos'
import { Mensagem } from '../components/Mensagem'
import { Paginacao } from '../components/Paginacao'
import { ErroApi } from '../api/cliente'
import { formatarData, formatarDinheiro, formatarDuracao, formatarNumero } from '../utils/formato'
import estilos from './FilmeDetalhe.module.css'

/** Acima deste número o elenco é recolhido; direção e roteiro nunca são. */
const LIMITE_ELENCO = 12

function lerPagina(valor: string | null): number {
  const numero = Number(valor)
  return Number.isInteger(numero) && numero >= 1 ? numero : 1
}

function FichaMetricas({ metricas }: { metricas: MetricasFilme }) {
  // Filmes sem votos chegam com nota 0, e não nula: exibir "0.0" sugeriria
  // avaliação péssima em vez de ausência de dados. Por isso o zero é omitido.
  const linhas = [
    metricas.nota_tmdb
      ? {
          rotulo: 'TMDB',
          valor: metricas.nota_tmdb.toFixed(1),
          extra: formatarNumero(metricas.qtd_tmdb),
        }
      : null,
    metricas.nota_imdb
      ? {
          rotulo: 'IMDb',
          valor: metricas.nota_imdb.toFixed(1),
          extra: formatarNumero(metricas.qtd_imdb),
        }
      : null,
    // Orçamento e receita existem para menos de 10% do catálogo: a seção só
    // aparece quando há o que mostrar, em vez de exibir campos vazios.
    formatarDinheiro(metricas.orcamento_usd)
      ? { rotulo: 'Orçamento', valor: formatarDinheiro(metricas.orcamento_usd)!, extra: null }
      : null,
    formatarDinheiro(metricas.receita_usd)
      ? { rotulo: 'Receita', valor: formatarDinheiro(metricas.receita_usd)!, extra: null }
      : null,
  ].filter((linha) => linha !== null)

  if (linhas.length === 0) {
    return null
  }

  return (
    <section className={estilos.metricas}>
      {linhas.map((linha) => (
        <div key={linha.rotulo} className={estilos.metrica}>
          <span className={estilos.metricaRotulo}>{linha.rotulo}</span>
          <span className={estilos.metricaValor}>{linha.valor}</span>
          {linha.extra && <span className={estilos.metricaExtra}>{linha.extra} votos</span>}
        </div>
      ))}
    </section>
  )
}

export function FilmeDetalhe() {
  const { id = '' } = useParams()
  const navegar = useNavigate()
  const [parametros, definirParametros] = useSearchParams()
  const paginaAvaliacoes = lerPagina(parametros.get('avaliacoes'))

  const filme = useFilme(id)
  const avaliacoes = useAvaliacoes(id, paginaAvaliacoes)
  const remover = useRemoverFilme()
  const [confirmando, setConfirmando] = useState(false)

  function irParaAvaliacoes(destino: number) {
    definirParametros(destino === 1 ? {} : { avaliacoes: String(destino) })
  }

  function excluir() {
    remover.mutate(id, {
      // A navegação acontece no sucesso, não antes: se a remoção falhar, o
      // usuário continua na página e vê o motivo, em vez de ser levado ao
      // catálogo acreditando que deu certo.
      onSuccess: () => navegar('/', { replace: true }),
    })
  }

  if (filme.isPending) {
    return (
      <div className={estilos.pagina}>
        <div className={estilos.carregando} aria-label="Carregando filme" />
      </div>
    )
  }

  if (filme.isError) {
    const naoEncontrado = filme.error instanceof ErroApi && filme.error.status === 404
    return (
      <div className={estilos.pagina}>
        <Mensagem
          tom="erro"
          titulo={naoEncontrado ? 'Filme não encontrado' : 'Não foi possível carregar o filme'}
          descricao={
            naoEncontrado
              ? 'O filme que você procura não está no catálogo.'
              : 'Verifique se a API está rodando em localhost:8000.'
          }
          acao={{ rotulo: 'Voltar ao catálogo', onClick: () => navegar('/') }}
        />
      </div>
    )
  }

  const dados = filme.data
  const duracao = formatarDuracao(dados.duracao_minutos)
  const lancamento = formatarData(dados.data_lancamento)

  return (
    <article className={estilos.pagina}>
      {/* 40% dos filmes não têm backdrop; sem ele a faixa vira um gradiente. */}
      <div
        className={dados.backdrop_url ? estilos.capa : estilos.capaVazia}
        style={
          dados.backdrop_url ? { backgroundImage: `url(${dados.backdrop_url})` } : undefined
        }
      />

      <div className={estilos.conteudo}>
        <div className={estilos.barraTopo}>
          <Link to="/" className={estilos.voltar}>
            ← Voltar ao catálogo
          </Link>

          <div className={estilos.acoes}>
            <Link to={`/filmes/${id}/editar`} className={estilos.editar}>
              Editar
            </Link>
            <button
              type="button"
              className={estilos.excluir}
              onClick={() => setConfirmando(true)}
            >
              Excluir
            </button>
          </div>
        </div>

        {/* Confirmação em painel, e não `window.confirm`: o diálogo do navegador
            não pode dizer o que será apagado junto, que é justamente a
            informação que faz a confirmação valer algo. */}
        {confirmando && (
          <div className={estilos.confirmacao} role="alertdialog" aria-label="Confirmar exclusão">
            <p className={estilos.confirmacaoTexto}>
              Excluir <strong>{filme.data.titulo}</strong> em definitivo?
              {filme.data.qtd_avaliacoes > 0 && (
                <>
                  {' '}
                  As {filme.data.qtd_avaliacoes}{' '}
                  {filme.data.qtd_avaliacoes === 1 ? 'avaliação' : 'avaliações'} também
                  {filme.data.qtd_avaliacoes === 1 ? ' será' : ' serão'} removidas.
                </>
              )}
            </p>

            {remover.isError && (
              <p className={estilos.confirmacaoErro} role="alert">
                {remover.error instanceof Error
                  ? remover.error.message
                  : 'Não foi possível excluir o filme.'}
              </p>
            )}

            <div className={estilos.confirmacaoAcoes}>
              <button
                type="button"
                className={estilos.confirmar}
                disabled={remover.isPending}
                onClick={excluir}
              >
                {remover.isPending ? 'Excluindo…' : 'Sim, excluir'}
              </button>
              <button
                type="button"
                className={estilos.manter}
                disabled={remover.isPending}
                onClick={() => setConfirmando(false)}
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        <div className={estilos.topo}>
          <div className={estilos.posterArea}>
            {dados.poster_url ? (
              <img
                src={dados.poster_url}
                alt={`Pôster de ${dados.titulo}`}
                className={estilos.poster}
              />
            ) : (
              <div className={estilos.posterVazio}>{dados.titulo}</div>
            )}
          </div>

          <div className={estilos.cabecalho}>
            <h1 className={estilos.titulo}>{dados.titulo}</h1>

            <p className={estilos.ficha}>
              {[dados.ano, duracao, dados.status].filter(Boolean).join(' · ')}
            </p>

            {dados.generos.length > 0 && (
              <ul className={estilos.generos}>
                {dados.generos.map((genero) => (
                  <li key={genero.id}>{genero.nome}</li>
                ))}
              </ul>
            )}

            <div className={estilos.avaliacaoGeral}>
              {dados.nota_media === null ? (
                <span className={estilos.semNota}>Ainda não avaliado</span>
              ) : (
                <>
                  <Estrelas nota={dados.nota_media} />
                  <span className={estilos.notaValor}>{dados.nota_media.toFixed(1)}</span>
                  <span className={estilos.notaContagem}>
                    {dados.qtd_avaliacoes}{' '}
                    {dados.qtd_avaliacoes === 1 ? 'avaliação' : 'avaliações'}
                  </span>
                </>
              )}
            </div>

            {dados.sinopse && <p className={estilos.sinopse}>{dados.sinopse}</p>}

            {lancamento && (
              <p className={estilos.lancamento}>Lançamento: {lancamento}</p>
            )}
          </div>
        </div>

        <div className={estilos.creditos}>
          <ListaCreditos titulo="Direção" pessoas={dados.diretores} />
          <ListaCreditos titulo="Roteiro" pessoas={dados.roteiristas} />
          <ListaCreditos titulo="Elenco" pessoas={dados.elenco} limite={LIMITE_ELENCO} />
          <ListaCreditos
            titulo="Produção"
            pessoas={dados.produtoras}
            limite={LIMITE_ELENCO}
          />
        </div>

        {dados.metricas && <FichaMetricas metricas={dados.metricas} />}

        <section className={estilos.secaoAvaliacoes}>
          <h2 className={estilos.secaoTitulo}>
            Avaliações
            {avaliacoes.data && avaliacoes.data.total > 0 && (
              <span className={estilos.secaoContagem}>{avaliacoes.data.total}</span>
            )}
          </h2>

          {avaliacoes.isPending ? (
            <p className={estilos.aguarde}>Carregando avaliações…</p>
          ) : avaliacoes.isError ? (
            <Mensagem
              tom="erro"
              titulo="Não foi possível carregar as avaliações"
              acao={{ rotulo: 'Tentar novamente', onClick: () => void avaliacoes.refetch() }}
            />
          ) : avaliacoes.data.items.length === 0 ? (
            <Mensagem
              titulo="Nenhuma avaliação ainda"
              descricao="Este filme não recebeu resenhas."
            />
          ) : (
            <>
              <ListaAvaliacoes avaliacoes={avaliacoes.data.items} />
              <Paginacao
                pagina={avaliacoes.data.pagina}
                paginas={avaliacoes.data.paginas}
                onMudar={irParaAvaliacoes}
              />
            </>
          )}
        </section>
      </div>
    </article>
  )
}
