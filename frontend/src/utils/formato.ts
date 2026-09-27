/** Formatações de exibição. Todas devolvem `null` quando não há o que mostrar,
 * para que a interface simplesmente omita o campo em vez de exibir um traço.
 */

export function formatarDuracao(minutos: number | null): string | null {
  if (!minutos || minutos <= 0) {
    return null
  }
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  if (horas === 0) {
    return `${resto} min`
  }
  return resto === 0 ? `${horas}h` : `${horas}h ${resto}min`
}

export function formatarData(iso: string | null): string | null {
  if (!iso) {
    return null
  }
  // A data vem como `2017-02-01`. Criar o Date direto dessa string a interpreta
  // como UTC, o que em fusos negativos exibiria o dia anterior.
  const [ano, mes, dia] = iso.split('-').map(Number)
  if (!ano || !mes || !dia) {
    return null
  }
  return new Date(ano, mes - 1, dia).toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}

export function formatarDinheiro(valor: number | null): string | null {
  if (valor === null || valor <= 0) {
    return null
  }
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  })
}

export function formatarNumero(valor: number | null): string | null {
  return valor === null ? null : valor.toLocaleString('pt-BR')
}

const MINUTO = 60_000
const HORA = 60 * MINUTO
const DIA = 24 * HORA
/** Fronteira entre "é notícia" e "é história". */
const LIMITE_RELATIVO = 7 * DIA

/** Formata um instante como tempo relativo na primeira semana, data depois.
 *
 * "há 3 horas" responde a pergunta que se faz de uma avaliação recente — quão
 * recente? Passada uma semana, a pergunta muda: "há 43 dias" obriga o leitor a
 * fazer a conta que ele queria pronta, e a data absoluta responde melhor.
 *
 * O instante chega com fuso (`...+00:00`), porque o backend o marca como UTC.
 * Sem esse fuso, o JavaScript leria a data-hora como local e uma avaliação
 * criada agora apareceria três horas no futuro.
 */
export function formatarQuando(iso: string | null): string | null {
  if (!iso) {
    return null
  }

  const instante = new Date(iso)
  if (Number.isNaN(instante.getTime())) {
    return null
  }

  const decorrido = Date.now() - instante.getTime()

  // Relógios podem divergir por alguns segundos entre servidor e navegador; um
  // instante "no futuro" por essa margem ainda é agora, não uma data futura.
  if (decorrido < MINUTO) {
    return 'agora mesmo'
  }

  if (decorrido < LIMITE_RELATIVO) {
    const relativo = new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' })
    if (decorrido < HORA) {
      return relativo.format(-Math.floor(decorrido / MINUTO), 'minute')
    }
    if (decorrido < DIA) {
      return relativo.format(-Math.floor(decorrido / HORA), 'hour')
    }
    return relativo.format(-Math.floor(decorrido / DIA), 'day')
  }

  return instante.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}
