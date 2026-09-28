/** Desenho da estrela, compartilhado pela exibição e pelo seletor.
 *
 * A tinta do traçado vai de x=2,5 a x=21,5 num `viewBox` de 24 unidades, ou
 * seja, é **simétrica** dentro da caixa: o centro visual da estrela coincide com
 * o centro da caixa. Isso é o que permite recortar exatamente metade dela em
 * 50% da largura, sem tabela de ajustes.
 */

const CAMINHO =
  'M12 2l2.9 6.26 6.6.72-4.9 4.6 1.35 6.42L12 16.9l-5.95 3.1L7.4 13.58 2.5 8.98l6.6-.72L12 2z'

export function IconeEstrela({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path d={CAMINHO} />
    </svg>
  )
}
