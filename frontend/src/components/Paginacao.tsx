import estilos from './Paginacao.module.css'

interface Props {
  pagina: number
  paginas: number
  onMudar: (pagina: number) => void
}

/** Quantidade de páginas mostradas de cada lado da atual. */
const VIZINHOS = 1

type Item = number | 'salto-inicio' | 'salto-fim'

/** Monta a lista de botões visíveis.
 *
 * O catálogo tem milhares de páginas, então listar todas é inviável. A régua
 * mostra sempre a primeira, a última e uma janela ao redor da atual, com
 * reticências no lugar do que foi omitido.
 */
function montarItens(atual: number, total: number): Item[] {
  if (total <= 1) {
    return total === 1 ? [1] : []
  }

  const itens: Item[] = [1]
  const inicio = Math.max(2, atual - VIZINHOS)
  const fim = Math.min(total - 1, atual + VIZINHOS)

  if (inicio > 2) {
    itens.push('salto-inicio')
  }
  for (let numero = inicio; numero <= fim; numero += 1) {
    itens.push(numero)
  }
  if (fim < total - 1) {
    itens.push('salto-fim')
  }
  itens.push(total)

  return itens
}

export function Paginacao({ pagina, paginas, onMudar }: Props) {
  if (paginas <= 1) {
    return null
  }

  const itens = montarItens(pagina, paginas)

  return (
    <nav className={estilos.base} aria-label="Paginação do catálogo">
      <button
        type="button"
        className={estilos.controle}
        onClick={() => onMudar(pagina - 1)}
        disabled={pagina <= 1}
      >
        Anterior
      </button>

      <ul className={estilos.lista}>
        {itens.map((item) =>
          typeof item === 'number' ? (
            <li key={item}>
              <button
                type="button"
                className={item === pagina ? estilos.atual : estilos.numero}
                onClick={() => onMudar(item)}
                aria-current={item === pagina ? 'page' : undefined}
                aria-label={`Página ${item}`}
              >
                {item.toLocaleString('pt-BR')}
              </button>
            </li>
          ) : (
            <li key={item} className={estilos.reticencias} aria-hidden="true">
              …
            </li>
          ),
        )}
      </ul>

      <button
        type="button"
        className={estilos.controle}
        onClick={() => onMudar(pagina + 1)}
        disabled={pagina >= paginas}
      >
        Próxima
      </button>
    </nav>
  )
}
