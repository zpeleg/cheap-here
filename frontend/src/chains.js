export const CHAIN_NAMES = {
  '7290027600007': 'Shufersal',
  '7290058140886': 'Rami Levy',
  '7290873255550': 'Tiv Taam',
  '7290803800003': 'Yohananof',
  '7290103152017': 'Osher Ad',
  '7290696200003': 'Victory',
  '7290058103393': 'Victory',
  '7290058249350': 'Wolt Market',
  '7290058197699': 'Good Pharm',
  '7290055700007': 'Carrefour',
  '7290700100008': 'Hazi Hinam',
}

export const chainName = (chainId) => CHAIN_NAMES[chainId] || chainId
