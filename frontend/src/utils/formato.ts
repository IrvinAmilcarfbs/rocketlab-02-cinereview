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
