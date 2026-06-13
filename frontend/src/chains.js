// Chain display names come from the data export (the `chains` map in
// stores.json), so the ETL is the single source of truth. The map is populated
// once stores.json is fetched; until then chainName falls back to the raw id.
let chainNames = {}

export const setChainNames = (map) => {
  chainNames = map || {}
}

export const chainName = (chainId) => chainNames[chainId] || chainId
