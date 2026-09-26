import { useSearchParams } from 'react-router-dom'

import { TAMANHO_PAGINA, useCatalogo } from '../api/filmes'
import { CardEsqueleto } from '../components/CardEsqueleto'
import { FilmeCard } from '../components/FilmeCard'
import { Mensagem } from '../components/Mensagem'
import { Paginacao } from '../components/Paginacao'
import estilos from './Catalogo.module.css'

/** A página vive na URL para que recarregar e compartilhar o link funcionem. */
function lerPagina(valor: string | null): number {
  const numero = Number(valor)
  return Number.isInteger(numero) && numero >= 1 ? numero : 1
}

export function Catalogo() {
  const [parametros, definirParametros] = useSearchParams()
  const pagina = lerPagina(parametros.get('pagina'))
  const { data, isPending, isError, error, isFetching, refetch } = useCatalogo(pagina)

  function irPara(destino: number) {
    // A primeira página fica sem parâmetro, deixando a URL limpa na entrada.
    definirParametros(destino === 1 ? {} : { pagina: String(destino) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function renderizarConteudo() {
    if (isError) {
      return (
        <Mensagem
          tom="erro"
          titulo="Não foi possível carregar o catálogo"
          descricao={
            error instanceof Error
              ? `${error.message} Verifique se a API está rodando em localhost:8000.`
              : undefined
          }
          acao={{ rotulo: 'Tentar novamente', onClick: () => void refetch() }}
        />
      )
    }

    if (isPending) {
      return (
        <div className={estilos.grade}>
          {Array.from({ length: TAMANHO_PAGINA }, (_, indice) => (
            <CardEsqueleto key={indice} />
          ))}
        </div>
      )
    }

    if (data.items.length === 0) {
      return (
        <Mensagem
          titulo="Nenhum filme nesta página"
          descricao="O catálogo não chega até aqui."
          acao={{ rotulo: 'Voltar ao início', onClick: () => irPara(1) }}
        />
      )
    }

    return (
      <>
        {/* Durante a troca de página os dados antigos continuam na tela, apenas
            esmaecidos — evita o salto de layout que um estado de carregamento
            cheio provocaria a cada clique. */}
        <div className={isFetching ? estilos.gradeAtualizando : estilos.grade}>
          {data.items.map((filme) => (
            <FilmeCard key={filme.id} filme={filme} />
          ))}
        </div>

        <Paginacao pagina={data.pagina} paginas={data.paginas} onMudar={irPara} />

        <p className={estilos.rodape}>
          Página {data.pagina.toLocaleString('pt-BR')} de{' '}
          {data.paginas.toLocaleString('pt-BR')}
        </p>
      </>
    )
  }

  return (
    <div className={estilos.pagina}>
      <header className={estilos.cabecalho}>
        <h1 className={estilos.marca}>
          Cine<span className={estilos.marcaDestaque}>log</span>
        </h1>
        <p className={estilos.subtitulo}>
          {data
            ? `${data.total.toLocaleString('pt-BR')} filmes no catálogo`
            : 'Carregando catálogo…'}
        </p>
      </header>

      <main>{renderizarConteudo()}</main>
    </div>
  )
}
