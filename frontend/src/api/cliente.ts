/** Cliente HTTP mínimo sobre `fetch`.
 *
 * O caminho é relativo (`/api/v1`) porque o proxy do Vite encaminha para o
 * backend em desenvolvimento — ver `vite.config.ts`.
 */

const BASE = '/api/v1'

export class ErroApi extends Error {
  status: number

  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.name = 'ErroApi'
    this.status = status
  }
}

type Parametros = Record<string, string | number | undefined>

/** Executa um GET e devolve o JSON já tipado.
 *
 * `fetch` só rejeita em falha de rede: uma resposta 404 ou 500 chega como
 * sucesso com `ok === false`. Converter isso em exceção é o que permite ao
 * TanStack Query distinguir erro de dado e acionar seu retry.
 */
export async function buscar<T>(caminho: string, parametros?: Parametros): Promise<T> {
  const url = new URL(`${BASE}${caminho}`, window.location.origin)

  for (const [chave, valor] of Object.entries(parametros ?? {})) {
    if (valor !== undefined) {
      url.searchParams.set(chave, String(valor))
    }
  }

  const resposta = await fetch(url)

  if (!resposta.ok) {
    throw new ErroApi(
      resposta.status,
      resposta.status >= 500
        ? 'O servidor não conseguiu responder.'
        : 'Não foi possível carregar os dados.',
    )
  }

  return (await resposta.json()) as T
}
