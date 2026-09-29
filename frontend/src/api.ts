export async function api<T>(path:string,body?:unknown,method?:string):Promise<T>{
  const response=await fetch('/api'+path,{method:method??(body===undefined?'GET':'POST'),headers:body instanceof FormData?undefined:body===undefined?undefined:{'Content-Type':'application/json'},body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)})
  if(!response.ok){let message=await response.text();try{const data=JSON.parse(message);message=typeof data.detail==='string'?data.detail:JSON.stringify(data.detail)}catch{}throw new Error(message)}
  return response.json()
}
export const errorMessage=(error:unknown)=>error instanceof Error?error.message:String(error)
