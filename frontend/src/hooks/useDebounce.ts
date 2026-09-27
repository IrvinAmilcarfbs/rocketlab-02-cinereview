import { useEffect, useState } from 'react'

/** Adia a propagação de um valor até que ele pare de mudar.
 *
 * Sem isso, cada tecla digitada dispararia uma requisição: "batman" geraria
 * seis buscas, das quais só a última interessa. O efeito é recriado a cada
 * mudança e a limpeza cancela o temporizador anterior, de modo que apenas a
 * pausa na digitação chega ao fim.
 */
export function useDebounce<T>(valor: T, atrasoMs = 350): T {
  const [adiado, setAdiado] = useState(valor)

  useEffect(() => {
    const temporizador = setTimeout(() => setAdiado(valor), atrasoMs)
    return () => clearTimeout(temporizador)
  }, [valor, atrasoMs])

  return adiado
}
