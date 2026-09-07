// AegisWatch frontend config.
//
// After deploying the contract on GenLayer Studio, paste its address into the
// fallback below or set VITE_CONTRACT_ADDRESS at build time (Vercel env).
//
//   CHAIN = "studio"    -> GenLayer Studio Network (studionet)
//   CHAIN = "simulator" -> localnet / simulator

export const CONTRACT_ADDRESS =
  import.meta.env.VITE_CONTRACT_ADDRESS || "TO_BE_FILLED_AFTER_DEPLOY";
export const CHAIN = import.meta.env.VITE_CHAIN || "studio";
