// AegisWatch frontend config.
//
// After deploying the contract on GenLayer Studio, paste its address into the
// fallback below or set VITE_CONTRACT_ADDRESS at build time (Vercel env).
//
//   CHAIN = "studio"    -> GenLayer Studio Network (studionet)
//   CHAIN = "simulator" -> localnet / simulator

export const CONTRACT_ADDRESS =
  import.meta.env.VITE_CONTRACT_ADDRESS || "0x10781FE67637d391Faa5Ad63AF4fE41e0261304b";
export const CHAIN = import.meta.env.VITE_CHAIN || "studio";
