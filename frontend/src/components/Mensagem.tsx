import estilos from './Mensagem.module.css'

interface Props {
  titulo: string
  descricao?: string
  tom?: 'neutro' | 'erro'
  acao?: {
    rotulo: string
    onClick: () => void
  }
}

/** Bloco centralizado para os estados em que não há grade a exibir. */
export function Mensagem({ titulo, descricao, tom = 'neutro', acao }: Props) {
  return (
    <div className={tom === 'erro' ? estilos.erro : estilos.base} role="status">
      <h2 className={estilos.titulo}>{titulo}</h2>
      {descricao && <p className={estilos.descricao}>{descricao}</p>}
      {acao && (
        <button type="button" className={estilos.acao} onClick={acao.onClick}>
          {acao.rotulo}
        </button>
      )}
    </div>
  )
}
