export type Match = {id:string; competition_id:string; home:string; away:string; kickoff:string; status:string; home_score:number|null; away_score:number|null; provenance:string};
export async function api<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(path, init);
  if(!response.ok) {
    let message = `Request failed (${response.status})`;
    try {const error=await response.json(); message=typeof error.detail==='string'?error.detail:JSON.stringify(error.detail);} catch { /* retain HTTP error */ }
    throw new Error(message);
  }
  return response.json();
}
export function score(match:Match) {return match.home_score===null?'—':`${match.home_score} : ${match.away_score}`;}
