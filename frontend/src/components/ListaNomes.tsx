import { useState } from 'react'

import estilos from './ListaNomes.module.css'

interface Props {
  rotulo: string
  nomes: string[]
  onMudar: (nomes: string[]) => void
  descricao?: string
  placeholder?: string
}

/** Campo de lista de nomes, com adição por Enter e remoção por item.
 *
 * Um único campo de texto com nomes separados por vírgula seria mais curto de
 * escrever, mas empurraria para o usuário a tarefa de acertar a separação — e
 * um nome como "Silva, Ana" viraria dois diretores. Cada nome é uma entrada
 * própria, do mesmo jeito que é uma linha própria em `dim_people`.
 */
export function ListaNomes({ rotulo, nomes, onMudar, descricao, placeholder }: Props) {
  const [rascunho, setRascunho] = useState('')

  function adicionar() {
    const nome = rascunho.trim()
    if (!nome) {
      return
    }
    // A comparação ignora caixa para evitar "Ana" e "ana" na mesma lista; o
    // backend também recusaria o par repetido, porque a bridge tem chave
    // composta.
    const repetido = nomes.some((existente) => existente.toLowerCase() === nome.toLowerCase())
    if (!repetido) {
      onMudar([...nomes, nome])
    }
    setRascunho('')
  }

  return (
    <div className={estilos.campo}>
      <span className={estilos.rotulo}>{rotulo}</span>
      {descricao && <span className={estilos.descricao}>{descricao}</span>}

      <div className={estilos.entrada}>
        <input
          type="text"
          value={rascunho}
          placeholder={placeholder}
          className={estilos.texto}
          aria-label={rotulo}
          onChange={(evento) => setRascunho(evento.target.value)}
          onKeyDown={(evento) => {
            // Enter dentro de um formulário submeteria a página inteira.
            if (evento.key === 'Enter') {
              evento.preventDefault()
              adicionar()
            }
          }}
        />
        <button type="button" className={estilos.adicionar} onClick={adicionar}>
          Adicionar
        </button>
      </div>

      {nomes.length > 0 && (
        <ul className={estilos.lista}>
          {nomes.map((nome) => (
            <li key={nome} className={estilos.item}>
              {nome}
              <button
                type="button"
                className={estilos.remover}
                aria-label={`Remover ${nome}`}
                onClick={() => onMudar(nomes.filter((outro) => outro !== nome))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
