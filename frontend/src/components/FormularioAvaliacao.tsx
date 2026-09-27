import { useState } from 'react'

import { useCriarAvaliacao } from '../api/filmes'
import { SeletorEstrelas } from './SeletorEstrelas'
import estilos from './FormularioAvaliacao.module.css'

interface Props {
  filmeId: string
  titulo: string
}

const LIMITE_COMENTARIO = 4000

export function FormularioAvaliacao({ filmeId, titulo }: Props) {
  const [nome, setNome] = useState('')
  const [nota, setNota] = useState(0)
  const [comentario, setComentario] = useState('')
  const [erro, setErro] = useState<string | null>(null)

  const criar = useCriarAvaliacao(filmeId)

  function enviar(evento: React.FormEvent) {
    evento.preventDefault()

    // A nota não tem estado "em branco" no contrato: zero aqui significa "não
    // escolhida", e zero é um valor legítimo da escala. Por isso a validação é
    // explícita em vez de delegada ao campo.
    if (!nota) {
      setErro('Escolha uma nota antes de publicar.')
      return
    }
    if (!nome.trim()) {
      setErro('Diga seu nome — não há login neste sistema.')
      return
    }
    if (!comentario.trim()) {
      setErro('Escreva algo sobre o filme.')
      return
    }

    setErro(null)
    criar.mutate(
      { nome: nome.trim(), nota, comentario: comentario.trim() },
      {
        onSuccess: () => {
          // A nota é zerada junto com o resto: manter a anterior selecionada
          // sugeriria que a próxima avaliação já tem nota.
          setNome('')
          setNota(0)
          setComentario('')
        },
      },
    )
  }

  const restantes = LIMITE_COMENTARIO - comentario.length

  return (
    <form className={estilos.formulario} onSubmit={enviar} noValidate>
      <h3 className={estilos.titulo}>Avaliar {titulo}</h3>

      <SeletorEstrelas valor={nota} onMudar={setNota} />

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Seu nome</span>
        <input
          type="text"
          value={nome}
          maxLength={120}
          className={estilos.texto}
          placeholder="Como você quer aparecer"
          onChange={(evento) => setNome(evento.target.value)}
        />
      </label>

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Sua resenha</span>
        <textarea
          value={comentario}
          maxLength={LIMITE_COMENTARIO}
          rows={4}
          className={estilos.area}
          placeholder="O que você achou?"
          onChange={(evento) => setComentario(evento.target.value)}
        />
        {/* O contador só aparece perto do limite: exibi-lo sempre chamaria
            atenção para uma restrição que quase nunca importa. */}
        {restantes < 200 && (
          <span className={estilos.contador}>{restantes} caracteres restantes</span>
        )}
      </label>

      {(erro ?? criar.isError) && (
        <p className={estilos.erro} role="alert">
          {erro ??
            (criar.error instanceof Error
              ? criar.error.message
              : 'Não foi possível publicar a avaliação.')}
        </p>
      )}

      <div className={estilos.acoes}>
        <button type="submit" className={estilos.publicar} disabled={criar.isPending}>
          {criar.isPending ? 'Publicando…' : 'Publicar avaliação'}
        </button>
        {criar.isSuccess && !criar.isPending && (
          <span className={estilos.confirmacao} role="status">
            Avaliação publicada.
          </span>
        )}
      </div>
    </form>
  )
}
