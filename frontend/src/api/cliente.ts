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

type Metodo = 'POST' | 'PUT' | 'DELETE'

interface ItemValidacao {
  loc?: (string | number)[]
  msg?: string
}

/** Extrai uma mensagem legível do corpo de erro da API.
 *
 * O FastAPI usa a mesma chave `detail` para duas formas distintas: uma string,
 * quando o erro vem de um `HTTPException` nosso, e uma lista de objetos, quando
 * vem da validação do Pydantic. Sem tratar as duas, um 422 de validação
 * apareceria como "[object Object]" para quem preencheu o formulário.
 */
function mensagemDoErro(corpo: unknown, padrao: string): string {
  if (typeof corpo !== 'object' || corpo === null || !('detail' in corpo)) {
    return padrao
  }

  const detalhe = (corpo as { detail: unknown }).detail

  if (typeof detalhe === 'string') {
    return detalhe
  }

  if (Array.isArray(detalhe)) {
    const mensagens = (detalhe as ItemValidacao[])
      .map((item) => {
        // `loc` começa com "body"; o que interessa a quem lê é o campo.
        const campo = item.loc?.filter((parte) => parte !== 'body').join('.')
        return campo ? `${campo}: ${item.msg}` : item.msg
      })
      .filter((mensagem): mensagem is string => Boolean(mensagem))

    if (mensagens.length > 0) {
      return mensagens.join('; ')
    }
  }

  return padrao
}

/** Executa uma escrita (POST, PUT, DELETE) e devolve o JSON quando existir.
 *
 * Diferente de `buscar`, aqui a mensagem do servidor importa: é ela que informa
 * "Gêneros desconhecidos: Comedia" em vez de um erro genérico. Um 204 do DELETE
 * não tem corpo, e tentar interpretá-lo como JSON lançaria exceção.
 */
export async function enviar<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const resposta = await fetch(`${BASE}${caminho}`, {
    method: metodo,
    headers: corpo === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  })

  if (!resposta.ok) {
    let dados: unknown = null
    try {
      dados = await resposta.json()
    } catch {
      // Resposta de erro sem corpo JSON: fica a mensagem padrão.
    }
    throw new ErroApi(
      resposta.status,
      mensagemDoErro(
        dados,
        resposta.status >= 500
          ? 'O servidor não conseguiu concluir a operação.'
          : 'Não foi possível concluir a operação.',
      ),
    )
  }

  if (resposta.status === 204) {
    return undefined as T
  }

  return (await resposta.json()) as T
}
