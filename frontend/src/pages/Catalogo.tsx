import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { TAMANHO_PAGINA, useCatalogo } from '../api/filmes'
import { BarraBusca } from '../components/BarraBusca'
import { CardEsqueleto } from '../components/CardEsqueleto'
import { FilmeCard } from '../components/FilmeCard'
import { Mensagem } from '../components/Mensagem'
import { Paginacao } from '../components/Paginacao'
import { useDebounce } from '../hooks/useDebounce'
import estilos from './Catalogo.module.css'

/** A página vive na URL para que recarregar e compartilhar o link funcionem. */
function lerPagina(valor: string | null): number {
  const numero = Number(valor)
  return Number.isInteger(numero) && numero >= 1 ? numero : 1
}

export function Catalogo() {
  const [parametros, definirParametros] = useSearchParams()
  const pagina = lerPagina(parametros.get('pagina'))
  const busca = parametros.get('busca') ?? ''

  // O campo responde a cada tecla, mas só a pausa na digitação chega à URL —
  // e é a URL que alimenta a consulta.
  const [texto, setTexto] = useState(busca)
  const textoAdiado = useDebounce(texto)

  const { data, isPending, isError, error, isFetching, refetch } = useCatalogo(pagina, busca)

  useEffect(() => {
    if (textoAdiado === busca) {
      return
    }
    // Trocar a busca recomeça da primeira página: a numeração antiga não
    // descreve mais o mesmo conjunto. `replace` evita encher o histórico com
    // um registro por tecla digitada.
    definirParametros(textoAdiado ? { busca: textoAdiado } : {}, { replace: true })
  }, [textoAdiado, busca, definirParametros])

  // Mantém o campo coerente quando a URL muda por fora, como no botão voltar.
  // O ajuste acontece durante o render, e não em um efeito: é o padrão do React
  // para derivar estado de um valor externo, e evita o render intermediário com
  // o campo desatualizado que um efeito produziria.
  const [buscaVista, setBuscaVista] = useState(busca)
  if (busca !== buscaVista) {
    setBuscaVista(busca)
    setTexto(busca)
  }

  function irPara(destino: number) {
    const novos = new URLSearchParams()
    if (busca) {
      novos.set('busca', busca)
    }
    if (destino > 1) {
      novos.set('pagina', String(destino))
    }
    definirParametros(novos)
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
      return busca ? (
        <Mensagem
          titulo={`Nenhum filme encontrado para "${busca}"`}
          descricao="Verifique a grafia ou tente outro termo. A busca ignora acentos e maiúsculas."
          acao={{ rotulo: 'Limpar busca', onClick: () => setTexto('') }}
        />
      ) : (
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

  function descreverResultado() {
    if (!data) {
      return 'Carregando catálogo…'
    }
    const quantidade = data.total.toLocaleString('pt-BR')
    if (!busca) {
      return `${quantidade} filmes no catálogo`
    }
    return data.total === 1
      ? `1 filme encontrado para "${busca}"`
      : `${quantidade} filmes encontrados para "${busca}"`
  }

  return (
    <div className={estilos.pagina}>
      <header className={estilos.cabecalho}>
        <h1 className={estilos.marca}>
          Cine<span className={estilos.marcaDestaque}>log</span>
        </h1>

        <BarraBusca
          valor={texto}
          onMudar={setTexto}
          carregando={isFetching && texto !== busca}
        />

        <p className={estilos.subtitulo} aria-live="polite">
          {descreverResultado()}
        </p>
      </header>

      <main>{renderizarConteudo()}</main>
    </div>
  )
}
